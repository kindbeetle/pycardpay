import hashlib

from . import api
from .utils import order_to_xml
from .settings import test_settings, live_settings


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
        if not isinstance(client_password, bytes):
            client_password = client_password.encode('ascii')
        self.client_password = hashlib.sha256(client_password).hexdigest()
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
        :param currency: (optional) Is used when store works with multiple currencies. Country code from ISO 3166.
        :type currency: str|unicode
        :param order_number: (optional) Transaction number. If one transaction data is needed.
        :type order_number: int
        :raises: :class:`PyCardPay.exceptions.XMLParsingError`
        :returns: dict

        Return dict structure:

        >>> {
            'is_executed': True,                        # Success or Fail
            'details': '',                              # Contains detailed description when request failed.
            'orders': [                                 # Orders list
                {
                    'id': '12345',                      # Transaction ID
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
                          client_password=self.client_password,
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
                        client_password=self.client_password,
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
                          client_password=self.client_password, 
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
                           client_password=self.client_password,
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
            'amount': 120,                  # (Decimal) The total order amount in your account’s selected currency.
            'email': 'customer@exmaple.com', # (str|unicode) Customers e-mail address.
            'is_two_phase': False,          # (bool) Optional. If set to True, the amount will not be captured but only
                blocked.
            'currency': 'USD',              # (str|unicode) Optional. ISO 4217 currency code.
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

        Returning dict always contains key ``is_3ds_required``. If it set to ``False`` the dict will be:

        >>> payment_result = PyCardPay.pay(xml, 'YourSecretPassword')
        >>> print payment_result
        {
            'is_3ds_required': False,   # 3Ds authorization **not** required
            'id': '12345',              # Transaction ID
            'number': '54321',          # Your order number
            'status': 'APPROVED',       # Transaction status. May contains values: 'APPROVED', 'DECLINED', 'HOLD'
            'description': 'Test',      # Status description
        }

        If ``is_3ds_required`` is set to ``True``:

        >>> print payment_result
        {
            'is_3ds_required': True,    # 3Ds authorization required
            'url':  '...',              # URL for which you need to send a POST request
            'MD': '...',                # MD - data for POST request
            'PaReq': '...',             # PaReq - data for POST request
        }

        Then you need to redirect the user to 3Ds authorization page. Sample form:

        >>> form_3ds = [
            '<form action="{}" method="POST">'.format(payment_result['url']),
            '<input type="hidden" name="PaReq" value="{}">'.format(payment_result['PaReq']),
            '<input type="hidden" name="MD" value="{}">'.format(payment_result['MD']),
            '<input type="hidden" name="TermUrl" value="{}">'.format(callback_page_url),
            '</form>'
        ]
        >> form_3ds = ''.join(form_3ds)

        Where ``callback_page_url`` is your URL to which customer will be returned after the authentication in bank. You
        will get back POST request with parameter ``PaRes`` - response code from bank. Now you can complete payment with
        :method:`PyCardPay.cardpay.CardPay.finish_3ds`
        """
        order = dict(order, wallet_id=self.wallet_id)
        xml = order_to_xml(order, items=items, billing=billing,
                           shipping=shipping, card=card, recurring=recurring)
        return api.pay(xml, self.secret, settings=self.settings)

    def finish_3ds(self, MD, PaRes):
        """Finish 3Ds authorization.

        This method returns the same result as :method:`PyCardPay.cardpay.CardPay.pay`.

        :param MD: MD value received after payment request from CardPay API.
        :type MD: str|unicode
        :param PaRes: Response code from bank after authorization.
        :type PaRes: str|unicode
        :raises: :class:`PyCardPay.exceptions.XMLParsingError` if response contains unknown xml structure.
        :returns: dict -- see :func:`PyCardPay.api.pay` for description.
        """
        return api.finish_3ds(MD, PaRes, settings=self.settings)
