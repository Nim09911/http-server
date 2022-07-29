
#$ Multi-threaded implementation of TCP server

import socket, threading, time
import logging, json

'''
#TODO: 
    #* Create seperate recv function for tcp only
    #* Shift current recv to http base class
    #* Shift tcpconfig data to httpconfig data
'''

class TCPServer:

    def __init__(self, host='localhost', port=3000):
        
        self.host = host
        self.port = port
        self.clients = []

        with open('./tcpconfig.json', 'r') as file:
            tcpconfigdata = json.load(file)
            file.close()

        self.KeepAlive = tcpconfigdata['KeepAlive']
        self.MaxConnections = tcpconfigdata['MaxConnections']
        return

    def start(self):

        # create and bind a reusable tcp socket and make it listen
        self.tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcpsock.bind((self.host, self.port))
        self.tcpsock.listen()

        logging.info(f'Server Listening at ({self.host}, {self.port})')
        self.connect()

    def connect(self):
        
        while True:
            try:
                if(len(self.clients) <= self.MaxConnections):
                    client, addr = self.tcpsock.accept()
                    logging.info(f'Connected by {addr}')
                    thread = threading.Thread(target=self.handle_connection, args=(client,))
                    self.clients.append([client, thread])
                    try:
                        thread.start()
                        logging.debug(f'thread for {addr} started')
                    except:
                        logging.debug(f'thread {thread} failed to start')
                        try:
                            thread.join()
                            logging.debug(f'thread for {addr} failed to join')
                            self.close_conn(client)
                        except:
                            logging.error(f'Failed to close connection')
                else:
                    logging.info('Server Max connections reached')
                    time.sleep(1)
            except:
                logging.critical('Error while trying to establish connection')
                break
        return

    def handle_connection(self, client):

        # Create a thread for recv, recv internally handles
        # recv, send, keep-alive      

        try:
            thread_recv = threading.Thread(target=self.recv, args=(client,))
            thread_recv.start()
            logging.debug(f'thread {thread_recv} started')
        except:
            logging.debug(f'thread {thread_recv} failed to start')
            try:
                thread_recv.join()
                logging.debug(f'thread {thread_recv} joined')
            except:
                logging.debug(f'thread {thread_recv} failed to join')
            self.close_conn(self, client)
        return

    def recv(self, client):
        
        # recv data and get response from http server
        data = client.recv(4096)
        response_data, connection, Max, timeout = self.handle_request(data)
        
        # start send thread to send data
        thread_send = threading.Thread(target=self.send, args=(client, response_data))
        try:
            thread_send.start()
            logging.debug(f'thread {thread_send} started')
            time.sleep(1)
        except:
            logging.debug(f'thread {thread_send} failed to start')
        try:
            thread_send.join(timeout=1.0)
            logging.debug(f'thread {thread_send} joined')
        except:
            logging.debug(f'thread {thread_send} failed to join')

        if(connection == 'keep-alive' and self.KeepAlive == 'On'):
                timer = time.time()
                Max = Max
                timeout = timeout
                logging.info('Keep-Alive started')
                i = 0   # keep count of total times connection has sent request
                while( (time.time() - timer < timeout) and i < Max):
                    
                    try:
                        data = client.recv(4096)
                        if(data == b''):
                            continue
                        
                        i += 1
                        response_data, connection, Max, timeout =  self.handle_request(data)
                        thread_send = threading.Thread(target=self.send, args=(client, response_data))
                        try:
                            thread_send.start()
                            time.sleep(1)
                        except:
                            logging.debug(f'thread {thread_send} failed to start') 
                        try:
                            thread_send.join(timeout=1.0)
                        except:
                            logging.debug(f'thread {thread_send} failed to join')
                    except:
                        self.close_conn(client)
                        return
                    
                    if(connection == 'close'):
                        logging.info('Connection: close encountered while Keep-Alive')
                        break
                else:
                    logging.info('Keep-Alive connection over')

        try:
            self.close_conn(client)
        except:
            pass
        return

    def send(self, client, response_data):
        
        try:
            client.sendall(response_data)
            logging.info('Response succesfully sent')
        except:
            logging.error('Error in sending response data')
        return

    def close_conn(self, client):
        
        for i in range(len(self.clients)):
            if(self.clients[i][0] == client):
                try:
                    self.clients[i][1].join()
                    logging.debug(f'thread {self.clients[i][1]} joined')
                except:
                    logging.debug(f'thread {self.clients[i][1]} failed to join')
                try:
                    client.close()
                    logging.debug(f'connection {client} closed')
                except:
                    logging.debug(f'connection {client} failed to close')
                self.clients.pop(i)
        return
    
    def stop(self):
        
        # Currently isnt being used/accessed
        
        for Client in self.clients:
            self.close_conn(Client)
        self.tcpsock.close()
        return

    def handle_request(self, data):
        # abstract
        return (b'HTTP/1.1 201 Accepted\r\n\r\n <h1>Request Parsed</h1>'), 'close', 0, 0

if __name__ == '__main__':
    
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s :: %(levelname)s :: %(message)s')
    server = TCPServer()
    try:
        server.start()
    except:
        server.stop()
