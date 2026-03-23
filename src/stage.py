from enum import Enum


class Stage(str, Enum):
    connection = "connection"
    x25519 = "x25519"
    aes = "aes"
    online = "online"
