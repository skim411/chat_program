import select
import json
import sys
import signal
import argparse
import ssl
import warnings
import socket

from utils import *

# File to store user data
USER_FILE = 'chat_users.json'
SERVER_HOST = 'localhost'

# Suppress SSL deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning)

def registrate(username, password):
    """ Registers a new user if the username doesn't already exist in the user file. """
    # Load user data from file
    try:
        with open(USER_FILE, 'r') as file:
            users = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        users = {}
    # Check if the username already exists
    if username in users:
        return False

    # Add the new user to the user file
    users[username] = password
    with open(USER_FILE, 'w') as file:
        json.dump(users, file)
    return True


def login(username, password, client):
    """ Handles user login by verifying the username and password. """
    # Load user data from file
    try:
        with open(USER_FILE, 'r') as file:
            users = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        send(client, 'Log In Failed: No users found')
        return False

    # Check if the username and password match
    if username not in users or users[username] != password:
        send(client, 'Log In Failed: No users found' if username not in users else 'Log In Failed: Password does not match the username')
        return False
    return True


class ChatServer:
    """ Chat server implementation using select for handling multiple clients. """

    def __init__(self, port, backlog=5):
        """ Initialize the server with the given port and backlog. """
        # Initialize client map and output map
        self.clientmap = {}
        self.outputs = {} 

        # Configure SSL context
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.load_cert_chain(certfile="cert.pem", keyfile="cert.pem")
        self.context.load_verify_locations('cert.pem')
        self.context.set_ciphers('AES128-SHA')

        # Create and configure server socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((SERVER_HOST, port))
        self.server.listen(backlog)
        self.server = self.context.wrap_socket(self.server, server_side=True)

        # Handle server shutdown
        signal.signal(signal.SIGINT, self.sig_handler)
        print(f'Server listening on {SERVER_HOST}:{port}...')

    def sig_handler(self, *args):
        """ Handles server shutdown by closing all client connections. """
        print('Shutting down server...')
        for client in self.clientmap.keys():
            client.close()
        self.server.close()

    def get_client_name(self, client):
        """ Retrieves the client name from the client map. """
        return self.clientmap[client][1]

    def run(self):
        """ Main server loop to handle incoming connections and messages. """
        inputs = [self.server]
        running = True

        while running:
            try:
                readable, writeable, exceptional = select.select(inputs, [], [])
            except select.error:
                break

            for sock in readable:
                sys.stdout.flush()
                if sock == self.server:
                    # Accept a new connection
                    client, address = self.server.accept()
                    print(f'Chat server: got connection {client.fileno()} from {address}')
                    # Add the client to the inputs list
                    self.clientmap[client] = (address, None)
                    inputs.append(client)
                    # New clients are unauthorized by default
                    self.outputs[client] = False
                else:
                    try:
                        data = receive(sock)
                        if self.outputs.get(sock):
                            # Handle authorized clients
                            if data:
                                msg = f'{self.get_client_name(sock)}: {data}'
                                for output in inputs:
                                    if output != sock and self.outputs.get(output):
                                        send(output, msg)
                            else:
                                print(f'Chat server: {sock.fileno()} hung up')
                                self.remove_client(sock, inputs)
                        else:
                            # Handle unauthorized clients
                            self.handle_unauthorised(sock, data, inputs)
                    except socket.error:
                        self.remove_client(sock, inputs)

        # Close the server socket
        self.server.close()

    def remove_client(self, sock, inputs):
        """ Removes a client socket from the server and closes its connection. """
        if sock in inputs:
            inputs.remove(sock)
        if sock in self.outputs:
            del self.outputs[sock]
        sock.close()

    def handle_unauthorised(self, sock, data, inputs):
        """ Handles login and registration requests for unauthorized sockets. """
        if not data:
            print(f'Chat client: {sock.fileno()} hung up')
            self.remove_client(sock, inputs)
            return

        # Process login and registration requests
        if data.startswith('LOGIN:'):
            self.process_login(sock, data)
        elif data.startswith('REGISTRATION:'):
            self.process_registration(sock, data)

    def process_login(self, sock, data):
        """ Processes user login requests and sends a success message if successful. """
        # Extract username and password from the data
        info = data.split('LOGIN: ', 1)[1]
        username, password = info.split(' ', 1)
        username = username.strip()
        password = password.strip()

        # Log in the user and send a success message
        if login(username, password.strip(), sock):
            send(sock, 'Log In Success')
            self.clientmap[sock] = (self.clientmap[sock][0], username)
            msg = f'[Server: {self.get_client_name(sock)} joined the chat]'
            for output in self.outputs:
                if self.outputs.get(output):
                    send(output, msg)
            # Mark client as authorized
            self.outputs[sock] = True

    def process_registration(self, sock, data):
        """ Processes user registration requests and sends a success message if successful. """
        # Extract username and password from the data
        info = data.split('REGISTRATION: ', 1)[1]
        username, password = info.split(' ', 1)
        username = username.strip()
        password = password.strip()

        # Register the user and send a success message
        if registrate(username, password.strip()):
            send(sock, 'Registration Success')
        else:
            send(sock, 'Registration Failed: Username has already been taken')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Socket Server Example with Select')
    parser.add_argument('--port', required=True, type=int, help='Port to listen on')

    args = parser.parse_args()
    server = ChatServer(args.port)
    server.run()
