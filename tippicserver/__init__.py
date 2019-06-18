import sys

from flask import Flask
from flask_cors import CORS
import kin

import logging as log

from tippicserver.amqp_publisher import AmqpPublisher
from .encrypt import AESCipher


app = Flask(__name__)
CORS(app)

# set log level
log.getLogger().setLevel(log.INFO)

from flask_sqlalchemy import SQLAlchemy
from tippicserver import config, ssm, stellar

from .utils import increment_metric
increment_metric('server-starting')

# get seeds, channels from aws ssm:
base_seed, channel_seeds = ssm.get_stellar_credentials()
if not base_seed:
    log.error('could not get base seed - aborting')
    sys.exit(-1)

if channel_seeds is None:
    log.error('could not get channels seeds - aborting')
    sys.exit(-1)

# init sdk:
print('using kin sdk version: %s' % kin.version.__version__)
print("kin horizon: %s" % config.STELLAR_HORIZON_URL)

myenv = kin.Environment('CUSTOM', config.STELLAR_HORIZON_URL, config.STELLAR_NETWORK)
app.kin_sdk = kin.KinClient(myenv)
app.kin_account = app.kin_sdk.kin_account(base_seed, channel_seeds, "TIPC")
log.info('Kin account status: %s' % app.kin_account.get_status())

# init encryption util
key, iv = ssm.get_encrpytion_creds()
app.encryption = AESCipher(key, iv)

# SQLAlchemy stuff:
# create an sqlalchemy engine with "autocommit" to tell sqlalchemy NOT to use un-needed transactions.
# see this: http://oddbird.net/2014/06/14/sqlalchemy-postgres-autocommit/
# and this: https://github.com/mitsuhiko/flask-sqlalchemy/pull/67
class MySQLAlchemy(SQLAlchemy):
    def apply_driver_hacks(self, app, info, options):
        options['isolation_level'] = 'AUTOCOMMIT'
        super(MySQLAlchemy, self).apply_driver_hacks(app, info, options)

app.config['SQLALCHEMY_DATABASE_URI'] = config.DB_CONNSTR

# SQLAlchemy timeouts
app.config['SQLALCHEMY_POOL_SIZE'] = 1000
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 5
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 100
app.config['SQLALCHEMY_POOL_RECYCLE'] = 60*5

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if config.DEBUG:
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

if config.DEPLOYMENT_ENV in ['prod', 'stage']:
    print('starting sqlalchemy in autocommit mode')
    db = MySQLAlchemy(app)
else:
    db = SQLAlchemy(app)

#SQLAlchemy logging
#import logging
#logging.basicConfig()
#logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)
#logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
#logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)

import tippicserver.views_private
import tippicserver.views_public
import redis
from rq import Queue

#redis:
app.redis = redis.StrictRedis(host=config.REDIS_ENDPOINT, port=config.REDIS_PORT, db=0)
# redis config sanity
app.redis.setex('temp-key', 1, 'temp-value')

# start the rq queue connection
app.rq_fast = Queue('tippicserver-%s-fast' % config.DEPLOYMENT_ENV, connection=redis.Redis(host=config.REDIS_ENDPOINT, port=config.REDIS_PORT, db=0), default_timeout=200)
app.rq_slow = Queue('tippicserver-%s-slow' % config.DEPLOYMENT_ENV, connection=redis.Redis(host=config.REDIS_ENDPOINT, port=config.REDIS_PORT, db=0), default_timeout=7200)

# useful prints:
state = 'enabled' if config.PHONE_VERIFICATION_ENABLED else 'disabled'
log.info('phone verification: %s' % state)
state = 'enabled' if config.AUTH_TOKEN_ENABLED else 'disabled'
log.info('auth token enabled: %s' % state)
state = 'enabled' if config.AUTH_TOKEN_ENFORCED else 'disabled'
log.info('auth token enforced: %s' % state)
state = 'enabled' if config.P2P_TRANSFERS_ENABLED else 'disabled'
log.info('p2p transfers: %s' % state)

# get the firebase service-account from ssm
service_account_file_path = ssm.write_service_account()

# init the firebase admin stuff
import firebase_admin
from firebase_admin import credentials
cred = credentials.Certificate(service_account_file_path)
firebase_admin.initialize_app(cred)
app.firebase_admin = firebase_admin

# figure out blocked prefixes - if this fail, crash the server
from ast import literal_eval
app.blocked_phone_prefixes = literal_eval(config.BLOCKED_PHONE_PREFIXES)
app.allowed_phone_prefixes = literal_eval(config.ALLOWED_PHONE_PREFIXES)
app.blocked_country_codes = literal_eval(config.BLOCKED_COUNTRY_CODES)

# initialize geoip instance
from geolite2 import geolite2
app.geoip_reader = geolite2.reader()

# print db creation statements
if config.DEBUG:
    from .utils import print_creation_statement
    print_creation_statement()
    pass


