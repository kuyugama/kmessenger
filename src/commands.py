from enum import Enum


class Commands(str, Enum):
    get_stage = "gs"
    ping = "p"
    send_message = "sm"
    receive_messages = "rm"
    reset_keys = "rk"
