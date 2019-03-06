import json
import unittest
import uuid

import testing.postgresql
from stellar_base.keypair import Keypair

import tippicserver
from tippicserver import db

from tippicserver import stellar
from tippicserver.stellar import get_initial_reward

import logging as log
log.getLogger().setLevel(log.INFO)


USER_ID_HEADER = "X-USERID"


class Tester(unittest.TestCase):

    #@mock.patch('redis.StrictRedis', mockredis.mock_redis_client)
    def setUp(self):
        #overwrite the db name, dont interfere with stage db data
        self.postgresql = testing.postgresql.Postgresql()
        tippicserver.app.config['SQLALCHEMY_DATABASE_URI'] = self.postgresql.url()
        tippicserver.app.testing = True
        #tippicserver.app.redis = redis.StrictRedis(host='0.0.0.0', port=6379, db=0) # doesnt play well with redis-lock
        self.app = tippicserver.app.test_client()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        self.postgresql.stop()

    def test_discovery_apps_api(self):
        """ test discover app endpoints """
        demo_app = {
            "category_name": "Beauty",
            "identifier": "com.perfect365",
            "platform": "android",
            "tags": ["sport", "diet", "healthy"],
            "meta_data": {
                "earn_title": "get look pack",
                "card_image_url": "https://….png",
                "app_url": "https://play.google.com/store/apps/details?id=org.kinecosystem.kinit&hl=en",
                "earn_info": "Kin can be spent on premium emotions...",
                "icon_url": "https://…..jpg",
                "about_info": "Ask questions to the community.",
                "swipe_images_url": [
                    "https://cdn.kinitapp.com/brand_img/amazon.png",
                    "https://cdn.kinitapp.com/brand_img/soyummy.jpg",
                    "https://cdn.kinitapp.com/brand_img/amagon.png",
                ]
            }
        }

        #add android app
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
        self.assertEqual(len(data['apps'][0]['platform']), 'android')




if __name__ == '__main__':
    unittest.main()
