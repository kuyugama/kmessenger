import threading
import time
from socket import socket
import contextlib
import typing
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

from cryptography.hazmat.primitives.asymmetric.rsa import (
    RSAPrivateKey,
    RSAPublicKey,
)


def asymmetric_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


def public_key_from_bytes(key: bytes) -> RSAPublicKey:
    return serialization.load_der_public_key(key)


def public_key_to_bytes(key: RSAPublicKey) -> bytes:
    return key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def rsa_encrypt(public_key: RSAPublicKey, message: bytes) -> bytes:
    return public_key.encrypt(
        message,
        padding.OAEP(
            padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def rsa_decrypt(private_key: RSAPrivateKey, message: bytes) -> bytes:
    return private_key.decrypt(
        message,
        padding.OAEP(
            padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def symmetric_key() -> bytes:
    return os.urandom(32)


def symmetric_iv() -> bytes:
    return os.urandom(16)


def aes_encrypt(key: bytes, iv: bytes, message: bytes) -> bytes:
    cipher = Cipher(
        algorithms.AES(key), modes.CFB(iv), backend=default_backend()
    )

    encryptor = cipher.encryptor()

    return encryptor.update(message) + encryptor.finalize()


def aes_decrypt(key: bytes, iv: bytes, message: bytes) -> bytes:
    cipher = Cipher(
        algorithms.AES(key), modes.CFB(iv), backend=default_backend()
    )
    decryptor = cipher.decryptor()

    return decryptor.update(message) + decryptor.finalize()


@contextlib.contextmanager
def no_blocking(sock: socket):
    is_blocking = sock.getblocking()
    if is_blocking:
        sock.setblocking(False)

    try:
        yield
    finally:
        if is_blocking:
            sock.setblocking(True)


class Event:
    def __init__(
        self,
        data: bytes | None = None,
        no_message: bool = False,
        close_connection: bool = False,
    ):
        self.data = data
        self.no_message = no_message
        self.close_connection = close_connection


def read_event(sock: socket) -> Event:
    try:
        with no_blocking(sock):
            length_bytes = sock.recv(4)

        if len(length_bytes) != 4:
            length_bytes += sock.recv(4 - len(length_bytes))

        if len(length_bytes) != 4:
            return Event(close_connection=True)

        return Event(sock.recv(int.from_bytes(length_bytes)))
    except BlockingIOError:
        return Event(no_message=True)


def wait_event(sock: socket) -> Event:
    length_bytes = sock.recv(4)
    if len(length_bytes) != 4:
        return Event(close_connection=True)

    return Event(sock.recv(int.from_bytes(length_bytes)))


def send_message(sock: socket, message: bytes) -> None:
    length = len(message)
    length_bytes = length.to_bytes(4, byteorder="big")

    sock.send(length_bytes + message)


def loop(function: typing.Callable, args: tuple):
    while threading.main_thread().is_alive():
        try:
            function(*args)
            time.sleep(0.01)
        except StopIteration:
            break


def parse_part(length_size: int, buffer: bytes) -> tuple[bytes, bytes]:
    length_bytes = buffer[:length_size]
    length = int.from_bytes(length_bytes, byteorder="big")

    return (
        buffer[length_size : length_size + length],
        buffer[length_size + length :],
    )


class Command(typing.TypedDict):
    command: str
    args: bytes


def parse_command(buffer: bytes) -> Command:
    command, buffer = parse_part(1, buffer)

    return {
        "command": command.decode(),
        "args": buffer,
    }


def pack_command(command: str, *blocks: tuple[bytes, int]):
    command = command.encode()

    body = int.to_bytes(len(command), 1, byteorder="big") + command

    for data, length_size in blocks:
        body += int.to_bytes(len(data), length_size, byteorder="big")
        body += data

    if len(body) > 0xFFFFFFFF:
        raise OverflowError("Command too long")

    return body
