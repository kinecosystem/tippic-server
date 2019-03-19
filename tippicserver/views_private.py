"""
The Kin App Server private API is defined here.
"""
import logging as log
from uuid import UUID

from flask import request, jsonify, abort

from tippicserver import app, config, stellar, ssm
from tippicserver.models import nuke_user_data, get_user_report, get_user_tx_report, scan_for_deauthed_users, \
    user_exists, get_unauthed_users, get_all_user_id_by_phone, delete_all_user_data, blacklist_phone_number, \
    blacklist_phone_by_user_id, \
    get_tx_totals, set_should_solve_captcha, \
    set_update_available_below, set_force_update_below, add_picture, skip_picture_wait
from tippicserver.utils import InvalidUsage, InternalError, increment_metric, gauge_metric, sqlalchemy_pool_status
from tippicserver.views_common import limit_to_acl, limit_to_localhost, limit_to_password


@app.route('/health', methods=['GET'])
def get_health():
    """health endpoint"""
    return jsonify(status='ok')


@app.route('/user/data/delete', methods=['POST'])
def delete_user_data_endpoint():
    """endpoint used to delete all of a users data"""
    #disabling this function as its too risky
    abort(403)
    if not config.DEBUG:
        limit_to_localhost()

    payload = request.get_json(silent=True)
    user_id = payload.get('user_id', None)
    are_u_sure = payload.get('are_u_sure', False)
    delete_all_user_data(user_id, are_u_sure)
    return jsonify(status='ok')


@app.route('/stats/db', methods=['GET'])
def dbstats_api():
    """internal endpoint used to retrieve the number of db connections"""
    if not config.DEBUG:
        limit_to_localhost()

    return jsonify(status='ok', stats=sqlalchemy_pool_status()) # cant be async, used by the reboot script


@app.route('/balance', methods=['GET'])
def balance_api():
    """endpoint used to get the current balance of the seed and channels"""
    if not config.DEBUG:
        limit_to_localhost()

    base_seed, channel_seeds = ssm.get_stellar_credentials()
    balance = {'base_seed': {}, 'channel_seeds': {}}

    from stellar_base.keypair import Keypair
    balance['base_seed']['kin'] = stellar.get_kin_balance(Keypair.from_seed(base_seed).address().decode())
    balance['base_seed']['xlm'] = stellar.get_xlm_balance(Keypair.from_seed(base_seed).address().decode())
    index = 0
    for channel in channel_seeds:
        # seeds only need to carry XLMs
        balance['channel_seeds'][index] = {'xlm': 0}
        balance['channel_seeds'][index]['xlm'] = stellar.get_xlm_balance(Keypair.from_seed(channel).address().decode())
        index = index + 1

    return jsonify(status='ok', balance=balance)


@app.route('/user/nuke-data', methods=['POST'])
def nuke_user_api():
    """internal endpoint used to nuke a user's task and tx data. use with care"""
    if not config.DEBUG:
        limit_to_acl()
        limit_to_password()

    try:
        payload = request.get_json(silent=True)
        phone_number = payload.get('phone_number', None)
        nuke_all = payload.get('nuke_all', False) == True
        if None in (phone_number,):
            raise InvalidUsage('bad-request')
    except Exception as e:
        print(e)
        raise InvalidUsage('bad-request')

    user_ids = nuke_user_data(phone_number, nuke_all)
    if user_ids is None:
        print('could not find any user with this number: %s' % phone_number)
        return jsonify(status='error', reason='no_user')
    else:
        print('nuked users with phone number: %s and user_ids %s' % (phone_number, user_ids))
        return jsonify(status='ok', user_id=user_ids)


@app.route('/user/txs/report', methods=['POST'])
def user_tx_report_endpoint():
    """returns a summary of the user's txs data"""
    limit_to_acl()
    limit_to_password()

    try:
        payload = request.get_json(silent=True)
        user_id = payload.get('user_id', None)
        user_phone = payload.get('phone', None)
        if (user_id is None and user_phone is None) or (user_id is not None and user_phone is not None):
            print('user_tx_report_endpoint: userid %s, user_phone %s' % (user_id, user_phone))
            raise InvalidUsage('bad-request')
    except Exception as e:
        print(e)
        raise InvalidUsage('bad-request')

    try:  # sanitize user_id:
        if user_id:
            UUID(user_id)
    except Exception as e:
        log.error('cant generate tx report for user_id: %s ' % user_id)
        return jsonify(error='invalid_userid')

    if user_id:
        if not user_exists(user_id):
            print('user_tx_report_endpoint: user_id %s does not exist. aborting' % user_id)
            return jsonify(erorr='no_such_user')
        else:
            return jsonify(report=[get_user_tx_report(user_id)])

    else: # user_phone
        user_ids = get_all_user_id_by_phone(user_phone) # there may be a few users with this phone
        if not user_ids:
            print('user_tx_report_endpoint: user_phone %s does not exist. aborting' % user_phone)
            return jsonify(erorr='no_such_phone')
        else:
            return jsonify(report=[get_user_tx_report(user_id) for user_id in user_ids])


@app.route('/user/report', methods=['POST'])
def user_report_endpoint():
    """returns a summary of the user's data"""
    limit_to_acl()
    limit_to_password()

    try:
        payload = request.get_json(silent=True)
        user_id = payload.get('user_id', None)
        user_phone = payload.get('phone', None)
        if (user_id is None and user_phone is None) or (user_id is not None and user_phone is not None):
            print('user_report_endpoint: userid %s, user_phone %s' % (user_id, user_phone))
            raise InvalidUsage('bad-request')
    except Exception as e:
        print(e)
        raise InvalidUsage('bad-request')

    try:  # sanitize user_id:
        if user_id:
            UUID(user_id)
    except Exception as e:
        log.error('cant generate report for user_id: %s ' % user_id)
        return jsonify(error='invalid_userid')

    if user_id:
        if not user_exists(user_id):
            print('user_report_endpoint: user_id %s does not exist. aborting' % user_id)
            return jsonify(erorr='no_such_user')
        else:
            return jsonify(report=[get_user_report(user_id)])

    else: # user_phone
        user_ids = get_all_user_id_by_phone(user_phone) # there may be a few users with this phone
        if not user_ids:
            print('user_report_endpoint: user_phone %s does not exist. aborting' % user_phone)
            return jsonify(erorr='no_such_phone')
        else:
            return jsonify(report=[get_user_report(user_id) for user_id in user_ids])


@app.route('/users/deauth', methods=['GET'])
def deauth_users_endpoint():
    """disables users that were sent an auth token but did not ack it in time"""
    if not config.DEBUG:
        limit_to_localhost()

    app.rq_fast.enqueue(scan_for_deauthed_users)
    return jsonify(status='ok')


@app.route('/users/unauthed', methods=['GET'])
def users_unauthed_endpoint():
    """get the list of userids that are not authenticated"""
    if not config.DEBUG:
        limit_to_localhost()
    return jsonify(user_ids=get_unauthed_users())

@app.route('/user/phone-number/blacklist', methods=['POST'])
def user_phone_number_blacklist_endpoint():
    """blacklist a number"""
    if not config.DEBUG:
        limit_to_localhost()

    try:
        payload = request.get_json(silent=True)
        phone_number = payload.get('phone-number', None)
        if phone_number is None:
            print('user_phone_number_blacklist_endpoint: user_phone: %s' % phone_number)
            raise InvalidUsage('bad-request')
    except Exception as e:
        print(e)
        raise InvalidUsage('bad-request')

    if not blacklist_phone_number(phone_number):
        raise InternalError('cant blacklist number')
    return jsonify(status='ok')


@app.route('/user/blacklist', methods=['POST'])
def blacklist_user_endpoint():
    """"""
    if not config.DEBUG:
        limit_to_acl()
        limit_to_password()

    try:
        payload = request.get_json(silent=True)
        user_id = payload.get('user_id', None)
        if user_id is None:
            raise InvalidUsage('bad-request')
    except Exception as e:
        print(e)
        raise InvalidUsage('bad-request')
    else:
        if blacklist_phone_by_user_id(user_id):
            return jsonify(status='ok')
        else:
            return jsonify(status='error')


@app.route('/rq/jobs/count', methods=['GET'])
def get_rq_q_length_endpoint():
    # TODO remove me later
    if not config.DEBUG:
        limit_to_localhost()

    from rq import Queue
    for queue_name in ['tippicserver-%s-fast' % config.DEPLOYMENT_ENV,'tippicserver-%s-slow' % config.DEPLOYMENT_ENV]:
        q = Queue(queue_name, connection=app.redis)
        print('there are currently %s jobs in the %s queue' % (q.count, queue_name))
        gauge_metric('rq_queue_len', q.count, 'queue_name:%s' % queue_name)
    return jsonify(status='ok')


@app.route('/users/reregister', methods=['GET'])
def reregister_users_endpoint():
    if not config.DEBUG:
        limit_to_localhost()

    app.rq_slow.enqueue(re_register_all_users)
    return jsonify(status='ok')


@app.route('/tx/total', methods=['GET'])
def total_kins_endpoint():
    if not config.DEBUG:
        limit_to_localhost()

    return jsonify(status='ok', total=get_tx_totals())


@app.route('/users/captcha/set', methods=['POST'])
def user_set_captcha_endpoint():
    if not config.DEBUG:
        limit_to_acl()
        limit_to_password()
    try:
        payload = request.get_json(silent=True)
        user_ids = payload.get('user_ids')
        should_show = payload.get('set_captcha', 0)
    except Exception as e:
        log.error('failed to process user-set-captcha')
    else:
        for user_id in user_ids:
            print('user_set_captcha_endpoint: setting user_id %s to %s' % (user_id, should_show))
            set_should_solve_captcha(user_id, should_show)

    return jsonify(status='ok')


@app.route('/system/versions/update-available-below', methods=['POST'])
def system_versions_update_available_below_endpoint():
    if not config.DEBUG:
        limit_to_acl()
        limit_to_password()

    payload = request.get_json(silent=True)
    os_type = payload.get('os_type', None)
    app_version = payload.get('version', None)
    set_update_available_below(os_type, app_version)
    return jsonify(status='ok')


@app.route('/system/versions/force-update-below', methods=['POST'])
def system_versions_force_update_below_endpoint():
    if not config.DEBUG:
        limit_to_acl()
        limit_to_password()

    payload = request.get_json(silent=True)
    os_type = payload.get('os_type', None)
    app_version = payload.get('version', None)
    set_force_update_below(os_type, app_version)
    return jsonify(status='ok')


@app.route('/skip_picture', methods=['POST'])
def skip_picture_endpoint():
    """advances current_picture_index"""
    if not config.DEBUG:
        limit_to_localhost()
    
    try:
        payload = request.get_json(silent=True)
        skip_by = payload.get('skip_by', 1)
    except Exception as e:
        print(e)
        raise InvalidUsage('bad-request')
    else:
        skip_picture_wait(skip_by)

    increment_metric('skip-picture-wait')
    return jsonify(status='ok')


@app.route('/picture/add', methods=['POST'])
def add_pictures_endpoint():
    """used to add pictures to the db"""
    if not config.DEBUG:
        limit_to_acl()
        limit_to_password()
    try:
        pictures = payload.get('pictures', None)
        payload = request.get_json(silent=True)

    except Exception as e:
        print('exception: %s' % e)
        raise InvalidUsage('bad-request')
    
    for picture in pictures:
        status = add_picture(picture)
        if status is not True:
            raise InvalidUsage(message='error', payload={
                               'error field': str(status), 'picture': picture})

    return jsonify(status='ok')


@app.route('/discovery/add_app', methods=['POST'])
def add_discovery_app_endpoint():
    """ add app to db """
    from tippicserver.models.discovery_app import add_app
    if not config.DEBUG:
        limit_to_localhost()

    payload = request.get_json(silent=True)
    try:
        app = payload.get('app', None)
    except Exception as e:
        print('exception: %s' % e)
        raise InvalidUsage('bad-request')
    if add_app(app):
        return jsonify(status='ok')
    else:
        raise InvalidUsage('failed to add picture')
