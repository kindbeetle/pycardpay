# coding=utf-8
from .exceptions import XMLParsingError
from .utils import xml_to_string, xml_get_sha512, make_http_request, parse_response
from decimal import Decimal
from .settings import url_status_change, url_pay, url_status


def status_change(**kwargs):
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
    r = make_http_request(url_status_change, 'post', **kwargs)
    xml = parse_response(r)
    if xml.get('is_executed') != 'yes':
        return {'is_executed': False, 'details': xml.get('details')}
    return {'is_executed': True, 'details': ''}


def status(**kwargs):
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
    r = make_http_request(url_status, 'post', **kwargs)
    xml = parse_response(r)
    data = {'is_executed': True, 'details': '', 'orders': []}

    if xml.get('is_executed') != 'yes':
        data.update({'is_executed': False, 'details': xml.get('details')})
        return data

    for order in xml.xpath('.//orderu'):
        data['orders'].append({
            'id': order.get('id'),
            'status_name': order.get('status_name'),
            'date_in': order.get('date_in'),
            'amount': order.get('amount'),
            'hold_number': order.get('hold_number'),
            'email': order.get('email'),
        })
    return data


def void(**kwargs):
    """Change transaction status to "VOID"

    :param \*\*kwargs: Parameters that :func:`status_change` takes
    :returns: Result from :func:`status_change`
    """
    kwargs.update({'status_to': 'void'})
    return status_change(**kwargs)


def refund(**kwargs):
    """Change transaction status to "REFUND"

    :param \*\*kwargs: See :func:`status_change` for details
    :returns: Result from :func:`status_change`
    """
    kwargs.update({'status_to': 'refund'})
    return status_change(**kwargs)


def capture(**kwargs):
    """Change transaction status to "CAPTURE"

    :param \*\*kwargs: See :func:`status_change` for details
    :returns: Result from :func:`status_change`
    """
    kwargs.update({'status_to': 'capture'})
    return status_change(**kwargs)


def pay(xml, secret):
    """Process payment

    :param xml: Order XML created with :func:`PyCardPay.utils.order_to_xml`
    :type xml: :class:`lxml.etree.Element`
    :param secret: Your CardPay secret password.
    :type secret: str|unicode
    :raises: TypeError if passed not an :class:`lxml.etree.Element` as xml parameter.
    :raises: :class:`PyCardPay.exceptions.XMLParsingError` if response contains unknown xml structure.
    :returns: dict -- see below for description

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
    :func:`PyCardPay.api.finish_3ds`
    """
    order_xml = xml_to_string(xml, encode_base64=True)
    order_sha = xml_get_sha512(xml, secret)
    r = make_http_request(url_pay, method='post', **{'orderXML': order_xml, 'sha512': order_sha})
    r_xml = parse_response(r)

    if r_xml.tag == 'order':
        return {
            'is_3ds_required': False,
            'id': r_xml.get('id'),
            'number': r_xml.get('number'),
            'status': r_xml.get('status'),
            'description': r_xml.get('description'),
        }
    if r_xml.tag == 'redirect':
        return {
            'is_3ds_required': True,
            'url': r_xml.get('url'),
            'MD': r_xml.get('MD'),
            'PaReq': r_xml.get('PaReq'),
        }
    raise XMLParsingError(u'Unknown XML response. Root tag contains no order nor redirect: {}'.format(r))


def finish_3ds(MD, PaRes):
    """Finish 3Ds authorization.

    This method returns the same result as :func:`PyCardPay.api.pay`.

    :param MD: MD value received after payment request from CardPay API.
    :type MD: str|unicode
    :param PaRes: Response code from bank after authorization.
    :type PaRes: str|unicode
    :raises: :class:`PyCardPay.exceptions.XMLParsingError` if response contains unknown xml structure.
    :returns: dict -- see :func:`PyCardPay.api.pay` for description.
    """

    r = make_http_request(url_pay, method='post', MD=MD, PaRes=PaRes)
    r_xml = parse_response(r)

    if r_xml.tag == 'order':
        return {
            'is_3ds_required': False,
            'id': r_xml.get('id'),
            'number': r_xml.get('number'),
            'status': r_xml.get('status'),
            'description': r_xml.get('description'),
        }
    if r_xml.tag == 'redirect':
        return {
            'is_3ds_required': True,
            'url': r_xml.get('url'),
            'MD': r_xml.get('MD'),
            'PaReq': r_xml.get('PaReq'),
        }
    raise XMLParsingError(u'Unknown XML response. Root tag contains no order nor redirect: {}'.format(r))
