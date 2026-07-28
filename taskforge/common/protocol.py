import json
import socket
import struct
from typing import Any


HEADER_SIZE = 4 #tells how long upcoming message is, message length is 32 bit so 32/8 = 4 bytes. - contain how long the actual message is


def recv_exact(sock: socket.socket, size: int) -> bytes: #this function is to ensure the whole message is recieved
    data = bytearray() #empty container to collect incoming bytes - bytearray is a datastructure which is mutable and specifically for bytes

    while len(data) < size:
        chunk = sock.recv(size - len(data))

        if not chunk: #for cases where socket closes cleanly, and so that we dont keep expecting from a closed socket
            raise ConnectionError(
                "Socket closed before the complete message was received"
            )

        data.extend(chunk)
    return bytes(data)


def send_message(sock: socket.socket, message: dict[str, Any]) -> None: #python dict to bytes to network
    """Send one length-prefixed JSON message."""

    payload = json.dumps(message).encode("utf-8") #converted into bytes

    header = struct.pack("!I", len(payload)) #puts len of payload in header

    sock.sendall(header + payload)


def receive_message(sock: socket.socket) -> dict[str, Any]: #network to bytes to python dict
    """Receive one length-prefixed JSON message."""

    header = recv_exact(sock, HEADER_SIZE) #uses recv_exact func

    message_length = struct.unpack("!I", header)[0] #unpacks how long the message is from the header

    payload = recv_exact(sock, message_length) #payload uses recv_exact func till message_length is satisfied

    return json.loads(payload.decode("utf-8")) #transform back into python dict.