import json

from tippicserver import db
from tippicserver.models import SystemConfig, User, UUIDType, get_user_app_data, Transaction
from tippicserver.utils import InvalidUsage
from tippicserver.models.user import get_address_by_userid, set_username,get_user


class ReportedPictures(db.Model):
    picture_id = db.Column(db.String(40), nullable=False, primary_key=True)
    reporter_id = db.Column('user_id', UUIDType(binary=False), db.ForeignKey("user.user_id"), primary_key=True,
                            nullable=False)
    update_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())


def report_picture(user_id, picture_id):
    """ report a picture """
    print("reporting picture_id = %s" % picture_id)

    reported_picture = ReportedPictures()
    try:
        reported_picture.picture_id = picture_id.lower()
        reported_picture.reporter_id = user_id.lower()
        db.session.add(reported_picture)
        db.session.commit()
    except Exception as e:
        print(e)
        print(str(e.__traceback__))
        print('cant add pictureReport to db with picture_id %s' % picture_id)
        return False
    else:
        return True


class Picture(db.Model):
    """
    the represents a single picture
    """
    picture_id = db.Column(db.String(40), nullable=False, primary_key=True)
    picture_order_index = db.Column(db.Integer(), nullable=False, primary_key=False)
    title = db.Column(db.String(80), nullable=False, primary_key=False)
    image_url = db.Column(db.String(200), nullable=False, primary_key=False)
    author = db.Column(db.JSON)
    update_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())
    is_active = db.Column(db.Boolean, unique=False, default=True)

    def __repr__(self):
        return '<picture_id: %s, ' \
               'picture_order_index: %s,' \
               'title: %s,' \
               'author: %s, ' \
               'image_url: %s>' % (self.picture_id, self.picture_order_index,self.title, self.author, self.image_url)


def picture_to_json(picture):
    """converts the given picture object to a json-representation"""
    if not picture:
        return {}
    # build the json object:
    picture_json = {}
    picture_json['picture_id'] = picture.picture_id
    picture_json['title'] = picture.title
    picture_json['image_url'] = picture.image_url
    picture_json['author'] = picture.author

    # add picture author name
    user = User.query.filter_by(user_id=picture.author['user_id']).first()
    if user:
        picture_json['author']['name'] = user.username

    return picture_json


def get_pictures_summery(user_id):
    """ return a list of shown pictures and tips sum for each"""

    # get current shown picture order index
    # loop from 0 to index
    # for each get - if picture author is this user - get the id
    # for each id, sum tips from transactions table
    system_config = SystemConfig.query.first()
    if system_config is not None:
        current_picture_index = system_config.current_picture_index
        pictures = Picture.query.filter(Picture.picture_order_index <= current_picture_index).all()
        user_pictures = [picture_to_json(item) for item in pictures if item.author['user_id'] == user_id]
        for picture in user_pictures:
            total = db.engine.execute(
                "select sum(amount) as total from Transaction where tx_for_item_id = '%s'" % picture['picture_id'])
            picture['tips_sum'] = total.first()['total'] or 0
        return user_pictures
    return []


def get_picture_for_user(user_id):
    """ get next picture for this user"""
    system_config = SystemConfig.query.first()
    user_app_data = get_user_app_data(user_id)

    if system_config is None:
        # deliver the first image in the order
        new_picture = Picture.query.order_by(Picture.picture_order_index).first()
        # we might not have images in the db at all
        if new_picture is None:
            return {}
        # if user is blocked, return error message
        if user_app_data and user_app_data.blocked_users \
                and new_picture.author['user_id'] in user_app_data.blocked_users:
            return {"blocked": True}

        try:
            # store the delivered image information
            system_config = SystemConfig()
            system_config.current_picture_index = new_picture.picture_order_index
            db.session.add(system_config)
            db.session.commit()
        except Exception as e:
            print(e)
            print('cant get_picture_for_user with user_id %s' % user_id)
            return {}
        return picture_to_json(new_picture)
    else:
        # TODO: cache this
        # deliver the current picture
        new_picture = Picture.query.filter_by(picture_order_index=system_config.current_picture_index).first()

        if not new_picture:
            return {}

        if user_app_data and user_app_data.blocked_users \
                and new_picture.author['user_id'] in user_app_data.blocked_users:
            return {"blocked": True}

        return picture_to_json(new_picture)


def set_picture_active(picture_id, is_active):
    """enable/disable picture by offer_id"""
    picture = Picture.query.filter_by(picture_id=picture_id).first()
    if not picture:
        raise InvalidUsage('no such picture_id')
    picture.is_active = is_active
    try:
        db.session.add(picture)
        db.session.commit()
    except Exception as e:
        print(e)
        print('cant set_picture_active with picture_id %s' % picture_id)
        return False

    return True

def get_current_order_index():
    return db.session.query(db.func.max(Picture.picture_order_index)).scalar() or 0


def add_picture(picture_json, set_active=True):
    """adds an picture to the db"""
    import uuid, json
    print(picture_json)

    picture = Picture()
    try:
        picture.picture_id = str(uuid.uuid4())
        picture.title = picture_json['title']
        picture.image_url = picture_json['image_url']
        picture.author = {
            'user_id': picture_json['user_id'],
            'public_address': get_address_by_userid(picture_json['user_id'])
        }
        picture.picture_order_index = get_current_order_index() + 1

        db.session.add(picture)
        db.session.commit()

        if not get_user(picture_json['user_id']).username:
            set_username(picture_json['user_id'], picture_json['username'])
    except Exception as e:
        print(e)
        print('cant add picture to db with picture_id %s' % picture.picture_id)
        return e
    else:
        if set_active:
            set_picture_active(picture.picture_id, True)
        return True
