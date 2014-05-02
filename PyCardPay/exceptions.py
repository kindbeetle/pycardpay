class PyCardPayException(Exception):
    """Base PyCardPay exception."""
    pass


class XMLParsingError(PyCardPayException):
    """Raised when lxml failed to parse xml from string"""
    def __init__(self, msg, content=None):
        self.content = content
        self.msg = msg
        super(XMLParsingError, self).__init__(msg)


class HTTPError(PyCardPayException):
    """Raised when requests.Response.response_code contains value other than 2xx"""
    pass