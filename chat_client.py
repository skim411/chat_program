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

    def __init__(self, port, host=SERVER_HOST):
        self.connected = False
        self.host = host
        self.port = port

        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.set_ciphers('AES128-SHA')

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock = self.context.wrap_socket(self.sock, server_hostname=host)
            
            self.sock.connect((host, self.port))
            print(f'Now connected to chat server@ port {self.port}')
            self.connected = True
            
            action = input("Would you like to register or login? (register/login): ").strip().lower()
            if action =='register':
                print("Registration")
                self.register()
                login_choice = input("Would you like to login in now? (yes/no): ").strip().lower()
                if login_choice == 'yes':
                    self.login()
                else:
                    print("Exiting without loggin in.")
                    self.cleanup()
                    sys.exit(0)

            elif action == 'login':
                print("Login")
                self.login()
            
            else:
                print("Invalid action. Exiting.")
                self.cleanup()
                sys.exit(0)

        except socket.error as e:
            print(f'Failed to connect to chat server @ port {self.port}')
            sys.exit(1)

    def register(self):
        while True:
            self.name = input('Username: ')
            self.password = getpass('Password: ')
            send(self.sock, f'REGISTER: {self.name} {self.password}')
            response = receive(self.sock)

            if response == "SUCCESS":
                print("Registration successful.")
                break
            else:
                print("Failed: User already exists. Please try again.")


    def login(self):
        while True:
            self.name = input('Username: ')
            self.password = getpass('Password: ')
            send(self.sock, f'LOGIN: {self.name} {self.password}')
            response = receive(self.sock)

            if response == "SUCCESS":
                print("Login successful.")
                send_msg = input("Would you like to send a message? (yes/no): ")
                if send_msg == 'yes':
                    self.prompt = f'{self.name}(me): '
                    threading.Thread(target=get_and_send, args=(self,)).start()
                    return

            else:
                print("Failed: Invalid credentials.")
                # if input("Do you want to try again? (yes/no): ").lower() != "yes":
                #     self.cleanup()
                #     sys.exit(0)
                # else:
                #     continue

            self.cleanup()
            sys.exit(0)
        
        # if input("Would you like to send message? (yes/no): ").lower() != "yes":
        #     self.cleanup()
        #     sys.exit(0)

        # self.prompt = f'{self.name}(me): '
        # threading.Thread(target=get_and_send, args=(self,)).start()


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
    parser.add_argument('--port', dest="port", type=int, required=True)
    given_args = parser.parse_args()
    port = given_args.port

    client = ChatClient(port=port)
    client.run()