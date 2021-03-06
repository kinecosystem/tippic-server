# tester config file. should be overwritten by ansible in prod/stage.

DEPLOYMENT_ENV = 'test'
DEBUG = True
DB_CONNSTR = "postgresql://localhost/tippic_localhost"
REDIS_ENDPOINT = 'localhost'
REDIS_PORT = 6379

STELLAR_TIMEOUT_SEC = 10  # waitloop for tx data to be available
STELLAR_INITIAL_ACCOUNT_BALANCE = 0
PUSH_TTL_SECS = 60 * 60 * 24

STELLAR_HORIZON_URL = 'https://horizon-testnet.kin.org'
STELLAR_NETWORK ='Kin Testnet ; December 2018'
STELLAR_KIN_ISSUER_ADDRESS = 'GBC3SG6NGTSZ2OMH3FFGB7UVRQWILW367U4GSOOF4TFSZONV42UJXUH7'

KMS_KEY_AWS_REGION = 'us-east-1'

PHONE_VERIFICATION_REQUIRED = False
PHONE_VERIFICATION_ENABLED = True

P2P_TRANSFERS_ENABLED = True # leave this on for tests
P2P_MIN_KIN_AMOUNT = 300
P2P_MAX_KIN_AMOUNT = 12500

DISCOVERY_APPS_ANDROID_URL = 'https://discover.kin.org/android_stage.json'
DISCOVERY_APPS_OSX_URL = 'https://cdn.kinitapp.com/discovery_apps_osx_stage.json'

TOS_URL = 'http://www.kinitapp.com/terms-and-privacy-policy'
FAQ_URL = 'https://cdn.kinitapp.com/faq/v2/index.html'
FIREBASE_SERVICE_ACCOUNT_FILE = '/opt/tippic-server/service-account.json'


AUTH_TOKEN_SEND_INTERVAL_DAYS = 0
AUTH_TOKEN_ENFORCED = False
AUTH_TOKEN_ENABLED = False

BLOCK_ONBOARDING_IOS_VERSION = '0.1'
BLOCK_ONBOARDING_ANDROID_VERSION = '0.1'

BLOCKED_PHONE_PREFIXES = "[]"
ALLOWED_PHONE_PREFIXES = "[]"
BLOCKED_COUNTRY_CODES = "[]"

MAX_NUM_REGISTRATIONS_PER_NUMBER = 2  # keep this value at 2 for the test
APK_PACKAGE_NAME = 'org.kinecosystem.tippic'

PAYMENT_SERVICE_URL = 'http://localhost:4998'
API_SERVER_URL = 'http://localhost'
MIGRATION_SERVICE_URL = "http://localhost:8000" # tunnel
