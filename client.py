from threading import Lock
import threading
import time

import blessed

from src.client import Client

from window import Window, fill_message
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
                    t.orange(receiver_name) + ": " + t.yellow(message.decode())
                )
        except ValueError as e:
            if e.args[0] == "No sender":
                window.receiver_online = False
                continue

    client.stop()


lookup = threading.Thread(target=messages_lookup)
lookup.start()

window.non_blocking_draw()


while True:
    try:
        message = window.input()
    except KeyboardInterrupt:
        window.stop()
        util.print(t.move_xy(0, t.height) + t.green(fill_message("Goodbye!")))
        time.sleep(0.5)
        exit()
    data = message.encode()

    try:
        client.send_message(receiver, data)
        window.messages.append(t.green("You") + ": " + t.darkgreen(message))
    except ValueError as e:
        window.messages.append(t.darkred("Error") + ": " + t.red(e.args[0]))
        if e.args[0] == "No receiver":
            window.receiver_online = False
