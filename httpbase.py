
import tcpserver
import json

class HTTPBaseClass(tcpserver.TCPServer):

    response_headers = {
        'Accept-Ranges': '',
        'Connection': '',
        'Content-Encoding': '',
        'Content-Length': '',
        'Content-Location': '',
        'Content-MD5': '',
        'Content-Range': '',
        'Content-Type': '',
        'Date':'',
        'Last-Modified': '',
        'Server': 'Server_3146',
        'Set-Cookie': '',
        'Transfer-Encoding': '',
    }
    request_headers = {
        'Accept': '',
        'Accept-Encoding': '',
        'Accept-Charset': '',#! not doing
        'Connection': '',
        'Content-Encoding':'',
        'Content-Length':'',
        'Content-Location': '',
        'Content-Type':'',
        'Cookie':'',
        'Date':'',
        'Host':'',
        'If-Modified-Since':'',#! not doing
        'If-Range':'',#! no doing
        'If-Unmodified-Since':'',#! not doing
        'Keep-Alive':'',
        'Range':'',
        'Transfer-Encoding':'',#? not sure but done -> apply this if content-encoding is not gzip
        'User-Agent':''
    }
    # all status_codes may or may not be handled by this server
    status_codes = {
        
        100: 'Continue',
        101: 'Switching Protocol',
        102: 'Processing',
        103: 'Early Hints',

        200: 'OK',
        201: 'Created',
        202: 'Accepted',
        203: 'Non-Authoritative Information',
        204: 'No Content',
        205: 'Reset Content',
        206: 'Partial Content',
        207: 'Multi-Status',
        208: 'Already Reported',
        226: 'IM Used',

        300: 'Multiple Choice',
        301: 'Moved Permanetly',
        302: 'Found',
        303: 'See Other',
        304: 'Not Modified',
        307: 'Temporary Redirect',
        308: 'Permanent Redirect',
        
        400: 'Bad Request',
        401: 'Unauthorized',
        402: 'Payment Required',
        403: 'Forbidden',
        404: 'Not Found',
        405: 'Method Not Allowed',
        406: 'Not Acceptable',
        407: 'Proxy Authentication Required',
        408: 'Request Timeout',
        409: 'Conflict',
        410: 'Gone',
        411: 'Length Required',
        412: 'Precondition Failed',
        413: 'Payload Too Large',
        415: 'Unsupported Media Type',
        416: 'Range Not Satisfiable',
        417: 'Expectation Failed',
        418: "I'm a teapot",
        421: 'Misdirected Request',
        425: 'Too Early',
        426: 'Upgrade Required',
        428: 'Precondition Required',
        429: 'Too Many Requests',
        431: 'Request Header Fields Too Large',
        451: 'Unavailable For Legal Reasons',

        500: 'Internal Server Error',
        501: 'Not Implemented',
        502: 'Bad Gateway',
        503: 'Service Unavailable',
        504: 'Gateway Timeout',
        505: 'HTTP Version Not Supported',
        506: 'Variant Also Negotiates',
        507: 'Insufficient Storage',
        508: 'Loop Detected',
        510: 'Not Extended',
        511: 'Network Authentication Required'
    }  

    def __init__(self, host='localhost', port=3000):
        
        with open('./httpconfig.json', 'r') as file:
            httpconfigdata = json.load(file)
            file.close()

        self.method = None
        self.Allow = httpconfigdata['Allow']
        self.PATH = httpconfigdata['PATH']
        self.KeepALive = httpconfigdata['KeepAlive']
        self.MaxKeepALiveRequests = httpconfigdata['MaxKeepAliveRequests']
        self.KeepAliveTimeout = httpconfigdata['KeepAliveTimeout']

        tcpserver.TCPServer.__init__(self, host, port)
        return

if __name__ == '__main__':
    server = HTTPBaseClass()
    server.start()