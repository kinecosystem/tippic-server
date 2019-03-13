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
            "identifier": "com.perfect365",
            "category_name": "Beauty",
            "platform": "android",
            "meta_data": {
                "app_name": "Kinit",
                "app_url": "https://play.google.com/store/apps/details?id=org.kinecosystem.kinit&hl=en",
                "icon_url": "https://cdn.kinitapp.com/discovery/tippic/logo/Logo_tippic.png",
                "about_app": "Donec pharetra convallis nisi, ut imperdiet justo mollis eget. Nulla non ex vitae velit molestie tincidunt.",
                "experience_data": {
                    "title": "Unlock you life!",
                    "about": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed ornare nunc mauris, nec lobortis dui venenatis sed. In hac habitasse platea dictumst. Sed in convallis risus. Vestibulum pharetra pretium blandit.",
                    "howto": "Etiam posuere orci convallis varius egestas. Fusce id metus sodales, semper libero vitae, ornare eros."
                },
                "card_data": {
                    "title": "Play Trivia & arn Kin",
                    "text_color": "#FFFFF",
                    "font_name": "typeCaveat",
                    "font_size": "12.5f",
                    "font_line_spacing": "0f",
                    "font_letter_spacing": "0f"
                },
                "images": [
                    "https://cdn.kinitapp.com/discovery/tippic/Tippic1.jpg",
                    "https://cdn.kinitapp.com/discovery/tippic/Tippic2.jpg",
                    "https://cdn.kinitapp.com/discovery/tippic/Tippic3.jpg"
                ]
            },
            "transfer_data": {
                "launch_activity": "com.kin.ecosystem.transfer.view.AccountInfoActivity"
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

        resp = self.app.get('/discovery/get_apps?identifier=com.perfect365',
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
