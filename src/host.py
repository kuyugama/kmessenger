import threading
import socket
import typing


from src.commands import Commands
from src.codes import Codes
from src.stage import Stage
from src import util

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey


class ClientCredentials(typing.TypedDict):
    private_key: X25519PrivateKey | None

    symmetric_key: bytes | None
    symmetric_iv: bytes | None


class Client(typing.TypedDict):
    creds: ClientCredentials
    stage: Stage

    socket: socket.socket

    name: bytes | None

    messages: dict[bytes, list[bytes]]


class Host:
    def __init__(self, address: str, port: int):
        self._closed = False
        self._threads: list[threading.Thread] = []
        self.clients: dict[tuple[str, int], Client] = {}

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((address, port))

    def listen(self):
        self._socket.listen(4)

        while True:
            sock, address = self._socket.accept()
            self.clients[address] = Client(
                creds=ClientCredentials(
                    private_key=None,
                    symmetric_key=None,
                    symmetric_iv=None,
                ),
                stage=Stage.connection,
                socket=sock,
                name=None,
                messages={},
            )

            thread = threading.Thread(
                target=util.loop,
                args=(
                    self.handle_client,
                    (sock, address),
                ),
            )
            self._threads.append(thread)
            thread.start()

    def handle_client(self, client: socket.socket, address: tuple[str, int]):
        client_info = self.clients[address]
        creds = client_info["creds"]

        if client_info["stage"] == Stage.connection:
            # print(f"{address_format} connected")
            private = util.x25519_private_key()

            creds["private_key"] = private

            util.send_message(
                client, util.x25519_public_key_to_bytes(private.public_key())
            )

            client_info["stage"] = Stage.x25519

            util.send_message(client, Codes.ok.encode())
            return

        if client_info["stage"] == Stage.x25519:
            # print(f"{address_format} x25519 key exchanged")

            client_pub = util.x25519_public_key_from_bytes(
                util.wait_event(client).data
            )

            shared_secret = creds["private_key"].exchange(client_pub)
            key, iv = util.derive_symmetric_keys(shared_secret)

            creds["symmetric_key"] = key
            creds["symmetric_iv"] = iv
            util.send_message(client, Codes.ok.encode())

            # If user is already authorized, but requested key-flash
            if client_info["name"] is None:
                client_info["stage"] = Stage.aes
            else:
                client_info["stage"] = Stage.online

            return

        if client_info["stage"] == Stage.aes:
            # print(f"{address_format} aes key acquired")

            key, iv = creds["symmetric_key"], creds["symmetric_iv"]

            data = util.aes_decrypt(key, iv, util.wait_event(client).data)

            if len(data) > 255:
                util.send_message(
                    client,
                    util.aes_encrypt(
                        key,
                        iv,
                        Codes.name_too_long.encode(),
                    ),
                )
                return

            client_info["name"] = data
            client_info["stage"] = Stage.online

            util.send_message(
                client, util.aes_encrypt(key, iv, Codes.ok.encode())
            )

            # print(f"{address_format} registered")
            return

        event = util.read_event(client)

        if event.close_connection:
            # print(f"{address_format} disconnected")
            del self.clients[address]
            raise StopIteration

        if event.no_message:
            return

        # Client is online and ready to send and receive messages
        key, iv = creds["symmetric_key"], creds["symmetric_iv"]
        data = util.aes_decrypt(key, iv, event.data)

        command = util.parse_command(data)
        command, args = command["command"], command["args"]

        if command == Commands.ping:
            # print(f"{address_format} pong")
            util.send_message(client, Codes.ok.encode())
            return

        if command == Commands.reset_keys:
            private = util.x25519_private_key()
            creds["private_key"] = private
            util.send_message(
                client, util.x25519_public_key_to_bytes(private.public_key())
            )
            client_info["stage"] = Stage.x25519
            return

        if command == Commands.send_message:
            receiver_name, args = util.parse_part(1, args)

            # print(f"{address_format} send message to {receiver_name}")

            receiver = self.find_client(receiver_name)

            if receiver is None:
                util.send_message(
                    client,
                    util.aes_encrypt(key, iv, Codes.no_receiver.encode()),
                )
                return

            message, _ = util.parse_part(2, args)

            messages = client_info["messages"].setdefault(receiver_name, [])

            messages.append(message)

            util.send_message(
                client, util.aes_encrypt(key, iv, Codes.ok.encode())
            )

        if command == Commands.receive_messages:
            sender_name, args = util.parse_part(1, args)

            sender = self.find_client(sender_name)

            if sender is None:
                util.send_message(
                    client,
                    util.aes_encrypt(key, iv, Codes.no_sender.encode()),
                )
                return

            # print(f"{address_format} receive messages from {sender_name}")

            messages = sender["messages"].setdefault(client_info["name"], [])

            # Messages list copy is required to list only messages
            # that exists when client requested
            messages_copy = messages.copy()

            util.send_message(
                client,
                util.aes_encrypt(
                    key,
                    iv,
                    util.pack_command(
                        Commands.receive_messages,
                        (len(messages_copy).to_bytes(1, byteorder="big"), 1),
                    ),
                ),
            )

            for message in messages_copy:
                messages.pop(0)
                util.send_message(
                    client,
                    util.aes_encrypt(key, iv, message),
                )

            util.send_message(
                client,
                util.aes_encrypt(key, iv, Codes.ok.encode()),
            )
            return

    def find_client(self, name: bytes) -> Client | None:
        for client in self.clients.values():
            if client["name"] == name:
                return client

    def close(self):
        self._closed = True
        self._socket.close()
        for thread in self._threads:
            thread.join()

    def __del__(self):
        if not self._closed:
            self.close()
