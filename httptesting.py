from httprequesthandler import HTTPRequestHandler as HTTP
import threading
from socket import *
import os
import colorama
import time

class Test():

    def __init__(self, host='localhost', port=3000):
        
        self.host = host
        self.port = port
        self.testsock = socket(AF_INET, SOCK_STREAM)
        return

    def send_and_recv(self, req):

        self.testsock.connect((self.host, self.port))
        self.testsock.sendall(req)
        response = self.testsock.recv(4096)
        return response

    def parse_response(self, response):
        
        response_headers = {}

        # split request header by crlf
        lines = response.split(b'\r\n')
        response_line = lines[0].decode()        

        # now extract http response headers
        if(len(lines) > 1):
            for i in range(1, len(lines)):
                
                #? maxsplit as we only want to seperate out header and its parameters
                line = lines[i].decode().split(' ', maxsplit=1)
                if(line[0] == ''):
                    try:
                        response_headers['response_body'] = lines[i+1]
                    except:
                        pass
                    break
                header = line[0].strip(':')
                header = header.title()
                header_data = ''
                for j in range(1, len(line)):
                    header_data += line[j]
                response_headers.update({header: header_data})

        return response_line, response_headers

    def close(self):
        self.testsock.close()

class Method_Tester(Test):

    def __init__(self, method='method', request=b'', response=b'', host='localhost', port=3000):
        
        Test.__init__(self, host, port)
        self.req = request
        self.res = response
        self.method = method
        
        response = self.send_and_recv(self.req)
        self.response = self.parse_response(response)
        self.test()
    
    def test(self):
        try:
            response_line = self.response[0]
            assert response_line == self.res
            print(colorama.Fore.GREEN + f'Request: {self.req}')
            print(f'Response: {response_line}\r\n {self.response[1]}')
            print(f'Test {self.method} passed, Asserted: {response_line}, Expected: {self.res}' + colorama.Fore.WHITE)
        except:
            print(colorama.Fore.RED + f'Request: {self.req}')
            print(f'Response: {response_line}\r\n {self.response[1]}')
            print(colorama.Fore.RED + f'Test {self.method} failed, Asserted: {response_line}, Expected: {self.res}' + colorama.Fore.WHITE)
        print()
        self.close()
        return

class ThreadingTest():

    def __init__(self, host='localhost', port=3000):
        self.host = host
        self.port = port
        self.optionsreq = (bytes('OPTIONS * HTTP/1.1\r\n' + 'Host: localhost\r\n' + 'Connection: keep-alive\r\n' + 'Keep-Alive: timeout=15, max=5' + '\r\n', 'ascii'))
        self.optionsres = 'HTTP/1.1 200 OK'
        self.testsock = socket(AF_INET, SOCK_STREAM)
        self.testsock.connect((self.host, self.port))
        return

    def connect(self):
        self.testsock.sendall(self.optionsreq)
        response = self.testsock.recv(4096)
        response = response.split(b'\r\n')
        response_line = response[0].decode()
        print(colorama.Fore.GREEN + f'Thread result: {response_line}' + colorama.Fore.WHITE)
        return      


    def start_test(self):
        print('Test for Threading (Keep-Alive), starting 5 threads')
        thread_1 = threading.Thread(target=self.connect)
        thread_2 = threading.Thread(target=self.connect)
        thread_3 = threading.Thread(target=self.connect)
        thread_4 = threading.Thread(target=self.connect)
        thread_5 = threading.Thread(target=self.connect)
        
        thread_1.start()
        time.sleep(1)
        thread_2.start()
        time.sleep(1)
        thread_3.start()
        time.sleep(1)
        thread_4.start()
        time.sleep(1)
        thread_5.start()
        time.sleep(1)

        thread_1.join()
        thread_2.join()
        thread_3.join()
        thread_4.join()
        thread_5.join()
        self.testsock.close()
        return

PATH = '/var/www/html/tmp/'

print('Test Trace')
tracereq = (bytes('TRACE / HTTP/1.1\r\n' + 'Host: localhost\r\n'+ '\r\n', 'ascii'))
traceres = 'HTTP/1.1 405 Method Not Allowed'
test = Method_Tester('TRACE', tracereq, traceres)

print('Test Connect')
connectreq = (bytes('CONNECT / HTTP/1.1\r\n' + 'Host: localhost\r\n'+ '\r\n', 'ascii'))
connectres = 'HTTP/1.1 405 Method Not Allowed'
test = Method_Tester('CONNECT', connectreq, connectres)

print('Test Options')
optionsreq = (bytes('OPTIONS / HTTP/1.1\r\n' + 'Host: localhost\r\n'+ '\r\n', 'ascii'))
optionsres = 'HTTP/1.1 200 OK'
test = Method_Tester('OPTIONS', optionsreq, optionsres)

try:
    os.remove('test_files/post.json')
except:
    pass

print('Test Post')
postreq = post_request = bytes( 
        f'POST test_files/post.json HTTP/1.1\r\n' +
        'Host: Server_3146\r\n' +
        'Content-Type: application/json\r\n' +
        'Content-Length: 70\r\n' +
        '\r\n'+
        str({
        "Id": 12345,
        "Customer": "John Smith",
        "Quantity": 1,
        "Price": 10.00}), 
        'ascii')
postres = 'HTTP/1.1 201 Created'
test = Method_Tester('POST', postreq, postres)

postreq = post_request = bytes( 
        f'POST test_files/post_delete.json HTTP/1.1\r\n' +
        'Host: Server_3146\r\n' +
        'Content-Type: application/json\r\n' +
        'Content-Length: 80\r\n' +
        '\r\n'+
        str({
        "Id": 12345,
        "Customer": "John Smith",
        "Quantity": 1,
        "Price": 10.00}), 
        'ascii')
postres = 'HTTP/1.1 201 Created'
test = Method_Tester('POST', postreq, postres)

print('Test Delete')
deletereq = (bytes(f'DELETE test_files/post_delete.json HTTP/1.1\r\n' + 'Host: localhost\r\n'+ '\r\n', 'ascii'))
deleteres = 'HTTP/1.1 200 OK'
test = Method_Tester('DELETE', deletereq, deleteres)

deletereq = (bytes(f'DELETE test_files/post_delete.json HTTP/1.1\r\n' + 'Host: localhost\r\n'+ '\r\n', 'ascii'))
deleteres = 'HTTP/1.1 204 No Content'
test = Method_Tester('DELETE', deletereq, deleteres)

print('Test Put')
putreq = put_request = bytes( 
        f'PUT test_files/post.json HTTP/1.1\r\n' +
        'Accept-Ranges: bytes\r\n' +
        'Range: bytes=0-10, -10\r\n'
        'Host: Server_3146\r\n' +
        'Content-Type: application/json\r\n' +
        'Content-Length: 77\r\n' +
        '\r\n'+
        str({
        "Id": 111903146,
        "Customer": "Nimit Jain",
        "Quantity": 1,
        "Price": "Limitless"}), 
        'ascii')
putres = 'HTTP/1.1 200 OK'
test = Method_Tester('PUT', putreq, putres)

print('Test Get')
getreq = (bytes('GET / HTTP/1.1\r\n' + 'Host: localhost\r\n'+ '\r\n', 'ascii'))
getres = 'HTTP/1.1 200 OK'
test = Method_Tester('GET', getreq, getres)

print('Cookies, Encoding')
getreq = (bytes(f'GET test_files/post.json HTTP/1.1\r\n' + 'Accept-Encoding: gzip\r\n' + 'Accept-Ranges: bytes\r\n' + 'Cookie: i want cookie plz\r\n' + 'Range: bytes=0-10, -10\r\n' + 'Host: localhost\r\n'+ '\r\n', 'ascii'))
getres = 'HTTP/1.1 206 Partial Content'
test = Method_Tester('GET', getreq, getres)

print('Test Get')
getreq = (bytes('GET / HTTP/1.1\r\n'+ '\r\n', 'ascii'))
getres = 'HTTP/1.1 400 Bad Request'
test = Method_Tester('GET', getreq, getres)

getreq = (bytes(f'GET /var/www/html/tmp/ HTTP/1.1\r\n' + 'Host: localhost\r\n'+ '\r\n', 'ascii'))
getres = 'HTTP/1.1 403 Forbidden'
test = Method_Tester('GET', getreq, getres)

getreq = (bytes(f'GET /var/www/html/tmp/somefile.txt HTTP/1.1\r\n' + 'Host: localhost\r\n'+ '\r\n', 'ascii'))
getres = 'HTTP/1.1 404 Not Found'
test = Method_Tester('GET', getreq, getres)

getreq = (bytes(f'GET test_files/trial.mp4 HTTP/1.1\r\n' + 'Host: localhost\r\n'+ '\r\n', 'ascii'))
getres = 'HTTP/1.1 415 Unsupported Media Type'
test = Method_Tester('GET', getreq, getres)

test = ThreadingTest()
test.start_test()