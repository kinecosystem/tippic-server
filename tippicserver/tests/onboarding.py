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

    
    def test_onboard(self):
        """test onboarding scenarios"""
        # onboard 2 different user ids with the same phone number
        # both should succeed but user should get 15 Kin only once
        paddr = self.onboard_with_phone(str(uuid.uuid4()), '+9720528802120')
        self.assertEqual(get_initial_reward(), stellar.get_kin_balance(paddr))
        paddr = self.onboard_with_phone( str(uuid.uuid4()), '+9720528802120')
        self.assertEqual(0, stellar.get_kin_balance(paddr))

    def onboard_with_phone(self, userid, phone_num):
        resp = self.app.post('/user/register',
            data=json.dumps({
                            'user_id': str(userid),
                            'os': 'android',
                            'device_model': 'samsung8',
                            'device_id': '234234',
                            'time_zone': '05:00',
                            'token': 'fake_token',
                            'app_ver': '1.0'}),
            headers={},
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # phone authenticate

        resp = self.app.post('/user/firebase/update-id-token',
                    data=json.dumps({
                        'token': 'fake-token',
                        'phone_number': phone_num}),
                    headers={USER_ID_HEADER: str(userid)},
                    content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        print('onboarding user --------------')
        kp = Keypair.random()
        paddr = kp.address().decode()
        resp = self.app.post('/user/onboard',
            data=json.dumps({
                            'public_address': paddr}),
            headers={USER_ID_HEADER: str(userid)},
            content_type='application/json')

        print(json.loads(resp.data))
        self.assertEqual(resp.status_code, 200)

        # try onboarding again with the same user - should fail
        print('onboarding same user second time should fail --------------')
        resp = self.app.post('/user/onboard',
            data=json.dumps({
                            'public_address': kp.address().decode()}),
            headers={USER_ID_HEADER: str(userid)},
            content_type='application/json')
        print(json.loads(resp.data))
        self.assertEqual(resp.status_code, 400)

        return paddr


if __name__ == '__main__':
    unittest.main()
