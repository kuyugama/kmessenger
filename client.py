from threading import Lock
import threading
import time

import blessed

from src.client import Client

from window import Window, fill_message
from components import Colored, Bold, Italic, Underline, Text, serialize, deserialize
from md import parse as parse_md
import util

t = blessed.Terminal()

messages_box_height = t.height - 1

if messages_box_height < 8:
    util.print(
        t.darkred("You need taller terminal window to run this application!")
    )
    exit(1)

host = input(t.green(f"Host (\"{t.darkgreen('localhost')}\"): "))
port = util.prompt_int(
    t.yellow("Port (") + t.gold("6074") + t.yellow(")") + ": ", 6074
)

if host == "":
    host = "localhost"

user_name = util.prompt_name(t.cyan("Name") + ": " + t.yellow)

user = user_name.encode()

receiver_name = util.prompt_name(t.violet("Receiver") + ": " + t.yellow)

receiver = receiver_name.encode()

print(t.reset, end="")

client = Client(host, port, user)

y, x = t.get_location()
with t.location(x, y):
    print(t.yellow("Starting"))

client.start()

print(t.green("Started"), t.move_right)

window = Window(t.cyan(user_name), t.orange(receiver_name), False)

lock = Lock()


def messages_lookup():
    while threading.main_thread().is_alive():
        time.sleep(0.1)

        try:
            recv = client.receive_messages(receiver)

            if not window.receiver_online:
                window.receiver_online = True

            for message in recv:
                window.messages.append(
                    Colored("orange", receiver_name) + ": " + deserialize(message)
                )
        except ValueError as e:
            if e.args[0] == "No sender":
                window.receiver_online = False
                continue

    client.stop()


lookup = threading.Thread(target=messages_lookup)
lookup.start()

window.non_blocking_draw()


COMMANDS = {
    "refreshkey": "Refresh encryption keys with the server",
    "help": "Show available commands",
}


def handle_command(command: str):
    match command:
        case "refreshkey":
            try:
                client.refresh_key()
                window.messages.append(Colored("cyan", "Keys refreshed successfully"))
            except ValueError as e:
                window.messages.append(Colored("darkred", "Error") + ": " + Colored("red", str(e)))

        case "help":
            for name, description in COMMANDS.items():
                window.messages.append(
                    Colored("cyan", f"/{name}") + " — " + Colored("yellow", description)
                )

        case _:
            window.messages.append(
                Colored("darkred", "Unknown command: ")
                + Colored("red", f"/{command}")
                + Colored("darkred", ". Type /help to see available commands.")
            )


while True:
    try:
        message = window.input()
    except KeyboardInterrupt:
        window.stop()
        util.print(t.move_xy(0, t.height) + t.green(fill_message("Goodbye!")))
        time.sleep(0.5)
        exit()

    if message.startswith("/"):
        handle_command(message[1:].strip())
        continue

    try:
        parsed = parse_md(message)
        client.send_message(receiver, serialize(parsed))
        window.messages.append(Colored("green", "You") + ": " + parsed)
    except ValueError as e:
        window.messages.append(Colored("darkred", "Error") + ": " + Colored("red", e.args[0]))
        if e.args[0] == "No receiver":
            window.receiver_online = False
