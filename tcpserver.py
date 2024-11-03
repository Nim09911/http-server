import socket
import threading
import time
import logging
import json

class TCPServer:
    def __init__(self, host='localhost', port=3000):
        self.host = host
        self.port = port
        self.clients = []

        with open('./tcpconfig.json', 'r') as file:
            tcpconfigdata = json.load(file)

        self.KeepAlive = tcpconfigdata.get('KeepAlive', 'Off')
        self.MaxConnections = tcpconfigdata.get('MaxConnections', 5)

    def start(self):
        # Create and bind a reusable TCP socket and make it listen
        self.tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcpsock.bind((self.host, self.port))
        self.tcpsock.listen(self.MaxConnections)

        logging.info(f'Server Listening at ({self.host}, {self.port})')
        self.connect()

    def connect(self):
        while True:
            try:
                if len(self.clients) < self.MaxConnections:
                    client, addr = self.tcpsock.accept()
                    logging.info(f'Connected by {addr}')
                    thread = threading.Thread(target=self.handle_connection, args=(client,))
                    thread.start()
                    self.clients.append((client, thread))
                else:
                    logging.info('Max connections reached; retrying in 1 second')
                    time.sleep(1)
            except Exception as e:
                logging.critical(f'Error establishing connection: {e}')
                break

    def handle_connection(self, client):
        # Handle the client connection by starting the recv process
        try:
            thread_recv = threading.Thread(target=self.recv, args=(client,))
            thread_recv.start()
        except Exception as e:
            logging.error(f'Failed to start receive thread: {e}')
            self.close_conn(client)

    def recv(self, client):
        try:
            data = client.recv(4096)
            if not data:
                self.close_conn(client)
                return
            
            response_data, connection, Max, timeout = self.handle_request(data)
            self.send(client, response_data)

            if connection == 'keep-alive' and self.KeepAlive == 'On':
                self.handle_keep_alive(client, Max, timeout)
            else:
                self.close_conn(client)
        except Exception as e:
            logging.error(f'Error in recv: {e}')
            self.close_conn(client)

    def handle_keep_alive(self, client, max_requests, timeout):
        timer = time.time()
        request_count = 0
        logging.info('Keep-Alive mode active')

        while (time.time() - timer < timeout) and request_count < max_requests:
            try:
                data = client.recv(4096)
                if not data:
                    continue

                request_count += 1
                response_data, connection, _, _ = self.handle_request(data)
                self.send(client, response_data)

                if connection == 'close':
                    logging.info('Connection closed during Keep-Alive')
                    break
            except Exception as e:
                logging.error(f'Error in keep-alive loop: {e}')
                break

        logging.info('Ending Keep-Alive session')
        self.close_conn(client)

    def send(self, client, response_data):
        try:
            client.sendall(response_data)
            logging.info('Response sent successfully')
        except Exception as e:
            logging.error(f'Error sending response: {e}')
            self.close_conn(client)

    def close_conn(self, client):
        for idx, (cl, thread) in enumerate(self.clients):
            if cl == client:
                try:
                    client.close()
                    logging.info(f'Connection {client} closed')
                except Exception as e:
                    logging.error(f'Error closing connection: {e}')
                self.clients.pop(idx)
                return

    def stop(self):
        for client, _ in self.clients:
            self.close_conn(client)
        self.tcpsock.close()
        logging.info('Server stopped')

    def handle_request(self, data):
        # Mock implementation for handling request
        return (b'HTTP/1.1 200 OK\r\n\r\n<h1>Request Parsed</h1>', 'close', 0, 0)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s')
    server = TCPServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
