import select
import socket
import sys
import signal
import argparse
import threading
import ssl
from getpass import getpass

from utils import *

SERVER_HOST = 'localhost'
stop_thread = False

def get_and_send(client):
    while not stop_thread:
        data = sys.stdin.readline().strip()
        if data:
            send(client.sock, data)
            sys.stdout.write(client.prompt)
            sys.stdout.flush()

class ChatClient():
    """ A command line chat client using select """

    def __init__(self, port, host=SERVER_HOST, action='login'):
        self.action = action
        self.connected = False
        self.host = host
        self.port = port

        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.set_ciphers('AES128-SHA')

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock = self.context.wrap_socket(
                self.sock, server_hostname=host)
            
            self.sock.connect((host, self.port))
            print(f'Now connected to chat server@ port {self.port}')
            self.connected = True

            if self.action == 'register':
                print("Registration")
            elif self.action == 'login':
                print("Login")

            self.name = input('Username: ')
            self.password = getpass('Password: ')

            if self.action == 'register':
                send(self.sock, f'REGISTER: {self.name} {self.password}')
            elif self.action == 'login':
                send(self.sock, f'LOGIN: {self.name} {self.password}')

            response = receive(self.sock)
            if response == "SUCCESS":
                print(f"{self.action.capitalize()} successful.")

                if input("Would you like to send message? (yes/no): ").lower() != "yes":
                    self.cleanup()
                    sys.exit(0)

                data = receive(self.sock)
                addr = data.split('CLIENT: ')[1]
                self.prompt = '[' + '@'.join((self.name, addr)) + ']> '

                threading.Thread(target=get_and_send, args=(self,)).start()

        except socket.error as e:
            print(f'Failed to connect to chat server @ port {self.port}')
            sys.exit(1)


    def cleanup(self):
        """ Close the connection """
        self.sock.close()

    def run(self):
        """ Chat client main loop """
        while self.connected:
            try:
                sys.stdout.write(self.prompt)
                sys.stdout.flush()

                # Wait for input from stdin & socket
                readable, writeable, exceptional = select.select(
                    [self.sock], [], [])
                
                for sock in readable:
                    if sock == self.sock:
                        data = receive(self.sock)
                        if not data:
                            print('Shutting down.')
                            self.connected = False
                            break
                        else:
                            sys.stdout.write(data + '\n')
                            sys.stdout.flush()

            except KeyboardInterrupt:
                print('Interrupted.')
                self.connected = False
                self.cleanup()
                break

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--action', action="store", dest="action", choices=['register', 'login'], required=True)
    parser.add_argument('--port', action="store", dest="port", type=int, required=True)
    given_args = parser.parse_args()
    port = given_args.port
    action = given_args.action

    client = ChatClient(port=port, action=action)
    client.run()