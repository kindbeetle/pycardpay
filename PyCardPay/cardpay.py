import base64
import hashlib
from decimal import Decimal

from . import api
from .utils import order_to_xml, parse_response
from .settings import test_settings, live_settings
from .exceptions import SignatureError


class CardPay:
    """High level interface to CardPay service.

    :param wallet_id: Store id in CardPay system.
    :type wallet_id: int
    :param secret: Your CardPay secret password.
    :type secret: str|unicode
    :param client_login: Store login for administrative interface
    :type client_login: str|unicode
    :param client_password: Store password for administrative interface
    :type client_password: str|unicode
    :param test: Switch to testing mode (uses sandbox server)
    :type test: bool
    """

    def __init__(self, wallet_id, secret, client_login, client_password,
                 test=False):
        self.wallet_id = wallet_id
        if not isinstance(secret, bytes):
            secret = secret.encode('ascii')
        self.secret = secret
        self.client_login = client_login
        self.client_password = client_password
        if not isinstance(client_password, bytes):
            client_password = client_password.encode('ascii')
        self.client_password_sha256 = hashlib.sha256(client_password).hexdigest()
        self.test = test
        self.settings = test_settings if test else live_settings

    def status(self, **kwargs):
        """Get transactions report

        :param date_begin: (optional) Date from which you want to receive last 10 transactions.
        :param date_begin: (optional) Date from which you want to receive last 10 transactions. Valid format: 'yyyy-MM-dd'
            or 'yyyy-MM-dd HH:mm'.
        :type date_begin: srt|unicode
        :param date_end: (optional) Date before which you want to receive last 10 transactions. Valid format: 'yyyy-MM-dd'
            or 'yyyy-MM-dd HH:mm'.
        :type date_end: str|unicode
        :param number: (optional) Order number. If one transaction data is needed.
        :type number: str|unicode
        :raises: :class:`PyCardPay.exceptions.XMLParsingError`
        :returns: dict

        Return dict structure:

        >>> {
            'is_executed': True,                        # Success or Fail
            'details': '',                              # Contains detailed description when request failed.
            'orders': [                                 # Orders list
                {
                    'id': '12345',                      # Transaction ID
                    'orderu_number': '12345',           # Order ID
                    'status_name': 'clearing_success',  # Transaction status
                    'date_in':  '2014-04-28 21:55',     # Payment date
                    'amount': '210',                    # Payment amount
                    'hold_number: '5043696eec91f3b6b472b2e19d8fdf6061628fec',
                    'email': 'test@cardpay.com',        # Customer email
                },
                ...
            ]
        }
        """
        return api.status(client_login=self.client_login,
                          client_password=self.client_password_sha256,
                          wallet_id=self.wallet_id,
                          settings=self.settings,
                          **kwargs)

    def void(self, id):
        """Change transaction status to "VOID"

        :param id: Transaction id
        :type id: int
        :raises: :class:`PyCardPay.exceptions.HTTPError`, :class:`PyCardPay.exceptions.XMLParsingError`
        :returns: dict

        Return dict structure:

        >>> {'is_executed': True, 'details': ''}
        >>> {'is_executed': False, 'details': 'Reason'}
        """
        return api.void(id=id, client_login=self.client_login,
                        client_password=self.client_password_sha256,
                        settings=self.settings)

    def refund(self, id, reason, amount=None):
        """Change transaction status to "REFUND"

        :param id: Transaction id
        :type id: int
        :param reason: Refund reason
        :type reason: str|unicode
        :param amount: (optional) Refund amount in transaction currency. If not set then full refund will be made
        :type amount: Decimal|int
        :raises: :class:`PyCardPay.exceptions.HTTPError`, :class:`PyCardPay.exceptions.XMLParsingError`
        :returns: dict

        Return dict structure:
        >>> {'is_executed': True, 'details': ''}
        >>> {'is_executed': False, 'details': 'Reason'}
        """
        kwargs = {} if amount is None else {'amount': amount}
        return api.refund(id=id, reason=reason, client_login=self.client_login,
                          client_password=self.client_password_sha256, 
                          settings=self.settings, **kwargs)

    def capture(self, id):
        """Change transaction status to "CAPTURE"

        :param id: Transaction id
        :type id: int
        :raises: :class:`PyCardPay.exceptions.HTTPError`, :class:`PyCardPay.exceptions.XMLParsingError`
        :returns: dict

        Return dict structure:

        >>> {'is_executed': True, 'details': ''}
        >>> {'is_executed': False, 'details': 'Reason'}
        """
        return api.capture(id=id, client_login=self.client_login,
                           client_password=self.client_password_sha256,
                           settings=self.settings)

    def pay(self, order, items=None, billing=None, shipping=None, card=None,
            recurring=None):
        """Process payment

        :param order: Orders information.
        :type order: dict
        :param items: (optional) Product / service, provided to the customer.
        :type items: list
        :param shipping: (optional) Shipping address
        :type shipping: dict
        :param billing: (optional) Billing address
        :type billing: dict
        :param card: (optional) Credit card information
        :type card: dict
        :param recurring: Recurring payment
        :type recurring: dict
        :raises: KeyError if wasn't specified required items in order parameter.
        :raises: :class:`PyCardPay.exceptions.XMLParsingError` if response contains unknown xml structure.
        :returns: dict -- see below for description

        .. note::
            Minimal required parameters for *order* are: wallet_id, number, amount and email.

        .. note::
            If 'currency' parameter is not specified, ask your Account Manager which currency is used by default.

        .. warning::
            *card* and *billing* parameters **should be used and required** only in "Gateway Mode".
            If required, you can omit both the *billing* and the *shipping* address. To enable this feature, please contact
            your Account Manager.

        Parameters structure:

        >>> order =  {
            'number': 10,                   # (int) Unique order ID used by the merchant’s shopping cart.
            'description': 'Red T-Shirt',   # (str) Optional. Description of product/service being sold.
            'currency': 'USD',              # (str|unicode) Optional. ISO 4217 currency code.
            'amount': 120,                  # (Decimal) The total order amount in your account’s selected currency.
            'customer_id': '123',           # (str|unicode) Optional. Customer’s ID in the merchant’s system
            'email': 'customer@exmaple.com', # (str|unicode) Customers e-mail address.
            'is_two_phase': False,          # (bool) Optional. If set to True, the amount will not be captured but only
            'note': 'Last item',            # (str|unicode) Optional. Note about the order that will not be displayed to customer blocked.
            'return_url': 'http://example.com/', # (str|unicode) Optional. Overrides default success URL and decline URL. return_url can be used separately or together with other url parameters
            'success_url': 'http://example.com/', # (str|unicode) Optional. Overrides default success URL only
            'decline_url': 'http://example.com/', # (str|unicode) Optional. Overrides default decline_URL only
            'cancel_url': 'http://example.com/', # (str|unicode) Optional. Overrides default cancel URL only
            'is_gateway': False,            # (bool) Optional. If set to True, the "Gateway Mode" will be used.
            'locale': 'ru',                 # (str|unicode) Optional. Preferred locale for the payment page.
            'ip': '10.20.30.40',            # (str|unicode) Optional. Customers IPv4 address. Used only in "Gateway Mode".
        }
        >>> items = [
        {
            'name': 'Computer desk',        # (str|unicode) The name of product / service, provided to the customer.
            'description': 'Sport Video',   # (str|unicode) Optional. Description of product / service, provided to the
                customer.
            'count': 1,                     # (int) Optional. Product / service quantity.
            'price': 100,                   # (Decimal) Optional. Price of product / service.
        },
        ...
        ]
        >>> billing = {
            'country': 'USA',               # (str|unicode) ISO 3166-1 code of delivery country.
            'state': 'NY',                  # (str|unicode) Delivery state or province.
            'city': 'New York',             # (str|unicode) Delivery city.
            'zip': '04210',                 # (str|unicode) Delivery postal code.
            'street': '450 W. 33 Street',   # (str|unicode) Delivery street address.
            'phone': '+1 (212) 210-2100',   # (str|unicode) Customer phone number.
        }
        >>> shipping = {
            'country': 'USA',               # (str|unicode) Optional. ISO 3166-1 code of delivery country.
            'state': 'NY',                  # (str|unicode) Optional. Delivery state or province.
            'city': 'New York',             # (str|unicode) Optional. Delivery city.
            'zip': '04210',                 # (str|unicode) Optional. Delivery postal code.
            'street': '450 W. 33 Street',   # (str|unicode) Optional. Delivery street address.
            'phone': '+1 (212) 210-2100',   # (str|unicode) Optional. Customer phone number.
        }
        >>> card = {
            'num': '1111222233334444',      # (str|unicode) Customers card number (PAN)
            'holder': 'John Doe',           # (str|unicode) Cardholder name.
            'cvv': '321',                   # (str|unicode) Customers CVV2/CVC2 code. 3-4 positive digits.
            'expires': '04/15',             # (str|unicode) Card expiration date
        }
        >>> recurring = {
            'period': 30,                   # (int) Period in days of extension of service.
            'price': 120,                   # (Decimal) Optional. Cost of extension of service.
            'begin': '12.02.2015',          # (str|unicode) Optional. Date from which recurring payments begin.
            'count': 10,                    # (int) Optional. Number of recurring payments.
        }

        Return dict structure:

        >>> {
            'url':  '...',              # URL you need to redirect customer to
        }
        """
        order = dict(order, wallet_id=self.wallet_id)
        xml = order_to_xml(order, items=items, billing=billing,
                           shipping=shipping, card=card, recurring=recurring)
        return api.pay(xml, self.secret, settings=self.settings)

    def payouts(self, data, card):
        """Create Payout order.

        :param data: Order data
        :type dict
        :param card: Credit card information
        :type dict
        :returns: dict

        Parameters structure:

        >>> data = {
            "merchantOrderId": "PO01242324",    # (str|unicode) Represents the ID of the order in merchant’s system 
            "amount": 128,                      # (Decimal) Represents the amount to be transferred to the customer’s card
            "currency": "USD",                  # (str|unicode) Represents the amount to be transferred to the customer’s card
            "description": "X-mass gift",       # (str|unicode) Optional. Transaction description
            "note": "Payout Ref.12345",         # (str|unicode) Optional. Note about the order, not shown to the customer
            "recipientInfo": "John Smith"       # (str|unicode) Optional. Payout recipient (cardholder) information
        }

        >>> card = {
            "number": "4000000000000002",       # (str|unicode) Customer’s card number (PAN). Any valid card number, may contain spaces
            "expiryMonth": 7,                   # (int) Optional. Customer’s card expiration month. Format: mm
            "expiryYear": 2019                  # (int) Optional. Customer’s card expiration month. Format: yyyy
        }


        Response structure on success:

        >>> {
            "data": {
                "type": "PAYOUTS",
                "id": "4ed8991cc11e485c931dcf59387c06b6",
                "created": "2015-08-28T09:09:53Z",
                "updated": "2015-08-28T09:09:53Z",
                "rrn": "000018872019",
                "merchantOrderId": "PO01242324",
                "status": "SUCCESS"
            },
            "links": {
                "self": "https://sandbox.cardpay.com/MI/api/v2/payments/4ed8991cc11e485c931dcf59387c06b6"
            },
            "meta": {
                "request": {
                    "type": "PAYOUTS",
                    "timestamp": "2015-08-28T09:09:49Z",
                    "merchantOrderId": "PO01242324",
                    "amount": 128.97,
                    "currency": "USD",
                    "card": {
                        "number": "4000...0002",
                        "expiryMonth": 7,
                        "expiryYear": 2019
                    },
                    "description": "X-mass gift for you, my friend",
                    "note": "Payout Ref.12345",
                    "recipientInfo": "John Smith"
                },
                "foo": "bar"
            }
        }

        Response structure on error:

        >>> {
            "errors": [
                {
                    "status": "400",
                    "source": {
                        "pointer": "/data/card/number"
                    },
                    "title": "Invalid Attribute",
                    "detail": "invalid credit card number"
                }
            ]
        }
        """
        return api.payouts(self.wallet_id, self.client_login,
                           self.client_password, data=data, card=card,
                           settings=self.settings)

    def parse_callback(self, base64_string, sha512):
        """Checks if returned base64 encoded string is encoded with our secret password and parses it.

        :param base64_string: String encoded with base64.
        :type base64_string: str
        :param sha512: SHA512 checksum which must be verified.
        :type sha512: str
        :raises: TypeError if specified invalid base64 encoded string.
        :raises: :class:`PyCardPay.exceptions.SignatureError` if signature is incorrect.
        :raises: :class:`PyCardPay.exceptions.XMLParsingError` if lxml failed to parse string
        :returns: dict

        Return dict structure:
        >>> {
            'id': 299150,               # ID assigned to the order in CardPay. None is returned when order was cancelled by customer or order was incorrect.
            'refund_id': 299151,        # ID assigned to the refund in CardPay. Only for refund.
            'number': '458210',         # Merchant’s ID of the order if it was received from Merchant.
            'status': 'APPROVED',       # See possible values below.
            'description': 'CONFIRMED', # CardPay’s message about order’s validation.
            'date': '15-01-2013 10:30:45', # Format DD-MM-YYYY hh:mm:ss. For order: date and time when the order was received. For refund: date and time when the refund was received.
            'customer_id': '11021',     # Customer’s ID in the merchant’s system. Present if was sent with Order.
            'card_bin': '400000…0000',  # (Or 'card_num') Part of card number. Not present by default, ask your CardPay manager to enable it if needed.
            'card_holder': 'John Silver', # Name of cardholder. Not present by default, ask your CardPay manager to enable it if needed, Callback URL must be HTTPS.
            'decline_code': '05',       # Optional code of the decline. Included only when transaction is declined and sending of decline codes is enabled by wallet settings.
            'approval_code': 'DK3H25',  # Authorization code, provided by bank. Only in case of successful transaction.
            'is_3d': True,              # Was 3-D Secure authentication made or not.
            'currency': 'USD',          # Transaction currency as received with order
            'amount': '21.12',          # Current transaction’s amount as received with order, but can be reduced by refunds later. In case of refund notification this amount is before the refund was made.
            'recurring_id': '19F0B681E6F74F83AA6AB0162D7BF3A5', # ID of recurring that can be used to continue recurring in future. In case of successful recurring begin.
            'refunded': '7.04',         # Refund amount in order’s currency. In case of refund notification.
            'note': 'VIP customer',     # Present if was sent with Order.
        }

        Status field may have one of these values:

        APPROVED    Transaction successfully completed, amount was captured
        DECLINED    Transaction denied
        PENDING     Transaction successfully authorized, but needs some time to be verified, amount was held and can be captured later
        VOIDED      Transaction was voided (in case of void notification)
        REFUNDED    Transaction was voided (in case of refund notification)
        CHARGEBACK  Transaction was voided (in case of chargeback notification)
        """
        dec_string = base64.standard_b64decode(base64_string)
        if hashlib.sha512(dec_string + self.secret).hexdigest() != sha512:
            raise SignatureError('Incorrect signature')
        xml = parse_response(dec_string)
        result = {}
        for attr in ['id', 'refund_id', 'number', 'status', 'description',
                     'date', 'customer_id', 'card_bin', 'card_num',
                     'card_holder', 'decline_code', 'approval_code', 'is_3d',
                     'currency', 'amount', 'recurring_id', 'refunded', 'note']:
            value = xml.get(attr)
            if value is not None:
                if attr in ['id', 'refund_id']:
                    if value == '-':
                        value = None
                    else:
                        value = int(value)
                elif attr == 'is_3d':
                    value = (value == 'true')
                elif attr in ['amount', 'refunded']:
                    value = Decimal(value)
                result[attr] = value
        return result
