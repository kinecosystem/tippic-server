import json
import unittest
import uuid

import testing.postgresql
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

    def test_users_endpoints(self):
        """ Test setting user's username """

        # - create a user
        # register a user
        user_1 = uuid.uuid4()
        resp = self.app.post('/user/register',
                             data=json.dumps({
                                 'user_id': str(user_1),
                                 'os': 'iOS',
                                 'device_model': 'iPhone X',
                                 'device_id': '234234',
                                 'time_zone': '05:00',
                                 'token': 'fake_token',
                                 'app_ver': '1.0'}),
                             headers={},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # userid updates his phone number to the server after client-side verification
        phone_num = '+9720528802120'
        resp = self.app.post('/user/firebase/update-id-token',
                             data=json.dumps({
                                 'token': 'fake-token',
                                 'phone_number': phone_num}),
                             headers={USER_ID_HEADER: str(user_1)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # - create a user
        # register a user
        user_2 = uuid.uuid4()
        resp = self.app.post('/user/register',
                             data=json.dumps({
                                 'user_id': str(user_2),
                                 'os': 'iOS',
                                 'device_model': 'iPhone X',
                                 'device_id': '234234',
                                 'time_zone': '05:00',
                                 'token': 'fake_token',
                                 'app_ver': '1.0'}),
                             headers={},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # userid updates his phone number to the server after client-side verification
        phone_num = '+9720528802121'
        resp = self.app.post('/user/firebase/update-id-token',
                             data=json.dumps({
                                 'token': 'fake-token',
                                 'phone_number': phone_num}),
                             headers={USER_ID_HEADER: str(user_2)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # - create a user
        # register a user
        user_3 = uuid.uuid4()
        resp = self.app.post('/user/register',
                             data=json.dumps({
                                 'user_id': str(user_3),
                                 'os': 'iOS',
                                 'device_model': 'iPhone X',
                                 'device_id': '234234',
                                 'time_zone': '05:00',
                                 'token': 'fake_token',
                                 'app_ver': '1.0'}),
                             headers={},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # userid updates his phone number to the server after client-side verification
        phone_num = '+9720528802122'
        resp = self.app.post('/user/firebase/update-id-token',
                             data=json.dumps({
                                 'token': 'fake-token',
                                 'phone_number': phone_num}),
                             headers={USER_ID_HEADER: str(user_3)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # set username for user_1
        resp = self.app.post('/user/username',
                             data=json.dumps({
                                 'username': 'Baba Yaga'}),
                             headers={USER_ID_HEADER: str(user_1)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "ok")

        # set username for user_1
        resp = self.app.post('/user/username',
                             data=json.dumps({
                                 'username': 'The Boogeyman'}),
                             headers={USER_ID_HEADER: str(user_1)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "ok")

        # set username for user_2 same as user_1 - should fail
        resp = self.app.post('/user/username',
                             data=json.dumps({
                                 'username': 'The Boogeyman'}),
                             headers={USER_ID_HEADER: str(user_2)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "failed")

        # set username for user_2
        resp = self.app.post('/user/username',
                             data=json.dumps({
                                 'username': 'Baba Yaga'}),
                             headers={USER_ID_HEADER: str(user_2)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "ok")

        # set username for user_2
        resp = self.app.post('/user/username',
                             data=json.dumps({
                                 'username': 'Baba Yaga'}),
                             headers={USER_ID_HEADER: str(user_3)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "failed")

        # set username for user_3
        resp = self.app.post('/user/username',
                             data=json.dumps({
                                 'username': 'Slark'}),
                             headers={USER_ID_HEADER: str(user_3)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "ok")

        # user 1 blocks user 2
        resp = self.app.post('/user/block',
                             data=json.dumps({
                                 'user_id': str(user_2)}),
                             headers={USER_ID_HEADER: str(user_1)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "ok")

        # user 1 blocks user 3
        resp = self.app.post('/user/block',
                             data=json.dumps({
                                 'user_id': str(user_3)}),
                             headers={USER_ID_HEADER: str(user_1)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "ok")

        # user 1 gets blocked list
        resp = self.app.get('/user/block-list',
                            headers={USER_ID_HEADER: str(user_1)},
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual([{"user_id": str(user_2), "username": "Baba Yaga"}, {"user_id": str(user_3),"username": "Slark"}], data)

        # user 1 unblocks user 2
        resp = self.app.post('/user/unblock',
                             data=json.dumps({
                                 'user_id': str(user_2)}),
                             headers={USER_ID_HEADER: str(user_1)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "ok")

        # user 1 unblocks user 3
        resp = self.app.post('/user/unblock',
                             data=json.dumps({
                                 'user_id': str(user_3)}),
                             headers={USER_ID_HEADER: str(user_1)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "ok")

        # user 1 gets blocked list
        resp = self.app.get('/user/block-list',
                            headers={USER_ID_HEADER: str(user_1)},
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data, [])


if __name__ == '__main__':
    unittest.main()
