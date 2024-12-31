import socket
import selectors
import asyncio
from contextlib import asynccontextmanager
from logger import logger

"""
Building non-blocking, asynchronous TCP server that handles multiple client connections simultaneously, 
with a focus on understanding selectors and how Linux's epoll system improves performance.

1) Non-blocking I/O:
    -> Non-blocking sockets allow the application to continue doing useful work (or serve other clients) while waiting for data or connections.
    -> Set the Socket's File Descriptor blocking flag to False to make it non-blocking.'

2) How Selectors (Application Level) / Epoll (Kernel Level) Work:
    -> Register a socket (file descriptor) with the selector and specify which events you’re interested in (e.g., EVENT_READ for incoming data, EVENT_WRITE for sending).
    -> Use the select() method in a loop to check which sockets are ready for the specified events.
    for the server listening socket, we listen for EVENT_READ to accept new connections. For client sockets, we also monitor EVENT_READ to check if there's incoming data to be processed.

3) Asyncio Non Blocking Operations:
    -> asyncio.get_event_loop().sock_recv(sock, 1024) instead of sock.recv(1024)
    -> asyncio.get_event_loop().sock_sendall(sock, data) instead of sock.sendall(data)
"""

#selectors.DefaultSelector(), automatically chooses the best available selector for your platform.
#On Linux, DefaultSelector typically uses EpollSelector.
#On Windows, it falls back to SelectSelector.
#On macOS/BSD, it uses KqueueSelector.

selector = selectors.DefaultSelector()
HOST, PORT = ("127.0.0.1", 8000)


@asynccontextmanager
async def server_socket(host, port):
    """
    Set up async server listening socket factory.
    :param host:
    :param port:
    :return:
    """
    listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listening_socket.bind((host, port))

    # Set Socket FD as Non Blocking
    listening_socket.setblocking(False)

    # Register Epoll (linux) on the FD to notify on events
    # For Server Socket it would be EVENT_READ
    selector.register(listening_socket, selectors.EVENT_READ, data="client_connected")

    try:
        yield listening_socket
    finally:
        selector.unregister(listening_socket)
        listening_socket.close()


async def accept_client(listening_socket):
    """
    Set up async client connection socket factory.
    Every new client connection would be accepted here and assigned a new connection socket.
    :param listening_socket:
    :return:
    """
    # use asyncio's non blocking version of sock_accept()
    client_connection_socket, addr = await asyncio.get_event_loop().sock_accept(
        listening_socket
    )

    # Set client_connection_socket as NonBlocking
    client_connection_socket.setblocking(False)

    # Register Epoll (linux) on the FD to notify on events
    # For Server Socket it would be EVENT_READ
    selector.register(
        client_connection_socket, selectors.EVENT_READ, data="data_received"
    )

    return client_connection_socket, addr


async def process_client_io(client_connection_socket: socket.socket):
    """
    This method reads the data that has been received in the client connection socket's read buffer.
    Call this method when `data_received` event is triggered by the selector.
    :param client_connection_socket:
    :return:
    """
    # replace sock.recv() which is blocking
    buffer_data = await asyncio.get_event_loop().sock_recv(
        client_connection_socket, 1024
    )
    if buffer_data:
        logger.info(
            f"Client={client_connection_socket.getpeername()} | Received: {buffer_data.decode()}"
        )
        echo_payload = f"Client={client_connection_socket.getpeername()}| Echo: {buffer_data.decode()}"
        # replace sock.sendall() which is blocking
        await asyncio.get_event_loop().sock_sendall(
            client_connection_socket, data=echo_payload.encode()
        )
    else:
        logger.info(f"Closing connection to {client_connection_socket.getpeername()}")
        selector.unregister(client_connection_socket)
        client_connection_socket.close()


async def main():
    async with server_socket(HOST, PORT) as listening_socket:
        logger.info(f"Server listening on {HOST}:{PORT}")
        listening_socket.listen()
        while True:
            # Wait for I/O events from the selector
            events = selector.select(timeout=0.1)
            for key, _ in events:
                match key.data:
                    case "client_connected":
                        # Listening socket received a new client connection event
                        client_connection_socket, addr = await accept_client(
                            listening_socket
                        )
                        if client_connection_socket:
                            client_connection_socket_peer_name = (
                                client_connection_socket.getpeername()
                            )
                            logger.info(
                                f"Received connection from {client_connection_socket_peer_name}"
                            )
                            logger.info(
                                f"Connected to client {client_connection_socket_peer_name}"
                            )
                    case "data_received":
                        # The client connection socket has received data
                        client_connection_socket = key.fileobj
                        await process_client_io(client_connection_socket)

                    case _:
                        logger.error(f"Unknown event: {key.data}")


if __name__ == "__main__":
    asyncio.run(main())
