from enum import Enum


class Codes(int, Enum):
    ok = 0
    name_too_long = 1
    no_receiver = 2
    no_sender = 3

    def encode(self):
        return self.to_bytes(byteorder="big")

    @classmethod
    def decode(cls, byte: bytes) -> "Codes":
        num = int.from_bytes(byte, "big")

        for value in vars(cls).values():
            if value == num:
                return value
