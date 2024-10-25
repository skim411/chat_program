import select
import sys
import argparse
import threading
import ssl
import socket
import warnings

from utils import *

# Default server host
SERVER_HOST = 'localhost'
stop_thread = False

# Suppress Deprecation Warnings for the SSL version
warnings.filterwarnings("ignore", category=DeprecationWarning)


def get_and_send(client):
    """ Handles sending messages from the client to the server. """
    while not stop_thread:
        data = sys.stdin.readline().strip()
        if data:
            send(client.sock, data)
            sys.stdout.write(client.prompt)
            sys.stdout.flush()


def prompt_for_credentials(prompt_text):
    """ Prompt the user for input using a given prompt text. """
    sys.stdout.write(prompt_text)
    sys.stdout.flush()
    return sys.stdin.readline().strip()


def main_menu():
    """ Displays the main menu for the client and prompts for an option. """
    print("\n1. Register a new user.\n2. Log in as an existing user.\n3. Exit the program.")
    option = prompt_for_credentials("Choose your option (1, 2 or 3): ")
    return option


def registrate():
    """ Handles user registration by prompting for a username and password. """
    print("\nRegistration:")
    username = prompt_for_credentials("Username: ")
    password = prompt_for_credentials("Password: ")
    return username, password


def login():
    """ Handles user login by prompting for a username and password. """
    print("\nLog In")
    username = prompt_for_credentials("Username: ")
    password = prompt_for_credentials("Password: ")
    return username, password


class ChatClient:
    """ A command-line chat client using SSL for secure communication and select for non-blocking IO."""

    def __init__(self, port, host=SERVER_HOST):
        # Initialize the client with the given host and port
        self.name = None
        self.connected = False
        self.host = host
        self.port = port

        # Set up an SSL context with a specific protocol and cipher
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.set_ciphers('AES128-SHA')

        try:
            # Connect to a secure socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock = self.context.wrap_socket(
                self.sock, server_hostname=host)

            self.sock.connect((host, self.port))
            self.connected = True
            print(f'Connected to chat server @ port {self.port}\n')

            # Perform authentication
            self.authenticate()
            self.prompt = f'{self.name} (me): '

            # Start a new thread to handle sending messages
            threading.Thread(target=get_and_send, args=(self,)).start()

        except socket.error:
            print(f'Failed to connect to chat server @ port {self.port}')
            sys.exit(1)

    def authenticate(self):
        """ Authenticate the user by showing the main menu and processing registration or login. """
        authenticated = False
        print("Welcome to the chat server!")

        while not authenticated:
            option = main_menu()
            if option == '1':
                # Registration option
                name, password = registrate()
                send(self.sock, f'REGISTRATION: {name} {password}')
                data = receive(self.sock)
                sys.stdout.write(f'{data}\n')
                sys.stdout.flush()

            elif option == '2':
                # Login option
                name, password = login()
                send(self.sock, f'LOGIN: {name} {password}')
                data = receive(self.sock)
                sys.stdout.write(f'\n{data}\n')
                sys.stdout.flush()
                # Check if the login was successful and set the authenticated flag
                if data == 'Log In Success':
                    authenticated = True
                    self.name = name

            elif option == '3':
                # Exit option
                print("\nExiting...")
                self.sock.close()
                sys.exit(0)

            else:
                # Invalid option
                print("Invalid option. Please enter 1, 2 or 3.")

    def cleanup(self):
        """Clean up client resources by closing the socket."""
        self.sock.close()

    def run(self):
        """ Main client loop that listens for server messages and processes them. """
        while self.connected:
            try:
                sys.stdout.write(self.prompt)
                sys.stdout.flush()

                # Check for readable sockets using select
                readable, writeable, exceptional = select.select([self.sock], [], [])
                for sock in readable:
                    if sock == self.sock:
                        data = receive(self.sock)
                        if not data:
                            print('\nClient shutting down.')
                            self.connected = False
                            break
                        else:
                            sys.stdout.write("\n" + data + "\n")
                            sys.stdout.flush()

            except KeyboardInterrupt:
                print("\nClient interrupted.")
                stop_thread = True
                self.cleanup()
                break


if __name__ == "__main__":
    # Command-line argument parsing for the server port
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', action="store", dest="port", type=int, required=True)
    given_args = parser.parse_args()
    port = given_args.port

    # Create a new chat client and run it
    chat_client = ChatClient(port=port)
    chat_client.run()
