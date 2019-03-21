import json
import logging as log
import unittest

import testing.postgresql

import tippicserver
from tippicserver import db

log.getLogger().setLevel(log.INFO)

USER_ID_HEADER = "X-USERID"


class Tester(unittest.TestCase):

    # @mock.patch('redis.StrictRedis', mockredis.mock_redis_client)
    def setUp(self):
        # overwrite the db name, dont interfere with stage db data
        self.postgresql = testing.postgresql.Postgresql()
        tippicserver.app.config['SQLALCHEMY_DATABASE_URI'] = self.postgresql.url(
        )
        tippicserver.app.testing = True
        # tippicserver.app.redis = redis.StrictRedis(host='0.0.0.0', port=6379, db=0) # doesnt play well with redis-lock
        self.app = tippicserver.app.test_client()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        self.postgresql.stop()

    def test_discovery_apps_api(self):
        """ test discover app endpoints """
        demo_app = {
            "identifier": "kinnyco.kinnyapp",
            "category_name": "Social",
            "platform": "android",
            "meta_data": {
                "about_app": "Kinny enables users to earn Kin in-app and send and receive Kin through social media.",
                "app_name": "Kinny",
                "app_url": "https://play.google.com/store/apps/details?id=kinnyco.kinnyapp",
                "card_data": {
                    "font_letter_spacing": "0f",
                    "font_line_spacing": "3f",
                    "font_name": "AmericanTypewriter",
                    "font_size": "21f",
                    "background_color": "#2675fe",
                    "title": "Tip friends on social media"
                },
                "experience_data": {
                    "about": "Sync your Reddit, Twitter and Discord accounts and start tipping your friends with Kin.",
                    "howto": "Create your kinny tip wallet and use the @kinnytips or u/kinnytips tag in a comment to send your friends Kin.",
                    "title": "Comment to tip your friends"
                },
                "icon_url": "https://cdn.kinitapp.com/discovery/reveald/logo/android/xxhdpi/Logo_reveald.png",
                "images": [
                    "https://cdn.kinitapp.com/discovery/reveald/android/xxhdpi/app_image_1.jpg",
                    "https://cdn.kinitapp.com/discovery/reveald/android/xxhdpi/app_image_2.jpg",
                ]
            }
        }


        # add android app
        resp = self.app.post(
            '/discovery/add_app', data=json.dumps({'app': demo_app}), content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        demo_app['platform'] = 'ios'
        # add ios app
        resp = self.app.post(
            '/discovery/add_app', data=json.dumps({'app': demo_app}), content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        resp = self.app.get('/discovery/get_apps',
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data['apps']), 2)

        resp = self.app.get('/discovery/get_apps?identifier=' + demo_app['identifier'],
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data['apps']), 0)

        resp = self.app.get('/discovery/get_apps?platform=android',
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data['apps']), 1)
        self.assertEqual(data['apps'][0]['platform'], 'android')


if __name__ == '__main__':
    unittest.main()
