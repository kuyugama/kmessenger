from enum import Enum


class Stage(str, Enum):
    connection = "connection"
    rsa = "rsa"
    aes = "aes"
    online = "online"
