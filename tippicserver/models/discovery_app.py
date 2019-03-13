import logging as log

from tippicserver import db


class DiscoveryApp(db.Model):
    """email templates for various uses"""
    sid = db.Column(db.Integer(), db.Sequence(
        'discovery_app_sid', start=1, increment=1), primary_key=True)
    identifier = db.Column(db.String(40), primary_key=False, nullable=False)
    category_name = db.Column(db.String(40), primary_key=False, nullable=False)
    platform = db.Column(db.String(10), primary_key=False, nullable=False)
    meta_data = db.Column(db.JSON())
    transfer_data = db.Column(db.JSON())

    def __repr__(self):
        return '<identifier: %s, category_name: %s, platform: %s, tags: %s, meta_data: %s>' % (
            self.identifier, self.category_name, self.platform, self.tags, self.meta_data)


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

    return list(result)


def app_to_json(app):
    """convert app to a json format"""
    json_app = {}

    json_app['category_name'] = app.category_name
    json_app['identifier'] = app.identifier
    json_app['platform'] = app.platform
    json_app['meta_data'] = app.meta_data
    
    if app.transfer_data:
        json_app['transfer_data'] = app.transfer_data

    return json_app


def add_app(json_app):
    """ add app to db"""
    try:
        new_app = DiscoveryApp()

        new_app.category_name = json_app['category_name']
        new_app.identifier = json_app['identifier']
        new_app.platform = json_app['platform']
        new_app.meta_data = json_app['meta_data']
        new_app.transfer_data = json_app['transfer_data']

        db.session.add(new_app)
        db.session.commit()

    except Exception as e:
        print(e)
        log.error('cant add app to db with id %s' % json_app['identifier'])
    else:
        log.info('created app with id: %s' % json_app['identifier'])
        return True

    return False
