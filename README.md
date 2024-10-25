# chat_program
This is a simple chat server and client application implemented in Python using SSL for secure communication and select for handling multiple clients.

## Installation
To install and run this program, ensure you have Python 3.7.4 or higher installed on your machine. Then follow these steps:
1. Clone the repository or download the files to your local machine
2. Generate SSL certificates.
    This program uses SSL for secure communicaation. You need to create a self-signed certificate for testing. You can generate one with the following command:

    ```bash
    openssl req -x509 -newkey rsa:2048 -keyout cert.pem -out cert.pem -days 365 -nodes
    ```

## Running the Program
### Starting the Chat Server
1. Open a terminal window
2. Navigate to the directory containing your script
3. Start the server by running the following command, replacing <port> with the desired port number:
    ```bash
    python3 chat_server.py --port <port>
    ```

    Example:
    ```bash
    python3 chat_server.py --port 9988
    ```

### Starting the Chat Client
1. Open another terminal window.
2. Navigate to the directory containing your script.
3. Start the client by running the following command, using the same port number as the server:
    ```bash
    python3 chat_client.py --port <port>
    ```

    Example:
    ```bash
    python3 chat_client.py --port 9988
    ```

### User Registration and Login
- Upon starting the client, you will see a menu with the following options:
    1. Register a new user.
    2. Log in as an existing user.
    3. Exit the program.

- If you choose to register, provide a username and password. If the username is available, you will be registered successfully.

- If you choose to log in, enter your username and password. You will be notified if the login is successful.