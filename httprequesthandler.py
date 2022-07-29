
import os, re, random, mimetypes, hashlib, gzip
import mimetypes
import random
import re
# to handle url
from urllib.parse import urlparse
# for time formatting
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
from httpbase import HTTPBaseClass

import logging

class HTTPRequestHandler(HTTPBaseClass):

    def __init__(self, host='localhost', port=3000, loglevel=30):
        
        HTTPBaseClass.__init__(self, host, port)
        logging.basicConfig(level=loglevel, format='%(asctime)s :: %(levelname)s :: %(message)s')
        return

    def parse_request(self, request_data):
        
        request_headers = self.request_headers.copy()

        #? Extract method, uri, http ver
        # split request header by crlf
        lines = request_data.split(b'\r\n')
        # split first line into words
        request_line = lines[0].split(b' ')
        # extract request type and decode
        method = request_line[0].decode()

        # get uri and http_version
        path, http_version = None, None
        if(len(request_line) == 3):
            path = request_line[1].decode()
            http_version = request_line[2].decode()
            if(http_version != 'HTTP/1.1'):
                method = 505
        else:
            method = 400

        # now extract http response headers
        if(len(lines) > 1):
            for i in range(1, len(lines)):
                
                #? maxsplit as we only want to seperate out header and its parameters
                line = lines[i].decode().split(' ', maxsplit=1)
                if(line[0] == ''):
                    try:
                        request_headers['request_body'] = lines[i+1]
                    except:
                        pass
                    break
                header = line[0].strip(':')
                header = header.title()
                header_data = ''
                for j in range(1, len(line)):
                    header_data += line[j]
                request_headers.update({header: header_data})

        # If Host header is missing -> 404 must to raised as per RFC
        if(request_headers['Host'] == ''):
            method = 400

        #! also might be some issue due to netloc
        path = urlparse(path)
        path = path.path

        logging.debug(f'Method: {method}\thttp_version: {http_version}\tpath: {path}')
        logging.info('Request has been parsed')

        return method, path, request_headers

    def handle_request(self, request_data):

        # map method to a approriate request handling function
        requests = {
            'GET' : self.handle_GET_HEAD,
            'HEAD': self.handle_GET_HEAD,
            'POST': self.handle_POST,
            'PUT': self.handle_PUT,
            'DELETE': self.handle_DELETE,
            'OPTIONS': self.handle_OPTIONS,
            'TRACE': self.handle_405,
            'PATCH': self.handle_405,
            'CONNECT': self.handle_405,
        }

        method, path, request_data = self.parse_request(request_data)
        self.method = method
              
        # handle connection type
        Max = self.MaxKeepALiveRequests
        timeout = self.KeepAliveTimeout
        if( (request_data['Connection']).lower() == 'keep-alive' and self.KeepALive == 'On'):
            logging.debug('Connection is Keep-Alive')
            keep_alive_params = request_data['Keep-Alive'].split(', ')
            try:
                timeout = int(re.sub('[^0-9]', '', keep_alive_params[0]))
                Max = int(re.sub('[^0-9]', '', keep_alive_params[1]))
            except:
                pass

        # generate and send response
        try:
            try:
                response = requests[method](path, request_data)
                logging.debug(f'Response for request method {method} has been generated')
            except:
                status_code = method
                response = self.handle_status(status_code)
                logging.debug(f'Request may/may not have some errors and was met with {status_code} response')
        except:
            response = self.handle_501(path, request_data)
            logging.error('An error occured while handling the request and will be replied with a 501')

        logging.info(f'Response: {response}')
        return response, request_data['Connection'], Max, timeout
    
    def handle_OPTIONS(self, path, request_data):
        
        crlf = '\r\n'
        response_line = 'HTTP/1.1 ' + str(200) + ' ' + self.status_codes[200] + crlf
        response_headers = 'Allow: ' + self.Allow + crlf
        response_headers += 'Connection: ' + 'close' + crlf
        Time = datetime.now()
        response_headers += 'Date: ' + self.time(Time) + crlf
        response_headers += 'Server: ' + self.response_headers['Server'] + crlf

        try:
            response = bytes(response_line + response_headers + crlf, 'ascii')
        except:
            logging.debug('OPTIONS: Error in generating response')
        
        return response

    def handle_GET_HEAD(self, path, request_data):
        
        response, response_body = self.handle_GET(path, request_data)
        if(self.method == 'GET'):
            response += response_body

        return response

    def handle_GET(self, path, request_data):

        crlf = '\r\n'
        logging.info(f'HEAD/GET: Request data:\n{request_data}\n')
        response_headers = self.response_headers.copy()
        
        # get valid path
        if(path == '/'):
            path = self.PATH + 'index.html'
        if(os.name == 'nt'):
            path = path[1:]
        if(os.access(path, os.F_OK) == False or os.access(path, os.R_OK) == False or os.path.isdir(path) == True):
            status_code = 404
            if(os.access(path, os.F_OK) == False):
                logging.info(f"HEAD/GET: File {path} doesn't exist")
                status_code = 404
            elif(os.access(path, os.R_OK) == False or os.path.isdir(path) == True):
                logging.info(f'HEAD/GET: File {path} either has no read access or is a directory')
                status_code = 403
            
            response = self.handle_status(status_code)
            return response, b''
        logging.info(f'HEAD/GET: Path {path} requested is valid')
   
        # valid path -> getting headers
        response_line = 'HTTP/1.1 ' + str(200) + ' ' + self.status_codes[200] + crlf
        last_modified = datetime.utcfromtimestamp(os.path.getmtime(path))
        response_headers['Last-Modified'] = self.time(last_modified)
    
        content_type = mimetypes.guess_type(path)[0] or 'text/html'
        response_headers['Content-Type'] = content_type

        # check if content type is supported
        type = (content_type.split('/'))[0]
        if(type == 'audio' or type == 'video'):
            response = self.handle_status(415)
            return response, b''

        try:
            # get the accept header to see which content types are accepted by client
            request_accept = request_data['Accept'].split(',')
            for i in range(len(request_accept)):
                request_accept[i] = (request_accept[i].split(';'))[0]
            logging.debug(f'Accept header in request: {request_accept}\n')
        
            # check if content_type is accepted by client
            logging.debug(f'Content types accepted by client: {request_accept}, content-type of path: {content_type}')
            if(content_type not in request_accept):
                response = self.handle_request(406)
                return response, b''
        except:
            logging.debug('HEAD/GET: No accept type mentioned in request')

        #content length
        content_length = os.path.getsize(path)
        response_headers['Content-Length'] = str(content_length)
        
        # checking for connection type
        if(request_data['Connection'] == 'keep-alive' and self.KeepALive == 'On'):
            logging.debug('HEAD/GET: Connection type is Keep-Alive')
            response_headers['Connection'] = 'keep-alive'
        else:
            logging.debug('Connection type is close')
            response_headers['Connection'] = 'close'

        # checking for cookies
        try:
            if(request_data['Cookie'] != ''):
                response_headers['Set-Cookie'] = str(self.cookies(path, None))
                logging.debug('HEAD/GET: Cookies requested and set')
        except:
            logging.debug('GET/HEAD: No cookies were requeseted')
            pass
        
        # read file
        try:
            temp_response_line, response_body, response_headers = self.file_RW('GET', path, request_data, response_headers)
            if(temp_response_line != ""):
                response_line = temp_response_line
            logging.debug(f'HEAD/GET: File {path} succesfully read')
        except:
            #some error message -> internal server error?
            logging.error(f'HEAD/GET: Unable to read File {path}')
            pass

        # try:
        #     # get accpet-encoding data -> currently ignores q values
        #     #? server currently only performs gzip encoding
        #     #! should i change to substring matching instead?
        #     request_accept_encoding = request_data['Accept-Encoding'].split(',')
        #     for i in range(len(request_accept_encoding)):
        #         request_accept_encoding[i] = (request_accept_encoding[i].split(';'))[0]

        #     #! content-encoding, doesnt work on text/html files currently
        #     if(content_type != 'text/html'):
        #         for encodings in request_accept_encoding:
        #             if(encodings == 'gzip'):
        #                 response_body = gzip.compress(response_body)
        #                 response_headers['Content-Encoding'] = 'gzip'
        #                 logging.debug('response_body encoded with gzip')
        #                 break
        #         else:
        #             response_body = gzip.compress(response_body)
        #             response_headers['Transfer-Encoding'] =  'gzip'
        #             logging.debug('response_body transfer-encoding gzip')
        # except:
        #     logging.debug('HEAD/GET: Either no accept-encoding was given or encoding failed')
        #     pass

        try:
            # build response
            Time = datetime.now()
            response_headers['Date'] = self.time(Time)
            response = response_line
            for key, value in response_headers.items():
                if(value != ''):
                    response += key + ': ' + value + crlf
            response = bytes(response + crlf, 'ascii')
        except:
            logging.info('Response headers succesfully build')
            pass
        
        return response, response_body

    def handle_POST(self, path, request_data):
        
        response_headers = self.response_headers.copy()

        if(path == '/'):
            path = self.PATH + 'index.html'
        if(os.name == 'nt'):
            path = path[1:]
        if(os.access(path, os.F_OK) or os.path.isdir(path)):
            logging.debug(f'POST: {path}')
            status_code = 403
            response = self.handle_status(status_code, {'Content-Type': request_data['Content-Type']})
            return response

        logging.debug(f'POST" Writing data in {path}')
        with open(path, 'wb') as file:
            file.write(request_data['request_body'])
            file.close()

        crlf = '\r\n'
        
        logging.debug(f'POST: Finding status_code')
        if(request_data['Content-Length'] == '0'):
            status_code = 204
        else:
            status_code = 201

        response_line = 'HTTP/1.1 ' + str(status_code) + ' ' + self.status_codes[status_code] + crlf
        if(status_code == 201):
            response_headers['Content-Location'] = str(path)
            last_modified = datetime.utcfromtimestamp(os.path.getctime(path))
            response_headers['Last-Modified'] = self.time(last_modified)
        
        logging.debug(f'POST: status_code {status_code}')
        Time = datetime.now()       
        response_headers['Date']  = self.time(Time)
        response_headers['Content-Length'] = request_data['Content-Length']
        response_headers['Content-Type'] = request_data['Content-Type']

        # checking for connection type
        if(request_data['Connection'] == 'keep-alive' and self.KeepALive == 'On'):
            response_headers['Connection'] = 'keep-alive'
        else:
            response_headers['Connection'] = 'close'
            
        try:
            response = response_line
            for key, value in response_headers.items():
                if(value != ''):
                    response += key + ': ' + value + crlf
            response = bytes(response + crlf, 'ascii')
        except:
            pass
    
        return response

    def handle_PUT(self, path, request_data):

        #!needs to handle content-ranges
        # first lets make it to just replace the entire file
        
        # this is responsible to update a file
        # post to create -> change post according;y
        # put to update or create file if it doesnt exist
        # if it exist -> overwrite

        response_headers = self.response_headers.copy()

        if(path == '/'):
            path = self.PATH + 'index.html'
        if(os.name == 'nt'):
            path = path[1:]
        if(os.path.isdir(path)):
            response = self.handle_status(403)
            return response

        status_code = 201
        if(os.path.exists(path)):
            if(os.access(path, os.W_OK)):
                status_code = 200
            elif(os.path.isdir(path)):
                response = self.handle_status(403)
                return response
    
        try:
            response_headers = self.file_RW('PUT', path, request_data, response_headers)
        except:
            response = self.handle_status(202)
            return response

        crlf = '\r\n'
        try:
            if(os.path.getsize(path) == 0):
                status_code = 204
        
            response_line = 'HTTP/1.1 ' + str(status_code) + ' ' + self.status_codes[status_code] + crlf
            if(status_code == 201):
                last_modified = datetime.utcfromtimestamp(os.path.getmtime(path))
                response_headers['Last-Modified'] = self.time(last_modified)
                response_headers['Content-Location'] = str(path)
            
            Time = datetime.now()
            response_headers['Date']  = self.time(Time)
            response_headers['Content-Length'] = request_data['Content-Length']
            response_headers['Content-Type'] = request_data['Content-Type']

            # checking for connection type
            if(request_data['Connection'] == 'keep-alive' and self.KeepALive == 'On'):
                response_headers['Connection'] = 'keep-alive'
            else:
                response_headers['Connection'] = 'close'
            
            response_body = b''
        except:
            response = self.handle_status(404)
            return response
        
        try:
            response = response_line
            for key, value in response_headers.items():
                if(value != ''):
                    response += key + ': ' + value + crlf
            response = bytes(response + crlf, 'ascii') + response_body
        except:
            pass

        return response

    def handle_DELETE(self, path, request_data):
        
        # this will delete the file and send a success response if deleted succesfully
        # what will it send if it isnt present -> maybe success as it can be considerd deleted?
        # just need the file path and delete if it exists
        # doesnt need to do anything if already deleted
        # generate response accordingly

        content_type = mimetypes.guess_type(path)[0] or 'text/html'
        content_length = 0

        status_code = 204
        if(os.path.exists(path)):
            content_length = os.path.getsize(path)
            os.remove(path)
            status_code = 200
            logging.info(f'DELETE: File {path} succesfully deleted')
        else:
            logging.info(f'DELETE: File {path} has been previously deleted')

        crlf = '\r\n'
        response_line = 'HTTP/1.1 ' + str(status_code) + ' ' + self.status_codes[status_code] + crlf
        Time = datetime.now()
        response_headers = 'Date: ' + self.time(Time) + crlf
        response_headers += 'Server: ' + self.response_headers['Server'] + crlf
        response_headers += 'Content-Length: ' + str(content_length) + crlf
        response_headers += 'Content-Type: ' + str(content_type) + crlf
        response_headers += 'Connection: ' + 'close' + crlf

        try:
            response = bytes(response_line + response_headers + crlf, 'ascii')
        except:
            logging.debug('DELETE: Error in generating response')
            pass

        return response

    def handle_status(self, status_code, *args):

        crlf = '\r\n'
        response_line = 'HTTP/1.1 ' + str(status_code) + ' ' + str(self.status_codes[status_code]) + crlf
        
        response_headers = ''
        Time = datetime.now()
        response_headers = 'Date: ' + self.time(Time) + crlf
        response_headers += 'Server: ' + self.response_headers['Server'] + crlf
        response_headers += 'Connection: ' + 'close' + crlf

        try:
            request_data = args[0]
            for key, value in request_data.items():
                response_headers += str(key) + ': ' + str(value) + crlf
        except:
            pass

        response_body = b''
        if(status_code >= 400):
            response_body = bytes(f'<h1>Error {status_code}: {self.status_codes[status_code]}</h1>', 'ascii')

        response = bytes(response_line + response_headers + crlf, 'ascii') + response_body
        return response

    def handle_501(self, path, request_data):
        
        crlf = '\r\n'  
        response_line = 'HTTP/1.1 ' + str(501) + ' ' + self.status_codes[501] + crlf
        Time = datetime.now()
        response_headers = 'Date: ' + self.time(Time) + crlf
        response_headers += 'Server: ' + self.response_headers['Server'] + crlf
        response_headers += 'Connection: ' + 'close' + crlf

        response = bytes(response_line + response_headers + crlf, 'ascii')
        return response

    def handle_405(self, path, request_data):
        
        crlf = '\r\n'
        response_line = 'HTTP/1.1 ' + str(405) + ' ' + self.status_codes[405] + crlf
        response_headers = 'Allow: ' + self.Allow + crlf
        response_headers += 'Connection: ' + 'close' + crlf
        Time = datetime.now()
        response_headers += 'Date: ' + self.time(Time) + crlf
        response_headers += 'Server: ' + self.response_headers['Server'] + crlf

        response = bytes(response_line + response_headers + crlf, 'ascii')
        return response

    def time(self, Time):
            
        tstamp = mktime(Time.timetuple())
        time = format_date_time(tstamp)
        logging.debug(f'Calculated time is: {time}')
        return time

    def cookies(self, path, cookie_data):

        # create randon int and store in a cookie file
        # if called again the ++ -> basic file handling

        # what is a cookie file -> plain txt file to store randint
        # [path_head]/cookie_[path_tail] -> os.path.split()
        

        cookie_file = str(os.path.split(path)[0])+ '/cookie_'+ str(os.path.split(path)[1]) + '.txt'
        cookie = 0
        if(os.path.exists(cookie_file) ):
            logging.debug('Retriving cookies')
            with open(cookie_file, 'r') as file:
                cookie = int(file.read())
                file.close()

            cookie += 1
            logging.debug('Rewriting cookies')
            with open(cookie_file, 'w') as file:
                file.write(str(cookie))
                file.close()

        else:
            logging.debug('Creating cookies')
            with open(cookie_file, 'w') as file:
                cookie = random.randint(1,100)
                file.write(str(cookie))
                file.close()

        logging.info(f'Cookies: {cookie}')
        return cookie

    def file_RW(self, method, path, request_data, response_headers):
        
        # responsible for file reading and writing for GET, HEAD, PUT

        response_body = b''
        crlf = '\r\n'

        if(method == 'GET'):
            content_length = int(response_headers['Content-Length'])
        else:
            content_length = int(request_data['Content-Length'])
        # handle ranges
        start = 0
        end = content_length
        try:
            request_accept_ranges = request_data['Accept-Ranges']
            if(request_accept_ranges == 'bytes'):
                logging.info('Getting ranges')
                request_range = request_data['Range'].strip().strip('bytes=').split(',')
                for i in range(len(request_range)):
                    start, end = request_range[i].split('-')
                    request_range[i] = [start.strip(), end.strip()]
                response_line = 'HTTP/1.1 ' + str(206) + ' ' + self.status_codes[206] + crlf
                response_headers['Accept-Ranges'] = request_data['Accept-Ranges']
                response_headers['Content-Range'] = request_data['Range']
        except:
            request_range = [[str(start), str(end)]]
        logging.debug(f'Content Ranges: {request_range}')

        if(method == 'GET'):
            with open(path, 'rb') as file:
                prevstart=0
                for i in range(len(request_range)):
                    start = request_range[i][0]
                    if(start == ''):
                        end = int(request_range[i][1])
                        start = content_length - end
                        end = content_length
                    else:
                        start = int(start)
                        end = int(request_range[i][1])
                    file.seek(start-prevstart)
                    response_body = file.read(end-start+1)
                    prevstart = end
                file.close()
            response_headers['Content-MD5'] = str((hashlib.md5(response_body)).hexdigest())
            logging.info(f'HEAD/GET: response_body:\n{response_body}\n')
        elif(method == 'PUT'):
            with open(path, mode='rb+') as file:
                prevstart=0
                for i in range(len(request_range)):
                    start = request_range[i][0]
                    if(start == ''):
                        end = int(request_range[i][1])
                        start = content_length - end
                        end = content_length
                    else:
                        start = int(start)
                        end = int(request_range[i][1])
                    logging.info(f'PUT: Range start {start} end {end}')
                    data = request_data['request_body'][start:end+1]
                    logging.info(f'PUT: Data {data}')
                    file.seek(start-prevstart)
                    n = len(request_data['request_body'])
                    if(start >= n):
                        start -= n
                        end -= n
                        file.write(request_data['request_body'][start:end+1])
                        end += n
                    file.write(request_data['request_body'][start:end+1])
                    prevstart = end
                file.close()
           
        if(method=='GET'):
            try:
                return response_line, response_body, response_headers
            except:
                return "", response_body, response_headers
        elif(method=='PUT'):
            return response_headers

if __name__ == '__main__':
    
    logging.basicConfig(level=logging.INFO)
    server = HTTPRequestHandler()
    server.start()