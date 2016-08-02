# coding=utf-8

import base64
import datetime as dt
import hashlib
from decimal import Decimal

from lxml import etree
from lxml.builder import E
import requests

from .exceptions import HTTPError, XMLParsingError


def order_to_xml(order, items=None, billing=None, shipping=None, card=None,
                 generate_card_token=False, card_token=None, recurring=None):
    """Creates order xml

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
    :param generate_card_token: (optional) Whether card token should be generated
    :type generate_card_token: bool
    :param card_token: (optional) Card token used instead of card data
    :type card_token: str
    :param recurring: Recurring payment
    :type recurring: dict
    :raises: KeyError if wasn't specified required items in order parameter.
    :returns: :class:`lxml.etree.Element`

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
        'wallet_id': 123,               # (int) Unique merchant's ID used by the CardPay payment system.
        'number': 10,                   # (int) Unique order ID used by the merchant’s shopping cart.
        'description': 'Red T-Shirt',   # (str) Optional. Description of product/service being sold.
        'currency': 'USD',              # (str|unicode) Optional. ISO 4217 currency code.
        'amount': 120,                  # (Decimal) The total order amount in your account’s selected currency.
        'customer_id': '123',           # (str|unicode) Optional. Customer’s ID in the merchant’s system
        'email': 'customer@exmaple.com', # (str|unicode) Customers e-mail address.
        'is_two_phase': False,          # (bool) Optional. If set to True, the amount will not be captured but only blocked.
        'is_gateway': False,            # (bool) Optional. If set to True, the "Gateway Mode" will be used.
        'note': 'Last item',            # (str|unicode) Optional. Note about the order that will not be displayed to customer
        'return_url': 'http://example.com/', # (str|unicode) Optional. Overrides default success URL and decline URL. return_url can be used separately or together with other url parameters
        'success_url': 'http://example.com/', # (str|unicode) Optional. Overrides default success URL only
        'decline_url': 'http://example.com/', # (str|unicode) Optional. Overrides default decline_URL only
        'cancel_url': 'http://example.com/', # (str|unicode) Optional. Overrides default cancel URL only
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

    Minimal usage example:

    >>> xml = PyCardPay.order_to_xml(order={'wallet_id': 20, 'number': 10, 'email': 'customer@exmaple.com',
                                            'amount': 120})
    >>>
    >>> print type(xml)
    <type 'lxml.etree._Element'>
    >>>
    >>> print PyCardPay.xml_to_string(xml, encode_base64=False)
    <?xml version='1.0' encoding='utf-8'?>
    <order description="" locale="en" is_gateway="no" number="10" amount="120" wallet_id="20"
        email="customer@exmaple.com" is_two_phase="no"/>
    """
    if items is None:
        items = []

    # <order ...></order>
    e_order = E.order(
        wallet_id=str(order['wallet_id']),
        number=str(order['number']),
        description=order.get('description', ''),
        amount=str(order['amount']),
        email=order['email'],
        is_two_phase='yes' if order.get('is_two_phase') is True else 'no',
        is_gateway='yes' if order.get('is_gateway') is True else 'no',
        locale=order.get('locale', 'en'),
    )
    if order.get('currency'):
        e_order.set('currency', order['currency'])
    if e_order.get('is_gateway') == 'yes' and order.get('ip'):
        e_order.set('ip', order.get('ip'))
    if order.get('customer_id'):
        e_order.set('customer_id', order['customer_id'])
    if order.get('note'):
        e_order.set('note', order['note'])
    if order.get('return_url'):
        e_order.set('return_url', order['return_url'])
    if order.get('success_url'):
        e_order.set('success_url', order['success_url'])
    if order.get('decline_url'):
        e_order.set('decline_url', order['decline_url'])
    if order.get('cancel_url'):
        e_order.set('cancel_url', order['cancel_url'])

    if generate_card_token:
        e_order.set('generate_card_token', 'true')

    if card_token is not None:
        e_order.set('card_token', card_token)

    # <order><item ... /></order>
    for item in items:
        e_item = E.order_item(
            name=item['name'],
            description=item.get('description', ''),
            count=str(item.get('count', 1)),
            price=str(item.get('price', 0)),
        )
        e_order.append(e_item)

    # <order><address ... /></order>
    if billing:
        billing.update({'type': 'Billing'})
        e_order.append(E.address(**billing))
    if shipping:
        shipping.update({'type': 'Shipping'})
        e_order.append(**shipping)

    # <order><card ... /></order>
    if card:
        e_order.append(E.card(**card))

    # <order><recurring ... /></order>
    if recurring:
        e_recurring = E.recurring(
            period=str(recurring['period']),
            # if not price set use order.amount value
            price=str(recurring.get('price', e_order.get('amount'))),
            begin=recurring.get('begin',
                                dt.datetime.now().date().strftime('%d.%m.%Y')),
        )
        if recurring.get('count'):
            e_recurring.set('count', str(recurring.get('count')))
        e_order.append(e_recurring)

    return e_order


def xml_to_string(xml, encode_base64=True):
    """Returns xml as string optionally encoded with base64.

    :param xml: Order XML
    :type xml: :class:`lxml.etree.Element`
    :param encode_base64: Encode result string with base64?
    :type encode_base64: bool
    :raises: TypeError if passed not an :class:`lxml.etree.Element` as xml parameter.
    :returns: str
    """
    xml_string = etree.tostring(xml, xml_declaration=True, encoding='utf-8',
                                pretty_print=True)
    if encode_base64:
        return base64.standard_b64encode(xml_string)
    return xml_string


def xml_get_sha512(xml, secret):
    """Calculates sha512 checksum based on xml + secret

    :param xml: Order XML
    :type xml: :class:`lxml.etree.Element`
    :param secret: Your CardPay secret password.
    :type secret: str|unicode
    :raises: TypeError if passed not an :class:`lxml.etree.Element` as xml parameter.
    :returns: str -- Calculated SHA512
    """
    xml_string = xml_to_string(xml, encode_base64=False) + secret
    return hashlib.sha512(xml_string).hexdigest()


def xml_check_sha512(base64_string, sha512, secret):
    """Checks if returned base64 encoded string is encoded  with our secret password.

    :param base64_string: String encoded with base64.
    :type base64_string: str
    :param sha512: SHA512 checksum which must be verified.
    :type sha512: str
    :param secret: Your CardPay secret password.
    :raises: TypeError if specified invalid base64 encoded string.
    :returns: bool - True if verified otherwise False
    """
    dec_string = base64.standard_b64decode(base64_string)
    return hashlib.sha512(dec_string + secret).hexdigest() == sha512


def parse_response(xml):
    """Parse XML from string

    :param xml: XML string
    :type xml: str|unicode
    :raises: :class:`PyCardPay.exceptions.XMLParsingError` if lxml failed to parse string
    :returns: :class:`lxml.etree.Element`
    """
    try:
        return etree.fromstring(xml)
    except etree.Error as e:
        raise XMLParsingError(
            u'Failed to parse response from CardPay service: {}'.format(e),
            content=xml
        )


def make_http_request(url, method='get', **kwargs):
    """Make http get request to *url* passing *kwargs* as arguments

    :param url: Request url
    :type url: str|unicode
    :param method: HTTP method
    :type method: str|unicode
    :param \*\*kwargs: Request parameters
    :raises: :class:`PyCardPay.exceptions.HTTPError` if server returns status code different from 2xx
    :returns: HTML content
    """
    try:
        r = getattr(requests, method)(url, data=kwargs, verify=True)
    except AttributeError:
        r = requests.get(url, data=kwargs, verify=True)
    if not (200 <= r.status_code < 300):
        raise HTTPError(
            u'Expected HTTP response code "2xx" but '
            u'received "{}"'.format(r.status_code),
            method=method, url=url, data=kwargs, response=r
        )
    return r.content


def xml_http_request(url, method='get', **kwargs):
    """Make http get request to *url* passing *kwargs* as arguments

    :param url: Request url
    :type url: str|unicode
    :param method: HTTP method
    :type method: str|unicode
    :param \*\*kwargs: Request parameters
    :raises: :class:`PyCardPay.exceptions.HTTPError` if server returns status code different from 2xx
    :raises: :class:`PyCardPay.exceptions.XMLParsingError` if lxml failed to parse string
    :returns: :class:`lxml.etree.Element`
    """
    xml = make_http_request(url, method=method, **kwargs)
    try:
        return etree.fromstring(xml)
    except etree.Error as e:
        raise XMLParsingError(
            u'Failed to parse response from CardPay service: {}'.format(e),
            method=method, url=url, data=kwargs, content=xml
        )


def parse_order(xml):
    """Converts Order XML to dictionary

    :param xml: Order XML
    :type xml: :class:`lxml.etree.Element`
    :returns: dict
    """
    result = {}
    for attr in ['id', 'refund_id', 'number', 'status', 'description',
                 'date', 'customer_id', 'card_bin', 'card_num',
                 'card_holder', 'decline_code', 'decline_reason',
                 'approval_code', 'is_3d', 'currency', 'amount',
                 'recurring_id', 'refunded', 'note']:
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
