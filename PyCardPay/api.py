# coding=utf-8
from .exceptions import XMLParsingError
from .utils import xml_to_string, xml_get_sha512, make_http_request, parse_response
from decimal import Decimal
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
    r = make_http_request(settings.url_status_change, 'post', **kwargs)
    xml = parse_response(r)
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
    r = make_http_request(settings.url_status, 'post', **kwargs)
    xml = parse_response(r)
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
    r = make_http_request(settings.url_pay, method='post', **{'orderXML': order_xml, 'sha512': order_sha})
    r_xml = parse_response(r)
    if r_xml.tag == 'redirect':
        return {
            'url': r_xml.get('url'),
        }
    raise XMLParsingError(u'Unknown XML response. Root tag is not redirect: {}'.format(r))
