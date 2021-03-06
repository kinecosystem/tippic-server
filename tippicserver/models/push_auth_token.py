import arrow
import logging as log

from tippicserver import db, config
from tippicserver.utils import InternalError
from sqlalchemy_utils import UUIDType, ArrowType
import uuid


class PushAuthToken(db.Model):
    """the PushAuth class hold data related to the push-authentication mechanism.
    """

    user_id = db.Column('user_id', UUIDType(binary=False), db.ForeignKey("user.user_id"), primary_key=True, nullable=False)
    authenticated = db.Column(db.Boolean, unique=False, default=False)
    send_date = db.Column(ArrowType)
    ack_date = db.Column(ArrowType)
    auth_token = db.Column(UUIDType(binary=False), unique=True, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return '<user_id: %s, authenticated: %s, send_date: %s, ack_date: %s, token: %s, updated_at: %s' % (
        self.user_id, self.authenticated, self.send_date, self.ack_date, self.auth_token, self.updated_at)


def get_token_obj_by_user_id(user_id):
    """returns the token object for this user, and creates one if one doesn't exist"""
    push_auth_token = PushAuthToken.query.filter_by(user_id=user_id).first()
    if not push_auth_token:
        # create one on the fly. throws exception if the user doesn't exist
        return create_token(user_id)

    return push_auth_token


def create_token(user_id):
    """create an authentication token for the given user_id"""
    try:
        push_auth_token = PushAuthToken()
        push_auth_token.user_id = user_id
        push_auth_token.auth_token = uuid.uuid4()
        push_auth_token.authenticated = False

        db.session.add(push_auth_token)
        db.session.commit()
    except Exception as e:
        log.error('cant add PushAuthToken to db with id %s. e:%s' % (user_id, e))
    else:
        return push_auth_token


def refresh_token(user_id):
    """regenerate the token"""
    push_auth_token = get_token_obj_by_user_id(user_id)
    push_auth_token.auth_token = uuid.uuid4()

    db.session.add(push_auth_token)
    db.session.commit()


def set_send_date(user_id):
    """update the send_date for this user_id's token"""
    push_auth_token = get_token_obj_by_user_id(user_id)
    push_auth_token.send_date = arrow.utcnow()

    db.session.add(push_auth_token)
    db.session.commit()
    return True


def ack_auth_token(user_id, token):
    """called when a user acks a push token

    returns true if all went well, false otherwise
    """
    try:
        push_auth_token = get_token_obj_by_user_id(user_id)
        if str(push_auth_token.auth_token) == str(token):
            log.info('user_id %s successfully acked the push token' % user_id)
            set_ack_date(user_id)
            return True
    except Exception as e:
        log.error('user_id %s failed to ack the (internal) push token: %s with this token %s' % (user_id, str(push_auth_token.auth_token), token))
        return False


def set_ack_date(user_id):
    """update the ack_date for this user_id's token"""
    push_auth_token = get_token_obj_by_user_id(user_id)
    push_auth_token.ack_date = arrow.utcnow()
    push_auth_token.authenticated = True

    db.session.add(push_auth_token)
    db.session.commit()


def get_token_by_user_id(user_id):
    """return the token uuid itself for this user_id"""
    push_auth_token = get_token_obj_by_user_id(user_id)
    if push_auth_token:
        return push_auth_token.auth_token


def print_auth_tokens():
    log.info('printing all auth tokens:')
    push_auth_tokens = PushAuthToken.query.all()
    for token in push_auth_tokens:
        log.info(token)
    return {str(token.user_id): str(token.auth_token) for token in push_auth_tokens}


def should_send_auth_token(user_id):
    """determines whether a user should be sent an auth push token"""
    if not config.AUTH_TOKEN_ENABLED:
        return False

    token_obj = get_token_obj_by_user_id(user_id)
    if token_obj.send_date is None:
        # always send to a user that hasn't been sent yet
        return True

    if not token_obj.authenticated:
        # keep sending the auth push message because the user isn't authenticated
        return True

    # if more than AUTH_TOKEN_SEND_INTERVAL_DAYS passed, resend and refresh the token regardless of the current state
    elif (arrow.utcnow() - token_obj.send_date).total_seconds() > 60 * 60 * 24 * int(config.AUTH_TOKEN_SEND_INTERVAL_DAYS):
        log.info('refreshing auth token for user %s' % user_id)
        refresh_token(user_id)
        return True

    return False


def is_user_authenticated(user_id):
    """returns True if the user is currently authenticated"""
    token_obj = get_token_obj_by_user_id(user_id)
    return token_obj.authenticated


def scan_for_deauthed_users():
    """this script is called by cron every x sedonds to de-authenticate users that failed to ack the auth token"""
    push_auth_tokens = PushAuthToken.query.all()
    deauth_user_ids = []
    now = arrow.utcnow()
    for token in push_auth_tokens:
        if token.authenticated:
            # authenticated users have all previously been sent - and acked
            send_date = arrow.get(token.send_date)
            ack_date = arrow.get(token.send_date)
            sent_secs_ago = (now - send_date).total_seconds()
            ack_secs_ago = (now - ack_date).total_seconds()
            if 5 < sent_secs_ago < 10 and ack_secs_ago > 10:
                log.info('scan_for_deauthed_users: marking user %s as unauthenticated. sent_secs_ago: %s' % (token.user_id, ack_secs_ago))
                deauth_user_ids.append(token.user_id)

    deauth_users(deauth_user_ids)
    log.info('deauthed %s users' % len(deauth_user_ids))
    return True


def deauth_users(user_ids):
    """set the given user_ids list to authenticated=false"""
    if len(user_ids) == 0:
        return

    user_ids_string = ''
    for user_id in user_ids:
        user_ids_string += ("\'%s\'," % user_id)
    user_ids_string = user_ids_string[:-1]
    prepared_string = "update push_auth_token set authenticated=false where user_id in (%s)" % (user_ids_string)
    log.info('deauthing users: %s' % prepared_string)
    db.engine.execute(prepared_string)  # safe


def validate_auth_token(user_id, auth_token):
    """compare the given auth token and user_id to the one stored in the db"""
    obj = get_token_obj_by_user_id(user_id)
    if str(obj.auth_token) == auth_token:
        return True
    log.error('auth token validation failed for user_id %s and token %s' % (user_id, auth_token))
    return False
