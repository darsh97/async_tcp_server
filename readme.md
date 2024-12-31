# Non-blocking Asynchronous TCP Server

This repository implements a non-blocking, asynchronous TCP server that can handle multiple client connections simultaneously. It focuses on understanding key concepts like selectors, epoll (Linux’s kernel-level event notification system), and asyncio for efficient, concurrent I/O operations.

## Key Concepts Covered:

1. **Non-blocking I/O**
2. **Selectors and Epoll**
3. **Asyncio Non-blocking Operations**
4. **Potential Additions (Protocol Support)**

---

### Why Non-blocking I/O?
- **Non-blocking Socket Operations**:
  - A socket can be configured to be non-blocking by setting the socket’s **blocking flag** to `False`.
  - When the socket is non-blocking, I/O operations such as `recv()` or `send()` return immediately:
    - If there is data available, the operation will return immediately with the data.
    - If no data is available, the operation will raise a special exception or return a value indicating no data is ready.

### Setting up Non-blocking Sockets:
In Python, you can make a socket non-blocking using the following code:

```python
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setblocking(False)  # Set the socket to non-blocking mode
```

###  Selectors and Epoll
- **Selectors (Application Level)**:
  - A selector is a mechanism that allows an application to monitor multiple sockets (file descriptors) for events like readability or writability. The selector keeps track of which sockets are ready for I/O, allowing the application to act accordingly without blocking.
  - Python’s selectors module provides a high-level abstraction to work with selectors. It simplifies the use of select(), poll(), or epoll() calls, which are the core of modern I/O multiplexing.

### Epoll (Kernel Level - Linux Specific):
At the kernel level, epoll is a scalable I/O notification mechanism used in Linux. It's an improvement over the traditional select() and poll() mechanisms, especially for large numbers of file descriptors. Epoll works by notifying the application only when an event occurs, reducing unnecessary overhead compared to select(), which requires polling all file descriptors.
Without Epoll, we would need to go through all the FD and check if it's state, we reduce our search space by registering only the FD's we want event to be read on.
- Key Features:
    - Efficiency: epoll only informs the application of file descriptors that have pending events, unlike select() which checks all file descriptors in every loop iteration.
    - Scalability: epoll can handle thousands of file descriptors without the performance degradation that select() suffers as the number of file descriptors increases.
    - Edge-triggered and Level-triggered modes: epoll offers both edge-triggered and level-triggered notifications. Edge-triggered mode gives the application an event only when the state changes (e.g., data is ready to be read), level-triggered provides notifications as long as the condition persists (e.g., more data to be read).

```python
import selectors
selector = selectors.DefaultSelector()
# Register server socket for EVENT_READ (waiting for incoming connections)
selector.register(listening_socket, selectors.EVENT_READ)
```
### Epoll (Kernel Level - Linux Specific) snippet in C:

```C
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/epoll.h>
#include <netinet/in.h>
#include <fcntl.h>

#define MAX_EVENTS 10
#define PORT 8080
#define BACKLOG 5

// Set the socket to non-blocking mode
int set_non_blocking(int sockfd) {
    int flags = fcntl(sockfd, F_GETFL, 0);
    if (flags == -1) {
        perror("fcntl F_GETFL");
        return -1;
    }

    flags |= O_NONBLOCK;
    if (fcntl(sockfd, F_SETFL, flags) == -1) {
        perror("fcntl F_SETFL");
        return -1;
    }

    return 0;
}

int main() {
    int server_fd, client_fd, epoll_fd, n, i;
    struct sockaddr_in server_addr, client_addr;
    socklen_t client_len = sizeof(client_addr);
    struct epoll_event ev, events[MAX_EVENTS];

    // Create server socket
    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd == -1) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    // Set server socket to non-blocking mode
    if (set_non_blocking(server_fd) == -1) {
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    // Set up server address
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(PORT);

    // Bind the socket
    if (bind(server_fd, (struct sockaddr *)&server_addr, sizeof(server_addr)) == -1) {
        perror("bind");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    // Listen on the socket
    if (listen(server_fd, BACKLOG) == -1) {
        perror("listen");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    // Create epoll instance
    epoll_fd = epoll_create1(0);
    if (epoll_fd == -1) {
        perror("epoll_create1");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    // Add the server socket to epoll
    ev.events = EPOLLIN;  // Listen for incoming connections
    ev.data.fd = server_fd;
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, server_fd, &ev) == -1) {
        perror("epoll_ctl: server_fd");
        close(epoll_fd);
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    // Main event loop
    while (1) {
        // Wait for events
        n = epoll_wait(epoll_fd, events, MAX_EVENTS, -1);
        if (n == -1) {
            perror("epoll_wait");
            close(epoll_fd);
            close(server_fd);
            exit(EXIT_FAILURE);
        }

        for (i = 0; i < n; i++) {
            if (events[i].data.fd == server_fd) {
                // New client connection
                client_fd = accept(server_fd, (struct sockaddr *)&client_addr, &client_len);
                if (client_fd == -1) {
                    perror("accept");
                    continue;
                }

                // Set the client socket to non-blocking
                if (set_non_blocking(client_fd) == -1) {
                    close(client_fd);
                    continue;
                }

                // Add the client socket to epoll
                ev.events = EPOLLIN | EPOLLET;  // Listen for incoming data
                ev.data.fd = client_fd;
                if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, client_fd, &ev) == -1) {
                    perror("epoll_ctl: client_fd");
                    close(client_fd);
                    continue;
                }
                printf("New connection from client: %d\n", client_fd);

            } else if (events[i].events & EPOLLIN) {
                // Data available to read from client
                client_fd = events[i].data.fd;
                char buffer[1024];
                ssize_t count;

                count = read(client_fd, buffer, sizeof(buffer));
                if (count == -1) {
                    perror("read");
                    close(client_fd);
                } else if (count == 0) {
                    // Client closed connection
                    printf("Client %d disconnected\n", client_fd);
                    close(client_fd);
                } else {
                    // Echo the received data back to the client
                    printf("Received data from client %d: %s\n", client_fd, buffer);
                    write(client_fd, buffer, count);
                }
            }
        }
    }

    // Clean up resources
    close(epoll_fd);
    close(server_fd);

    return 0;
}
```
