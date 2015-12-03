# coding=utf-8
from .exceptions import XMLParsingError, JSONParsingError, HTTPError
from .utils import xml_to_string, xml_get_sha512, xml_http_request
import json
from datetime import datetime
from decimal import Decimal
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
    r_xml = xml_http_request(settings.url_pay, method='post', **data)
    if r_xml.tag == 'redirect':
        return {
            'url': r_xml.get('url'),
        }
    raise XMLParsingError(u'Unknown XML response. Root tag is not redirect: {}'.format(r_xml.tag),
                          method='post', url=settings.url_pay, data=data, content=r_xml)


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
            type = 'PAYOUTS',
            timestamp = ts.strftime('%Y-%m-%dT%H:%M:%SZ'),
            amount = str(data['amount']),
            card = card,
        ),
    }
    r = requests.post(settings.url_payouts,
                      auth=(client_login, client_password),
                      params={'walletId': wallet_id}, json=request)
    if not (200 <= r.status_code < 300) and r.status_code != 400:
        raise HTTPError(u'Expected HTTP response code "200" but received "{}"'.format(r.status_code),
                        method='POST', url=settings.url_payouts, data=request, response=r)
    try:
        r_json = json.loads(r.content.decode('utf-8'))
    except ValueError as e:
        raise JSONParsingError(u'Failed to parse response from CardPay service: {}'.format(e),
                               method='POST', url=settings.url_payouts, data=request, content=r.content)
    return r_json
