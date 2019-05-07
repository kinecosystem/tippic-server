"""The model for the Kin App Server."""
import logging as log

from sqlalchemy import desc
from sqlalchemy_utils import UUIDType

from tippicserver import db, stellar, config


class Transaction(db.Model):
    """
    Tippic transactions: from and to the server
    """
    tx_hash = db.Column(db.String(100), nullable=False, primary_key=True)
    user_id = db.Column('user_id', UUIDType(binary=False), db.ForeignKey("user.user_id"), primary_key=False,
                        nullable=False)
    to_address = db.Column(db.String(60), primary_key=False, unique=False, nullable=False)
    amount = db.Column(db.Integer(), nullable=False, primary_key=False)
    tx_for_item_id = db.Column(db.String(100), nullable=False, primary_key=False)
    tx_type = db.Column(db.String(20), primary_key=False, unique=False, nullable=False)
    update_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return '<tx_hash: %s, type: %s, user_id: %s, amount: %s, to_address: %s, tx_for_item_id: %s,  update_at: %s>' % \
               (self.tx_hash, self.tx_type, self.user_id, self.amount, self.to_address, self.tx_for_item_id,
                self.update_at)


def get_tx_totals():
    totals = {'to_public': 0, 'from_public': 0}
    prep_stat = 'select sum(amount) from transaction where incoming_tx=false;'
    totals['to_public'] = db.engine.execute(prep_stat).scalar()
    prep_stat = 'select sum(amount) from transaction where incoming_tx=true;'
    totals['from_public'] = db.engine.execute(prep_stat).scalar()

    return totals


def report_transaction(tx_json):
    """ store a given transaction in the database """

    # check if tx_hash already in db
    tx = Transaction.query.filter(Transaction.tx_hash == tx_json['tx_hash']).first()
    if tx:
        return False

    # if not test - make sure transaction is valid
    try:
        valid, data = stellar.extract_tx_payment_data(tx_json['tx_hash'])
        if not config.DEBUG and not valid:
            return False
    except Exception as e:
        print("Exception occurred for tx_hash = %s:\n%s" % (tx_json['tx_hash'], e))
        return False
    # store transaction
    return create_tx(tx_json['tx_hash'], tx_json['user_id'], tx_json['to_address'], tx_json['amount'],
                     tx_json['type'], tx_json['id'])


def list_user_transactions(user_id, max_txs=None):
    """returns all txs by this user - or the last x tx if max_txs was passed"""
    txs = Transaction.query.filter(Transaction.user_id == user_id).order_by(desc(Transaction.update_at)).all()
    # trim the amount of txs
    txs = txs[:max_txs] if max_txs and max_txs > len(txs) else txs
    return txs

def list_user_incoming_tips(user_id, to_address, max_txs=None):
    from tippicserver.utils import PICTURE

    txs = Transaction.query.filter(Transaction.user_id != user_id).filter(Transaction.to_address == to_address).filter(Transaction.tx_type == PICTURE).order_by(desc(Transaction.update_at)).all()
    # trim the amount of txs
    txs = txs[:max_txs] if max_txs and max_txs > len(txs) else txs
    return txs

def create_tx(tx_hash, user_id, to_address, amount, tx_type, tx_for_item_id):
    try:
        tx = Transaction()
        tx.tx_hash = tx_hash
        tx.user_id = user_id
        tx.amount = int(amount)
        tx.to_address = to_address
        tx.tx_type = tx_type
        tx.tx_for_item_id = tx_for_item_id
        db.session.add(tx)
        db.session.commit()
    except Exception as e:
        print(e)
        log.error('cant add tx to db with id %s' % tx_hash)
    else:
        log.info('created tx with tx_hash: %s' % tx.tx_hash)
        return True

    return False


def get_user_tx_report(user_id):
    """return a json with all the interesting user-tx stuff"""
    print('getting user tx report for %s' % user_id)
    user_tx_report = {}
    try:
        txs = list_user_transactions(user_id)
        for tx in txs:
            user_tx_report[tx.tx_hash] = {'amount': tx.amount, 'date': tx.update_at, 'to_address': tx.to_address}

    except Exception as e:
        log.error('caught exception in get_user_tx_report:%s' % e)
    return user_tx_report
