import sqlite3
import select
import socket
import sys
import signal
import argparse
import ssl

from utils import *

SERVER_HOST = 'localhost'

conn = sqlite3.connect('chat_users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
''')
conn.commit()


class ChatServer(object):
    """ An example chat server using select """
    def __init__(self, port, backlog=5):
        self.clients = 0
        self.clientmap = {}
        self.outputs = []

        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.load_cert_chain(certfile="cert.pem", keyfile="cert.pem")
        self.context.load_verify_locations('cert.pem')
        self.context.set_ciphers('AES128-SHA')

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((SERVER_HOST, port))
        self.server.listen(backlog)                
        self.server = self.context.wrap_socket(self.server, server_side=True)

        signal.signal(signal.SIGINT, self.sighandler)
        print(f'Server listening to port: {port} ...')


    def sighandler(self, signum, frame):
        """ Clean up client outputs"""
        print('Shutting down server...')
        
        for output in self.outputs:
            output.close()
        self.server.close()
        conn.close()


    def get_client_name(self, client):
        """ Return the name of the client """
        info = self.clientmap[client]
        host, name = info[0][0], info[1]
        return '@'.join((name, host))


    def run(self):
        inputs = [self.server]
        self.outputs = []
        running = True
        while running:
            try:
                readable, writeable, exceptional = select.select(
                    inputs, self.outputs, [])
            except select.error as e:
                break

            for sock in readable:
                sys.stdout.flush()
                if sock == self.server:
                    # handle the server socket
                    client, address = self.server.accept()

                    print(
                        f'Chat server: got connection {client.fileno()} from {address}')
                    
                    data = receive(client)
                    action, credentials = data.split(": ", 1)
                    username, password = credentials.split()
                    
                    if action == "REGISTER":
                        if self.register_user(username, password):
                            send(client, "SUCCESS")
                        else:
                            send(client, "Failed: User already exists")
                            client.close()
                            continue

                    elif action == "LOGIN":
                        if self.authenticate_user(username, password):
                            send(client, "SUCCESS")
                        else:
                            send(client, "Failed: Invalid credentials")
                            client.close()
                            continue

                    # Client successfully authenticated or registered
                    self.clients += 1
                    inputs.append(client)
                    self.clientmap[client] = (address, username)

                    # Send joining information to other clients
                    msg = f'\n(Connected: New client ({self.clients}) from {self.get_client_name(client)})'
                    for output in self.outputs:
                        send(output, msg)
                    self.outputs.append(client)

                else:
                    try:
                        data = receive(sock)
                        if data:
                            # Send as new client's message...
                            # msg = f'\n{self.get_client_name(sock)}: {data}'
                            msg = f'\n{self.clientmap[sock][1]}: {data}'
                            
                            # Send data to all except ourself
                            for output in self.outputs:
                                if output != sock:
                                    send(output, msg)
                        else:
                            print(f'Chat server: {sock.fileno()} hung up')
                            self.clients -= 1
                            sock.close()
                            inputs.remove(sock)
                            self.outputs.remove(sock)

                            # Sending client leaving information to others
                            msg = f'\n(Now hung up: Client from {self.get_client_name(sock)})'

                            for output in self.outputs:
                                send(output, msg)
                    except socket.error as e:
                        inputs.remove(sock)
                        self.outputs.remove(sock)

        self.server.close()
        conn.close()

    def register_user(self, username, password):
        """ Register a user by username and password """
        try:
            cursor.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, password)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def authenticate_user(self, username, password):
        """ Authenticate a user by username and password """
        cursor.execute(
            'SELECT * FROM users WHERE username = ? AND password = ?',
            (username, password)
        )
        user = cursor.fetchone()
        return user is not None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Socket Server Example')
    parser.add_argument('--port', action="store",
                        dest="port", type=int, required=True)
    given_args = parser.parse_args()
    port = given_args.port

    server = ChatServer(port)
    server.run()
