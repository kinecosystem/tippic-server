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

    def test_picture_delivery(self):
        """Test getting correct picture"""

        # - call /user/picture without user_id - 400
        resp = self.app.get('/user/picture')
        self.assertEqual(resp.status_code, 400)

        # - create an *ios* Tippic user
        # register a user
        userid = uuid.uuid4()
        resp = self.app.post('/user/register',
                             data=json.dumps({
                                 'user_id': str(userid),
                                 'os': 'iOS',
                                 'device_model': 'iPhone X',
                                 'device_id': '234234',
                                 'time_zone': '05:00',
                                 'token': 'fake_token',
                                 'app_ver': '1.0'}),
                             headers={},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        picture_1 = {
            "skip_image_test": "true",
            "author": {
                "user_id": str(userid),
                "public_address": "GCNP7H4K7QZOBG3K7CSTHBFB4COHQHOLRM7PAZVFS5VF4OPKNN4YPCMS"
            },
            "image_url": "https://instagram.fsdv3-1.fna.fbcdn.net/vp/7af826e069bdbdc63dd443f3362e1d7a/5CACB7A9/t51.2885-15/e35/44676676_164229534532236_4062427518663301553_n.jpg",
            "title": "Random Dogs Band",
            "picture_order_index": 1
        }

        # - call /user/picture  - 400
        resp = self.app.get('/user/picture',
                            headers={USER_ID_HEADER: str(userid)},
                            content_type='application/json')
        self.assertEqual(resp.status_code, 403)

        # - ack new user
        db.engine.execute(
            """update public.push_auth_token set auth_token='%s' where user_id='%s';""" % (str(userid), str(userid)))
        resp = self.app.post('/user/auth/ack',
                             data=json.dumps({
                                 'token': str(userid)}),
                             headers={USER_ID_HEADER: str(userid)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # userid updates his phone number to the server after client-side verification
        phone_num = '+9720528802120'
        resp = self.app.post('/user/firebase/update-id-token',
                             data=json.dumps({
                                 'token': 'fake-token',
                                 'phone_number': phone_num}),
                             headers={USER_ID_HEADER: str(userid)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # - call /user/picture - 200 - no pictures
        resp = self.app.get('/user/picture',
                            headers={USER_ID_HEADER: str(userid)},
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data, {'picture': {}})

        # get viewed picture summery
        resp = self.app.get('/user/pictures-summery',
                            headers={USER_ID_HEADER: str(userid)},
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['summery'], [])

        # add a picture
        resp = self.app.post('/picture',
                             data=json.dumps({
                                 'picture': picture_1}),
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # call /user/picture - picture id 1 returns
        resp = self.app.get('/user/picture',
                            headers={USER_ID_HEADER: str(userid)},
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['picture']['image_url'], picture_1['image_url'])

        # get viewed picture summery
        resp = self.app.get('/user/pictures-summery',
                            headers={USER_ID_HEADER: str(userid)},
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['summery'][0]['image_url'], picture_1['image_url'])

        # user 1 blocks himself
        resp = self.app.post('/user/block',
                             data=json.dumps({
                                 'user_id': str(userid)}),
                             headers={USER_ID_HEADER: str(userid)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "ok")

        # call /user/picture - no pictures returned
        resp = self.app.get('/user/picture',
                            headers={USER_ID_HEADER: str(userid)},
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data, {'error': 'blocked_user'})

        # - skip user
        resp = self.app.post('/skip_picture',
                             data=json.dumps({
                                 'skip_by': '1'
                             }),
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # - call /user/picture - no pictures
        resp = self.app.get('/user/picture',
                            headers={USER_ID_HEADER: str(userid)},
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data, {'picture': {}})

        # - create a new *ios* Tippic user2
        # register a user
        userid2 = uuid.uuid4()
        resp = self.app.post('/user/register',
                             data=json.dumps({
                                 'user_id': str(userid2),
                                 'os': 'iOS',
                                 'device_model': 'iPhone X',
                                 'device_id': '134234',
                                 'time_zone': '05:00',
                                 'token': 'fake_token',
                                 'app_ver': '1.0'}),
                             headers={},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        # - ack new user
        db.engine.execute(
            """update public.push_auth_token set auth_token='%s' where user_id='%s';""" % (str(userid2), str(userid2)))
        resp = self.app.post('/user/auth/ack',
                             data=json.dumps({
                                 'token': str(userid2)}),
                             headers={USER_ID_HEADER: str(userid2)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # userid updates his phone number to the server after client-side verification
        phone_num = '+9720528802121'
        resp = self.app.post('/user/firebase/update-id-token',
                             data=json.dumps({
                                 'token': 'fake-token',
                                 'phone_number': phone_num}),
                             headers={USER_ID_HEADER: str(userid2)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        picture_2 = {
            "author": {
                "user_id": str(userid2),
                "public_address": "GAVIE7DPX3M2OOW3XBL2R5V5NHCVUJMHV6WSJVMNYK6YN4IB2GWRKYRQ"
            },
            "image_url": "https://instagram.fsdv3-1.fna.fbcdn.net/vp/7af826e069bdbdc63dd443f3362e1d7a/5CACB7A9/t51.2885-15/e35/44676676_164229534532236_4062427518663301553_n.jpg",
            "title": "Random Cats Band",
            "picture_order_index": 2
        }

        # - add a picture
        resp = self.app.post('/picture',
                             data=json.dumps({
                                 'picture': picture_2}),
                             headers={},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # call /user/picture  - picture id 2 returns
        resp = self.app.get('/user/picture',
                            headers={USER_ID_HEADER: str(userid)},
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['picture']['image_url'], picture_2['image_url'])

        # - call /user/picture  - picture id 2 returns
        resp = self.app.get('/user/picture',
                            headers={USER_ID_HEADER: str(userid2)},
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        picture_data = json.loads(resp.data)['picture']
        print(picture_data)
        self.assertEqual(picture_data['image_url'], picture_2['image_url'])

        # - report picture
        resp = self.app.post('/user/picture/report',
                             data=json.dumps({
                                 'picture_id': picture_data['picture_id']
                             }),
                             headers={USER_ID_HEADER: str(userid)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "ok")

        # - report same picture again - should fail
        resp = self.app.post('/user/picture/report',
                             data=json.dumps({
                                 'picture_id': picture_data['picture_id']
                             }),
                             headers={USER_ID_HEADER: str(userid)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)
        self.assertEqual(data['status'], "failed")

        # - skip picture again
        resp = self.app.post('/skip_picture',
                             data=json.dumps({
                                 'skip_by': '1'
                             }), content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # - call /user/picture  - no more pictures after skip
        resp = self.app.get('/user/picture',
                            headers={USER_ID_HEADER: str(userid2)},
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        print(data)

        self.assertEqual(data, {'picture': {}})


if __name__ == '__main__':
    unittest.main()
