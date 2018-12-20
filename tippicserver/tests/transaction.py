import json
import unittest
import uuid

import testing.postgresql
from flask_api.status import HTTP_403_FORBIDDEN

import tippicserver
from tippicserver import db

USER_ID_HEADER = "X-USERID"


class Tester(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        # overwrite the db name, dont interfere with stage db data
        self.postgresql = testing.postgresql.Postgresql()
        tippicserver.app.config['SQLALCHEMY_DATABASE_URI'] = self.postgresql.url()
        tippicserver.app.testing = True
        self.app = tippicserver.app.test_client()
        db.drop_all()
        db.create_all()
        tippicserver.config.PHONE_VERIFICATION_REQUIRED = True

    def tearDown(self):
        self.postgresql.stop()

    def test_transaction_reporting(self):
        """ Test transactions reporting api """

        # call /user/transaction/report without user
        resp = self.app.post('/user/transaction/report')
        self.assertEqual(resp.status_code, 400)

        # call /user/transaction/report with un auth'ed user
        resp = self.app.post('/user/transaction/report',
                             headers={USER_ID_HEADER: str(uuid.uuid4())},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 400)

        # register a user
        user_id = uuid.uuid4()
        resp = self.app.post('/user/register',
                             data=json.dumps({
                                 'user_id': str(user_id),
                                 'os': 'iOS',
                                 'device_model': 'iPhone X',
                                 'device_id': '234234',
                                 'time_zone': '05:00',
                                 'token': 'fake_token',
                                 'app_ver': '1.0'}),
                             headers={},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # call /user/transaction/report with bad payload
        resp = self.app.post('/user/transaction/report',
                             headers={USER_ID_HEADER: user_id},
                             content_type='application/json')
        self.assertEqual(resp.status_code, HTTP_403_FORBIDDEN)

        # userid updates his phone number to the server after client-side verification
        phone_num = '+9720528802120'
        resp = self.app.post('/user/firebase/update-id-token',
                             data=json.dumps({
                                 'token': 'fake-token',
                                 'phone_number': phone_num}),
                             headers={USER_ID_HEADER: str(user_id)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # call /user/transaction/report - should succeed
        resp = self.app.post('/user/transaction/report',
                             data=json.dumps(
                                 {
                                     "tx_hash": "f868b0c8e7d97fcaa1e651e6ea2d1c6d0a2fef738fab615a1906f4b0c883bc8f",
                                     "amount": 5,
                                     "to_address": "GCTWHWZASR3QPR4D2WAVFDIIVZF4VXKAT2NYB7ZNTTWHOA63KWX3B4DA",
                                     "id": "1",
                                     "type": "picture"
                                 }),
                             headers={USER_ID_HEADER: str(user_id)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['status'], 'ok')

        # call /user/transaction/report with the same tx_ hash - should fail
        resp = self.app.post('/user/transaction/report',
                             data=json.dumps(
                                 {
                                     "tx_hash": "f868b0c8e7d97fcaa1e651e6ea2d1c6d0a2fef738fab615a1906f4b0c883bc8f",
                                     "amount": 5,
                                     "to_address": "GCTWHWZASR3QPR4D2WAVFDIIVZF4VXKAT2NYB7ZNTTWHOA63KWX3B4DA",
                                     "id": "1",
                                     "type": "picture"
                                 }),
                             headers={USER_ID_HEADER: str(user_id)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 400)

        # call /user/transaction/report with the invalid tx_ hash - should fail
        resp = self.app.post('/user/transaction/report',
                             data=json.dumps(
                                 {
                                     "tx_hash": "f868ABCe7d97fcaa1e651e6ea2d1c6d0a2fef738fab615a1906f4b0c883bc8f",
                                     "amount": 5,
                                     "to_address": "GCTWHWZASR3QPR4D2WAVFDIIVZF4VXKAT2NYB7ZNTTWHOA63KWX3B4DA",
                                     "id": "1",
                                     "type": "picture"
                                 }),
                             headers={USER_ID_HEADER: str(user_id)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
