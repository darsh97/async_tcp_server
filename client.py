import socket
import time
import random

HOST, PORT = ("127.0.0.1", 8000)


def create_client_socket():
    """
    Create a client socket that connects to the server.
    :return: client socket object
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    return client_socket


def send_and_receive_data(client_socket: socket.socket, data: str):
    """
    Send data to the server and receive the response.
    :param client_socket: client socket object
    :param data: data to be sent to the server
    :return: server's response
    """
    client_socket.sendall(data.encode())  # Send data to the server
    response = client_socket.recv(1024)  # Receive the response from the server
    return response.decode()  # Return the decoded response


def main():
    client_socket = create_client_socket()
    print(f"Connected to server at {HOST}:{PORT}")
    while True:
        try:
            time.sleep(1)
            data_to_send = f"{random.randint(0, 100)}"
            print(f"Sending data to server: {data_to_send}")
            response = send_and_receive_data(client_socket, data_to_send)

            # Print the server's response
            print(f"Received response from server: {response}")

        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
