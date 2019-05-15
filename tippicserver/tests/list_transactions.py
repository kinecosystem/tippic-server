import simplejson as json
from uuid import uuid4
from time import sleep
import testing.postgresql
from stellar_base.keypair import Keypair
import unittest
import tippicserver
from tippicserver import db, stellar, models
from tippicserver.stellar import get_initial_reward
from tippicserver.utils import APP_TO_APP, PICTURE, GIFT, GIVE_TIP, GET_TIP
from tippicserver.models import get_address_by_userid

import logging as log
log.getLogger().setLevel(log.INFO)


USER_ID_HEADER = "X-USERID"


class Tester(unittest.TestCase):
    """tests the entire spend-scenario: creating an order and then redeeming it"""

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        # overwrite the db name, dont interfere with stage db data
        self.postgresql = testing.postgresql.Postgresql()
        tippicserver.app.config['SQLALCHEMY_DATABASE_URI'] = self.postgresql.url(
        )
        tippicserver.app.testing = True
        self.app = tippicserver.app.test_client()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        self.postgresql.stop()

    def test_listing_transactions(self):
        """test listing transactions"""

        # register a couple of users
        userid1 = uuid4()
        resp = self.app.post('/user/register',
                             data=json.dumps({
                                 'user_id': str(userid1),
                                 'os': 'android',
                                 'device_model': 'samsung8',
                                 'device_id': '234234',
                                 'time_zone': '05:00',
                                 'token': 'fake_token',
                                 'app_ver': '1.0'}),
                             headers={},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        db.engine.execute("""update public.push_auth_token set auth_token='%s' where user_id='%s';""" % (
            str(userid1), str(userid1)))

        resp = self.app.post('/user/auth/ack',
                             data=json.dumps({
                                 'token': str(userid1)}),
                             headers={USER_ID_HEADER: str(userid1)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        userid2 = uuid4()
        resp = self.app.post('/user/register',
                             data=json.dumps({
                                 'user_id': str(userid2),
                                 'os': 'android',
                                 'device_model': 'samsung8',
                                 'device_id': '234234',
                                 'time_zone': '05:00',
                                 'token': 'fake_token',
                                 'app_ver': '1.0'}),
                             headers={},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        db.engine.execute("""update public.push_auth_token set auth_token='%s' where user_id='%s';""" % (
            str(userid2), str(userid2)))

        resp = self.app.post('/user/auth/ack',
                             data=json.dumps({
                                 'token': str(userid2)}),
                             headers={USER_ID_HEADER: str(userid2)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # onboard user 1 to set address in server
        kp = Keypair.random()
        address1 = kp.address().decode()
        resp = self.app.post('/user/onboard',
                             data=json.dumps({
                                 'public_address': address1}),
                             headers={USER_ID_HEADER: str(userid1)},
                             content_type='application/json')
        print(json.loads(resp.data))
        self.assertEqual(resp.status_code, 200)

        # onboard user 2 to set address in server
        kp = Keypair.random()
        address2 = kp.address().decode()
        resp = self.app.post('/user/onboard',
                             data=json.dumps({
                                 'public_address': address2}),
                             headers={USER_ID_HEADER: str(userid2)},
                             content_type='application/json')
        print(json.loads(resp.data))
        self.assertEqual(resp.status_code, 200)

        # user 1 updates his phone number to the server after client-side verification
        phone_num = '+972527702890'
        resp = self.app.post('/user/firebase/update-id-token',
                             data=json.dumps({
                                 'token': phone_num,
                                 'phone_number': phone_num}),
                             headers={USER_ID_HEADER: str(userid1)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # user 2 updates his phone number to the server after client-side verification
        phone_num = '+972528802120'
        resp = self.app.post('/user/firebase/update-id-token',
                             data=json.dumps({
                                 'token': phone_num,
                                 'phone_number': phone_num}),
                             headers={USER_ID_HEADER: str(userid2)},
                             content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        resp = self.app.get('/user/transactions',
                            headers={USER_ID_HEADER: str(userid1)})
        data = json.loads(resp.data)


        picture_one = "GCTWHWZASR3QPR4D2WAVFDIIVZF4VXKAT2NYB7ZNTTWHOA63KWX3B4DA"
        picture_two = "GASZGYERTT4ZJNRVVOOXDTNZ4ZZ4HOCJS73VCBSPWS7IOSF5X7AIIN6E"
        user_one_public_address = get_address_by_userid(userid1)

        # user 1 tips a picture
        import arrow
        resp = self.app.post('/user/transaction/report',
                             data=json.dumps(
                                 {
                                     "tx_hash": "f868b0c8e7d97fcaa1e651e6ea2d1c6d0a2fef738fab615a1906f4b0c883bc8f",
                                     "amount": 2,
                                     "to_address": picture_one,
                                     "id": "1",
                                     "type": "picture",
                                     "date": arrow.utcnow().timestamp
                                 }),
                             headers={USER_ID_HEADER: str(userid1)},
                             content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['status'], 'ok')

        # sleep a sec to sort transactions by date
        sleep(1)

        # user 1 transfers kin to another app
        resp = self.app.post('/user/transaction/report',
                             data=json.dumps(
                                 {
                                     "tx_hash": "9dd18b4dc27aba6d4edd736a80969341321dd64afc9ce460449c946e4e5bd38e",
                                     "amount": 2,
                                     "to_address": picture_two,
                                     "id": "kit",
                                     "type": "app-to-app",
                                     "date": arrow.utcnow().timestamp
                                 }),
                             headers={USER_ID_HEADER: str(userid1)},
                             content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['status'], 'ok')

        sleep(1)

        # user 1 picture get a tip from someone
        resp = self.app.post('/user/transaction/report',
                             data=json.dumps(
                                 {
                                     "tx_hash": "5ddc8f1edb36ccfc5f1cad05c86d0f074a8cbeadc6c0d317262366cecab6d1d7",
                                     "amount": 3,
                                     "to_address": user_one_public_address,
                                     "id": "3",
                                     "type": "picture",
                                     "date": arrow.utcnow().timestamp
                                 }),
                             headers={USER_ID_HEADER: str(userid2)},
                             content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['status'], 'ok')

        sleep(1)

        resp = self.app.get('/user/transactions',
                            headers={USER_ID_HEADER: str(userid1)})
        data = json.loads(resp.data)
        detailed_txs = data['txs']


        # validate gift
        initial_reward = get_initial_reward()
        gift_tx = detailed_txs[3]

        self.assertEqual(gift_tx['amount'], initial_reward)
        self.assertEqual(gift_tx['type'], GIFT)

        tip_tx = detailed_txs[2]
        self.assertEqual(tip_tx['amount'], -2)
        self.assertEqual(tip_tx['type'], GIVE_TIP)


        app_to_app_tx = detailed_txs[1]
        self.assertEqual(app_to_app_tx['amount'], -2)
        self.assertEqual(app_to_app_tx['type'], APP_TO_APP)

        got_tip_tx = detailed_txs[0]
        self.assertEqual(got_tip_tx['amount'], 3)
        self.assertEqual(got_tip_tx['type'], GET_TIP)



if __name__ == '__main__':
    unittest.main()
