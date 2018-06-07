import arrow

from kinappserver import db
from kinappserver.utils import InternalError


class BlackhawkOffer(db.Model):
    """the BlackhawkOffer class represent a single offer from the OmniCodes API.

    Offers can be bought into cards
    """
    offer_id = db.Column('offer_id', db.String(40), db.ForeignKey("offer.offer_id"), primary_key=True, nullable=False)
    merchant_code = db.Column(db.String(40), nullable=False)
    merchant_template_id = db.Column(db.String(40), nullable=False)
    batch_size = db.Column(db.Integer, default=1, nullable=False)
    denomination = db.Column(db.Integer, nullable=False)
    minimum_threshold = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return '<offer_id: %s, merchant_code: %s, merchant_template_id: %s, batch_size: %s, denomination: %s, minimum_threshold: %s, updated_at: %s>' % (self.offer_id, self.merchant_code, self.merchant_template_id, self.batch_size, self.denomination, self.processed, self.minimum_threshold, self.updated_at)


def create_bh_offer(offer_id, merchant_code, merchant_template_id, batch_size, denomination, minimum_threshold):
    """creates a new instance of BlackhawkCard"""
    try:

        offer = BlackhawkOffer()
        offer.offer_id = offer_id
        offer.merchant_code = merchant_code
        offer.merchant_template_id = merchant_template_id
        offer.batch_size = batch_size
        offer.denomination = denomination
        offer.minimum_threshold = minimum_threshold

        db.session.add(offer)
        db.session.commit()
    except Exception as e:
        print('failed to create a new blackhawk offer with id: %s' % offer)
        print(e)
        raise InternalError('failed to create a new blackhawk offer')
    else:
        return True


def get_bh_offers():
    return BlackhawkOffer.query.order_by(BlackhawkOffer.updated_at).all()


def list_bh_offers():
    """returns a dict of all the offers"""
    response = {}
    offers = BlackhawkOffer.query.order_by(BlackhawkOffer.updated_at).all()
    for offer in offers:
        response[offer.offer_id] = {'merchant_code': offer.merchant_code,
                                    'merchant_template_id': offer.merchant_template_id,
                                    'batch_size': offer.batch_size,
                                    'denomination': offer.denomination,
                                    'minimum_threshold': offer.minimum_threshold}
    return response