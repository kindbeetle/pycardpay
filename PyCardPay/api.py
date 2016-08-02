# coding=utf-8
from .exceptions import (
    XMLParsingError, JSONParsingError, HTTPError, TransactionNotFound,
)
from .utils import (
    xml_to_string, xml_get_sha512, make_http_request, xml_http_request,
    parse_order,
)
import json
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
from lxml import etree
from datetime import datetime
import requests
from .settings import live_settings


def status_change(settings=live_settings, **kwargs):
    """Change transaction status.

    :param id: Transaction id
    :type id: int
    :param status_to: New transaction status. Valid values: *capture*, *refund*, *void*.
    :param client_login: Unique store id. It is the same as for administrative interface
    :type client_login: str|unicode
    :param client_password: Store password. It is the same as for administrative interface
    :type client_password: str|unicode
    :param reason: (optional) Refund reason. **Required** if status_to is 'refund'
    :type reason: str|unicode
    :param amount: (optional) Refund amount in transaction currency. If not set then full refund will be made
    :type amount: Decimal|int
    :raises: :class:`PyCardPay.exceptions.HTTPError`, :class:`PyCardPay.exceptions.XMLParsingError`
    :returns: dict

    Return dict structure:

    >>> {'is_executed': True, 'details': ''}
    >>> {'is_executed': False, 'details': 'Status [capture] not allowed after [SUCCESS_CAPTURE]'}

    .. note::

        There is no need to pass *status_to* parameter if you are using methods :func:`capture`, :func:`refund` or
        :func:`void`.

    Valid transaction status changes:

    +---------------+--------------+
    | Status from   | Status to    |
    +===============+==============+
    | capture       | void         |
    +---------------+--------------+
    | capture       | refund       |
    +---------------+--------------+
    | authorized    | capture      |
    +---------------+--------------+
    | authorize     | void         |
    +---------------+--------------+
    """
    xml = xml_http_request(settings.url_status_change, 'post', **kwargs)
    if xml.get('is_executed') != 'yes':
        return {'is_executed': False, 'details': xml.get('details')}
    return {'is_executed': True, 'details': ''}


def status(settings=live_settings, **kwargs):
    """Get transactions report

    :param client_login: Unique store id. It is the same as for administrative interface.
    :type client_login: str|unicode
    :param client_password: Store password. It is the same as for administrative interface.
    :type client_password: str|unicode
    :param wallet_id: Store id in CardPay system.
    :type wallet_id: int
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
    xml = xml_http_request(settings.url_status, 'post', **kwargs)
    data = {'is_executed': True, 'details': '', 'orders': []}

    if xml.get('is_executed') != 'yes':
        data.update({'is_executed': False, 'details': xml.get('details')})
        return data

    for order in xml.xpath('.//orderu'):
        data['orders'].append({
            'id': order.get('id'),
            'orderu_number': order.get('orderu_number'),
            'status_name': order.get('status_name'),
            'date_in': order.get('date_in'),
            'amount': order.get('amount'),
            'hold_number': order.get('hold_number'),
            'email': order.get('email'),
        })
    return data


def void(settings=live_settings, **kwargs):
    """Change transaction status to "VOID"

    :param \*\*kwargs: Parameters that :func:`status_change` takes
    :returns: Result from :func:`status_change`
    """
    kwargs.update({'status_to': 'void'})
    return status_change(settings=settings, **kwargs)


def refund(settings=live_settings, **kwargs):
    """Change transaction status to "REFUND"

    :param \*\*kwargs: See :func:`status_change` for details
    :returns: Result from :func:`status_change`
    """
    kwargs.update({'status_to': 'refund'})
    return status_change(settings=settings, **kwargs)


def capture(settings=live_settings, **kwargs):
    """Change transaction status to "CAPTURE"

    :param \*\*kwargs: See :func:`status_change` for details
    :returns: Result from :func:`status_change`
    """
    kwargs.update({'status_to': 'capture'})
    return status_change(settings=settings, **kwargs)


def pay(xml, secret, settings=live_settings):
    """Process payment

    :param xml: Order XML created with :func:`PyCardPay.utils.order_to_xml`
    :type xml: :class:`lxml.etree.Element`
    :param secret: Your CardPay secret password.
    :type secret: str|unicode
    :raises: TypeError if passed not an :class:`lxml.etree.Element` as xml parameter.
    :raises: :class:`PyCardPay.exceptions.XMLParsingError` if response contains unknown xml structure.
    :returns: dict

    Return dict structure:

    >>> {
        'url':  '...',              # URL you need to redirect customer to
    }
    """
    order_xml = xml_to_string(xml, encode_base64=True)
    order_sha = xml_get_sha512(xml, secret)
    data = {'orderXML': order_xml, 'sha512': order_sha}
    r = make_http_request(settings.url_pay, method='post', **data)
    try:
        r_xml = etree.fromstring(r)
    except etree.Error as e:
        raise XMLParsingError(
            u'Failed to parse response from CardPay service: {}'.format(e),
            method='post', url=settings.url_pay, data=data, content=r
        )
    if r_xml.tag == 'redirect':
        return {
            'url': r_xml.get('url'),
        }
    elif r_xml.tag == 'order':
        return parse_order(r_xml)
    raise XMLParsingError(
        u'Unknown XML response. Root tag is neither'
        u'redirect nor order: {}'.format(r_xml.tag),
        method='post', url=settings.url_pay, data=data, content=r
    )


def payouts(wallet_id, client_login, client_password, data, card,
            settings=live_settings):
    """Create Payout order.

    :param wallet_id: Unique merchant’s ID used by the CardPay payment system
    :type wallet_id: int
    :param client_login: Unique store id. It is the same as for administrative interface
    :type client_login: str|unicode
    :param client_password: Store password. It is the same as for administrative interface
    :type client_password: str|unicode
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
    ts = datetime.utcnow()
    request = {
        'data': dict(
            data,
            type='PAYOUTS',
            timestamp=ts.strftime('%Y-%m-%dT%H:%M:%SZ'),
            amount=str(data['amount']),
            card=card,
        ),
    }
    url = settings.url_payouts + '?' + urlencode({'walletId': wallet_id})
    r = requests.post(url, json=request, auth=(client_login, client_password))
    if not (200 <= r.status_code < 300) and r.status_code not in (400, 500):
        raise HTTPError(
            u'Expected HTTP response code "200" but '
            u'received "{}"'.format(r.status_code),
            method='POST', url=url, data=request, response=r
        )
    try:
        r_json = json.loads(r.content.decode('utf-8'))
    except ValueError as e:
        raise JSONParsingError(
            u'Failed to parse response from CardPay service: {}'.format(e),
            method='POST', url=url, data=request, content=r.content
        )
    return r_json


def _list(base_url, client_login, client_password, start_millis, end_millis,
          wallet_id=None, max_count=None):
    """Get the list of orders for a period of time. This service will return only orders available for this user to be seen.

    :param base_url: Base API URL to send request to
    :type base_url: str|unicode
    :param client_login: Unique store id. It is the same as for administrative interface
    :type client_login: str|unicode
    :param client_password: Store password. It is the same as for administrative interface
    :type client_password: str|unicode
    :param start_millis: Epoch time in milliseconds when requested period starts (inclusive)
    :type start_millis: int
    :param end_millis: Epoch time in milliseconds when requested period ends (not inclusive), must be less than 7 days after period start
    :type end_millis: int
    :param wallet_id: (optional) Limit result with single WebSite orders
    :type wallet_id: int
    :param max_count: (optional) Limit number of returned orders, must be less than default 10000
    :type max_count: int
    :raises: :class:`PyCardPay.exceptions.HTTPError`, :class:`PyCardPay.exceptions.JSONParsingError`
    :returns: dict

    Return dict structure:

    >>> {
        'data': [
            {
                'id': '299150',         # ID assigned to the order in CardPay
                ...
            },
            ...
        ],
        'hasMore': True     # Indicates if there are more orders for this period than was returned
    }
    """
    params = {
        'startMillis': int(start_millis),
        'endMillis': int(end_millis),
    }
    if wallet_id is not None:
        params['walletId'] = wallet_id
    if max_count is not None:
        params['maxCount'] = max_count
    url = base_url + '?' + urlencode(params)
    r = requests.get(url, auth=(client_login, client_password))
    if r.status_code != 200:
        raise HTTPError(
            u'Expected HTTP response code "200" but '
            u'received "{}"'.format(r.status_code),
            method='GET', url=url, response=r
        )
    try:
        r_json = json.loads(r.content.decode('utf-8'))
    except ValueError as e:
        raise JSONParsingError(
            u'Failed to parse response from CardPay service: {}'.format(e),
            method='GET', url=url, content=r.content
        )
    return r_json


def _status(base_url, id, client_login, client_password,
            settings=live_settings):
    """Use this call to get the status of the transaction by it’s id.

    :param base_url: Base API URL to send request to
    :type base_url: str|unicode
    :param id: Transaction id
    :type id: int
    :raises: :class:`PyCardPay.exceptions.HTTPError`, :class:`PyCardPay.exceptions.JSONParsingError`, :class:`PyCardPay.exceptions.TransactionNotFound`
    :returns: dict

    Return dict structure:

    >>> {
        "data": {
            "id": "12347",
            ...
        }
    }
    """
    url = base_url + '/' + str(id)
    r = requests.get(url, auth=(client_login, client_password))
    if r.status_code == 404:
        raise TransactionNotFound('Payment with ID {} is not found'.format(id))
    elif r.status_code != 200:
        raise HTTPError(
            u'Expected HTTP response code "200" but '
            u'received "{}"'.format(r.status_code),
            method='GET', url=url, response=r
        )
    try:
        r_json = json.loads(r.content.decode('utf-8'))
    except ValueError as e:
        raise JSONParsingError(
            u'Failed to parse response from CardPay service: {}'.format(e),
            method='GET', url=url, content=r.content
        )
    return r_json


def list_payments(client_login, client_password, start_millis, end_millis,
                  wallet_id=None, max_count=None, settings=live_settings):
    """Get the list of orders for a period of time. This service will return only orders available for this user to be seen.

    :param client_login: Unique store id. It is the same as for administrative interface
    :type client_login: str|unicode
    :param client_password: Store password. It is the same as for administrative interface
    :type client_password: str|unicode
    :param start_millis: Epoch time in milliseconds when requested period starts (inclusive)
    :type start_millis: int
    :param end_millis: Epoch time in milliseconds when requested period ends (not inclusive), must be less than 7 days after period start
    :type end_millis: int
    :param wallet_id: (optional) Limit result with single WebSite orders
    :type wallet_id: int
    :param max_count: (optional) Limit number of returned orders, must be less than default 10000
    :type max_count: int
    :raises: :class:`PyCardPay.exceptions.HTTPError`, :class:`PyCardPay.exceptions.JSONParsingError`
    :returns: dict

    Return dict structure:

    >>> {
        'data': [
            {
                'id': '299150',         # ID assigned to the order in CardPay
                'number': 'order00017', # Merchant’s ID of the order
                'state': 'COMPLETED',   # Payment State
                'date': 1438336812000,  # Epoch time when this payment started
                'customerId': '11021',  # Customer’s ID in the merchant’s system
                'declineReason': 'Cancelled by customer', # Bank’s message about order’s decline reason
                'declineCode': '02',    # Code of the decline
                'authCode': 'DK3H25',   # Authorization code, provided by bank
                'is3d': True,           # Was 3-D Secure authentication made or not
                'currency': 'USD',      # Transaction currency
                'amount': '21.12',      # Initial order amount
                'refundedAmount': '7.04', # Refund amount in order’s currency
                'note': 'VIP customer', # Note about the order
                'email': 'customer@example.com', # Customer’s e-mail address
            },
            ...
        ],
        'hasMore': True     # Indicates if there are more orders for this period than was returned
    }
    """
    return _list(settings.url_payments, client_login, client_password,
                 start_millis, end_millis, wallet_id=wallet_id,
                 max_count=max_count)


def payments_status(id, client_login, client_password, settings=live_settings):
    """Use this call to get the status of the payment by it’s id.

    :param id: Transaction id
    :type id: int
    :raises: :class:`PyCardPay.exceptions.HTTPError`, :class:`PyCardPay.exceptions.JSONParsingError`, :class:`PyCardPay.exceptions.TransactionNotFound`
    :returns: dict

    Return dict structure:

    >>> {
        "data": {
            "type": "PAYMENTS",
            "id": "12347",
            "created": "2015-08-28T09:09:53Z",
            "updated": "2015-08-28T09:09:53Z",
            "state": "COMPLETED",
            "merchantOrderId": "955987"
        }
    }
    """
    return _status(settings.url_payments, id, client_login, client_password)


def list_refunds(client_login, client_password, start_millis, end_millis,
                 wallet_id=None, max_count=None, settings=live_settings):
    """Get the list of refunds for a period of time. This service will return only orders available for this user to be seen.

    :param client_login: Unique store id. It is the same as for administrative interface
    :type client_login: str|unicode
    :param client_password: Store password. It is the same as for administrative interface
    :type client_password: str|unicode
    :param start_millis: Epoch time in milliseconds when requested period starts (inclusive)
    :type start_millis: int
    :param end_millis: Epoch time in milliseconds when requested period ends (not inclusive), must be less than 7 days after period start
    :type end_millis: int
    :param wallet_id: (optional) Limit result with single WebSite orders
    :type wallet_id: int
    :param max_count: (optional) Limit number of returned orders, must be less than default 10000
    :type max_count: int
    :raises: :class:`PyCardPay.exceptions.HTTPError`, :class:`PyCardPay.exceptions.JSONParsingError`
    :returns: dict

    Return dict structure:

    >>> {
        'data': [
            {
                "id": "12348",
                "number": "949225",
                "state": "COMPLETED",
                "date": 1444648088000,
                "authCode": "a38cce6d-d889-4d56-8712-9eaf14826464",
                "is3d": False,
                "currency": "EUR",
                "amount": 14.14,
                "customerId": "123",
                "email": "test1@example.com",
                "originalOrderId": "12350"
            },
            ...
        ],
        'hasMore': True     # Indicates if there are more orders for this period than was returned
    }
    """
    return _list(settings.url_refunds, client_login, client_password,
                 start_millis, end_millis, wallet_id=wallet_id,
                 max_count=max_count)


def refunds_status(id, client_login, client_password, settings=live_settings):
    """Use this call to get the status of the refund by it’s id.

    :param id: Transaction id
    :type id: int
    :raises: :class:`PyCardPay.exceptions.HTTPError`, :class:`PyCardPay.exceptions.JSONParsingError`, :class:`PyCardPay.exceptions.TransactionNotFound`
    :returns: dict

    Return dict structure:

    >>> {
        "data": {
            "type": "REFUNDS",
            "id": "12352",
            "created": "2015-10-12T12:34:02Z",
            "updated": "2015-10-12T12:34:02Z",
            "state": "COMPLETED",
            "merchantOrderId": "890081"
        }
    }
    """
    return _status(settings.url_refunds, id, client_login, client_password)


def list_payouts(client_login, client_password, start_millis, end_millis,
                 wallet_id=None, max_count=None, settings=live_settings):
    """Get the list of payouts for a period of time. This service will return only orders available for this user to be seen.

    :param client_login: Unique store id. It is the same as for administrative interface
    :type client_login: str|unicode
    :param client_password: Store password. It is the same as for administrative interface
    :type client_password: str|unicode
    :param start_millis: Epoch time in milliseconds when requested period starts (inclusive)
    :type start_millis: int
    :param end_millis: Epoch time in milliseconds when requested period ends (not inclusive), must be less than 7 days after period start
    :type end_millis: int
    :param wallet_id: (optional) Limit result with single WebSite orders
    :type wallet_id: int
    :param max_count: (optional) Limit number of returned orders, must be less than default 10000
    :type max_count: int
    :raises: :class:`PyCardPay.exceptions.HTTPError`, :class:`PyCardPay.exceptions.JSONParsingError`
    :returns: dict

    Return dict structure:

    >>> {
        'data': [
            {
                "id": "12348",
                "number": "949225",
                "state": "COMPLETED",
                "date": 1444648088000,
                "is3d": False,
                "currency": "EUR",
                "amount": 14.14,
                "number": "12350"
            },
            ...
        ],
        'hasMore': True     # Indicates if there are more orders for this period than was returned
    }
    """
    return _list(settings.url_payouts, client_login, client_password,
                 start_millis, end_millis, wallet_id=wallet_id,
                 max_count=max_count)


def payouts_status(id, client_login, client_password, settings=live_settings):
    """Use this call to get the status of the payout by it’s id.

    :param id: Transaction id
    :type id: int
    :raises: :class:`PyCardPay.exceptions.HTTPError`, :class:`PyCardPay.exceptions.JSONParsingError`, :class:`PyCardPay.exceptions.TransactionNotFound`
    :returns: dict

    Return dict structure:

    >>> {
        "data": {
            "type": "PAYOUTS",
            "id": "12352",
            "created": "2015-10-12T12:34:02Z",
            "updated": "2015-10-12T12:34:02Z",
            "state": "COMPLETED",
            "merchantOrderId": "890081"
        }
    }
    """
    return _status(settings.url_payouts, id, client_login, client_password)
