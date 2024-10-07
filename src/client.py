import threading

from src.commands import Commands
from src.codes import Codes
from src import util

import socket


class Client:
    def __init__(self, host: str, port: int, name: bytes):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.host = host
        self.port = port
        self.name = name

        self._key = None
        self._iv = None

        self.lock = threading.Lock()

    def start(self):
        self._socket.connect((self.host, self.port))

        public_key_bytes = util.wait_event(self._socket).data

        code = Codes.decode(util.wait_event(self._socket).data)

        if code != Codes.ok:
            raise ValueError(
                f"Cannot setup rsa encryption: Server respond with non-ok code: {code}"
            )

        public_key = util.public_key_from_bytes(public_key_bytes)

        self._key = key = util.symmetric_key()
        self._iv = iv = util.symmetric_iv()

        util.send_message(self._socket, util.rsa_encrypt(public_key, iv + key))

        data = util.wait_event(self._socket).data

        code = Codes.decode(data)

        if code != Codes.ok:
            raise ValueError(
                f"Cannot setup aes encryption: Server respond with non-ok code: {code} // {data}"
            )

        util.send_message(self._socket, util.aes_encrypt(key, iv, self.name))

        data = util.aes_decrypt(key, iv, util.wait_event(self._socket).data)

        code = Codes.decode(data)

        if code != Codes.ok:
            raise ValueError(
                f"Cannot set name: Server respond with non-ok code: {code} // {data}"
            )

    def send_message(self, receiver: bytes, message: bytes):
        with self.lock:
            command = util.pack_command(
                Commands.send_message, (receiver, 1), (message, 2)
            )

            util.send_message(
                self._socket, util.aes_encrypt(self._key, self._iv, command)
            )
            data = util.aes_decrypt(
                self._key, self._iv, util.wait_event(self._socket).data
            )

            code = Codes.decode(data)

            if code == Codes.no_receiver:
                raise ValueError("No receiver")

            if code != Codes.ok:
                raise ValueError(
                    f"Cannot send message: Server respond with non-ok code {code} // {data}"
                )

    def receive_messages(self, sender: bytes) -> list[bytes]:
        with self.lock:
            command = util.pack_command(
                Commands.receive_messages,
                (sender, 1),
            )
            util.send_message(
                self._socket, util.aes_encrypt(self._key, self._iv, command)
            )
            data = util.aes_decrypt(
                self._key, self._iv, util.wait_event(self._socket).data
            )

            code = Codes.decode(data)

            if code == Codes.no_sender:
                raise ValueError("No sender")

            command = util.parse_command(data)
            command, args = command["command"], command["args"]

            if command != Commands.receive_messages:
                raise ValueError(
                    f"Cannot receive messages: Server respond with wrong command: {command} // {data}"
                )

            messages_count, _ = util.parse_part(1, args)

            messages_count = int.from_bytes(messages_count, byteorder="big")

            messages = []

            for i in range(messages_count):
                messages.append(
                    util.aes_decrypt(
                        self._key, self._iv, util.wait_event(self._socket).data
                    )
                )

            data = util.aes_decrypt(
                self._key, self._iv, util.wait_event(self._socket).data
            )

            code = Codes.decode(data)

            if code != Codes.ok:
                raise ValueError(
                    f"Cannot receive messages: Server respond with non-ok code {code} // {data}"
                )

            return messages

    def stop(self):
        with self.lock:
            self._socket.close()
