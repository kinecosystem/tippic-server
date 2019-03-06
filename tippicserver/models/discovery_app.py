
import datetime
import logging as log
from tippicserver import db


class DiscoveryApp(db.Model):
    """email templates for various uses"""
    identifier = db.Column(db.String(40), primary_key=True, nullable=False)
    category_name = db.Column(db.String(40), primary_key=True, nullable=False)
    platform = db.Column(db.String(10), primary_key=True, nullable=False)
    tags = db.Column(db.JSON())
    meta_data = db.Column(db.JSON())
    
    
    def __repr__(self):
        return '<identifier: %s, category_name: %s, platform: %s, tags: %s, meta_data: %s>' % (self.identifier, self.category_name, self.platform, self.tags, self.meta_data)


def get_discovery_apps(app_identifier, platform):
    """ returns a list of avaliable discovery apps for specific platform """
    apps = DiscoveryApp.query.all()
    result = [app_to_json(app) for app in apps]

    if app_identifier is not None:
        result = filter(
            lambda app: app['identifier'] != app_identifier, result)
    if platform is not None:
        result = filter(
            lambda app: app['platform'] == platform, result)



def app_to_json(app):
    """convert app to a json format"""
    import json
    json_app = {}
    meta_data = app.meta_data

    json_app['category_name'] = app.category_name
    json_app['identifier'] = app.identifier
    json_app['tags'] = app.tags
    json_app['earn_title'] = meta_data['earn_title']
    json_app['card_image_url'] = meta_data['card_image_url']
    json_app['app_url'] = meta_data['app_url']
    json_app['earn_info'] = meta_data['earn_info']
    json_app['icon_url'] = meta_data['icon_url']
    json_app['about_info'] = meta_data['about_info']
    json_app['swipe_images_url'] = meta_data['swipe_images_url']

    return json_app
    

def add_app(json_app):
    """ add app to db"""

    new_app = DiscoveryApp()
    new_app['category_name'] = json_app['category_name']
    new_app['identifier'] = json_app['identifier']
    new_app['platform'] = json_app['platform']
    new_app['tags'] = json_app['tags']
    new_app['meta_data'] = json_app['meta_data']

    db.session.add(new_app)
    db.session.commit()

    return True
