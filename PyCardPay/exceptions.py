class PyCardPayException(Exception):
    """Base PyCardPay exception."""
    pass


class ParsingError(PyCardPayException):
    def __init__(self, msg, content=None):
        self.content = content
        self.msg = msg
        super(ParsingError, self).__init__(msg)

class XMLParsingError(ParsingError):
    """Raised when lxml failed to parse xml from string"""
    pass

class JSONParsingError(ParsingError):
    """Raised when failed to parse json from string"""
    pass

class SignatureError(PyCardPayException):
    """Raised when signature doesn't match response"""
    pass

class HTTPError(PyCardPayException):
    """Raised when requests.Response.response_code contains value other than 2xx"""
    pass
