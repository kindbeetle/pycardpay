from collections import namedtuple

Settings = namedtuple(
    'Settings',
    [
        'url_status_change',
        'url_status',
        'url_pay',
        'url_payouts',
        'url_payments',
        'url_refunds',
    ],
)


test_settings = Settings(
    url_pay = 'https://sandbox.cardpay.com/MI/cardpayment.html',
    url_status = 'https://sandbox.cardpay.com/MI/service/order-report',
    url_status_change = 'https://sandbox.cardpay.com/MI/service/order-change-status',
    url_payouts = 'https://sandbox.cardpay.com/MI/api/v2/payouts',
    url_payments = 'https://sandbox.cardpay.com/MI/api/v2/payments',
    url_refunds = 'https://sandbox.cardpay.com/MI/api/v2/refunds',
)

live_settings = Settings(
    url_pay = 'https://cardpay.com/MI/cardpayment.html',
    url_status = 'https://cardpay.com/MI/service/order-report',
    url_status_change = 'https://cardpay.com/MI/service/order-change-status',
    url_payouts = 'https://cardpay.com/MI/api/v2/payouts',
    url_payments = 'https://cardpay.com/MI/api/v2/payments',
    url_refunds = 'https://cardpay.com/MI/api/v2/refunds',
)
