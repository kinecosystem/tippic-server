import arrow

from kinappserver import db
from kinappserver.models import UserAppData
from kinappserver.utils import InvalidUsage


class Picture(db.Model):
    """
    the represents a single picture
    """
    picture_id = db.Column(db.String(40), nullable=False, primary_key=True)
    picture_order_index = db.Column(db.Integer(), nullable=False, primary_key=False)
    title = db.Column(db.String(80), nullable=False, primary_key=False)
    image_url = db.Column(db.String(200), nullable=False, primary_key=False)
    author = db.Column(db.JSON)
    min_client_version_ios = db.Column(db.String(10), nullable=False, primary_key=False)
    delay_days = db.Column(db.Integer(), nullable=False, primary_key=False)
    update_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())
    is_active = db.Column(db.Boolean, unique=False, default=True)

    def __repr__(self):
        return '<picture_id: %s, min_client_version_ios: %s, delay_days: %s>' % \
               (self.picture_id, self.min_client_version_ios, self.delay_days)


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
    return picture_json


def get_picture_for_user(user_id):
    """ get next picture for this user"""
    user_app_data = UserAppData.query.filter_by(user_id=user_id).first()
    if not user_app_data:
        raise InvalidUsage('no such user_id')

    if user_app_data.completed_picture is None:
        # deliver the first image in the order
        current_picture = Picture.query.order_by(Picture.picture_order_index).first()
        # we might not have images in the db at all
        if current_picture is None:
            return {}

        picture_json = picture_to_json(current_picture)
        # store the delivered image information
        user_app_data.completed_picture = {
            "picture_id": current_picture.picture_id,
            "picture_order_index": current_picture.picture_order_index,
            "timestamp": arrow.utcnow().timestamp
        }
        try:
            db.session.add(user_app_data)
            db.session.commit()
        except Exception as e:
            print(e)
            print('cant get_picture_for_user with user_id %s' % user_id)
            return {}
        return picture_json
    else:
        # if timestamp of current delivered picture + delay_time > current 
        # deliver the next image in order
        current_picture = Picture.query.filter_by(picture_id=user_app_data.completed_picture['picture_id']).first()

        now = arrow.utcnow()
        pictures_deliver_time = arrow.get(user_app_data.completed_picture['timestamp'])
        delay_passed = True if pictures_deliver_time.shift(days=current_picture.delay_days) <= now else False

        if delay_passed:
            new_picture = Picture.query.filter_by(picture_id=user_app_data.completed_picture['picture_id'] + 1).first()
            # do we have any more pictures to show?
            if not new_picture:
                return {}
        
            picture_json = picture_to_json(new_picture)
            # store the delivered image information
            user_app_data.completed_picture = {
                "picture_id": current_picture.picture_id,
                "picture_order_index": current_picture.picture_order_index,
                "timestamp": arrow.utcnow().timestamp
            }
            try:
                db.session.add(user_app_data)
                db.session.commit()
            except Exception as e:
                print(e)
                print('cant get_picture_for_user with user_id %s' % user_id)
                return {}
            return picture_json
        else:
            return picture_to_json(current_picture)


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


def add_picture(picture_json, set_active=True):
    """adds an picture to the db"""
    print(picture_json)
    try:
        picture = Picture()
        picture.picture_id = picture_json['picture_id']
        picture.title = picture_json['title']
        picture.image_url = picture_json['image_url']
        picture.author = picture_json['author']
        picture.picture_order_index = picture_json['picture_order_index']
        picture.min_client_version_ios = picture_json['min_client_version_ios']
        picture.delay_days = picture_json['delay_days']

        db.session.add(picture)
        db.session.commit()
    except Exception as e:
        print(e)
        print('cant add picture to db with picture_id %s' % picture_json['picture_id'])
        return False
    else:
        if set_active:
            set_picture_active(picture_json['picture_id'], True)
        return True
