import itertools
import threading
import atexit
import time

from blessed import Terminal

import util

t = Terminal()


def fill_message(message: str, width: int = None, fill: str = " "):
    if width is None:
        width = t.width

    raw_parts = list(
        itertools.chain(
            *map(lambda part: t.wrap(part, width=width), message.split("\n"))
        )
    ) or [""]

    message = ""

    for part in raw_parts:
        part_len = t.length(part)
        if part_len < width:
            part += fill * (width - part_len)

        message += part

    return message


class Window:
    def __init__(self, sender: str, receiver: str, receiver_online: bool):
        self.sender = sender
        self.receiver = receiver
        self.receiver_online = receiver_online

        self.messages: list[str] = []

        self._input = ""
        self._cursor = 0

        self._alive = True
        self._last_title = ""
        self._last_messages_box = ""
        self._last_prompt = ""

        atexit.register(lambda: util.print(t.normal_cursor, end=""))

    def on_input(self, input: str):
        """
        Bind custom function to this name to handle input
        :param input: User input
        """

    def cleanup_messages(self):
        # Subtract two lines reserved for title and prompt
        max_height = t.height - 2

        total_lines = 0
        remove_before = 0
        for index, message in enumerate(self.messages[::-1]):
            message_lines = t.length(fill_message(message)) / t.width
            total_lines += message_lines

            if total_lines >= max_height:
                remove_before = -index
                break

        self.messages = self.messages[remove_before:]

    def render_title(self) -> str:
        receiver_status = (
            self.receiver
            + "["
            + (t.green("ONLINE") if self.receiver_online else t.red("OFFLINE"))
            + "]"
        )

        return t.on_gray15(
            self.sender
            + t.gold(
                t.center("KMessenger")[
                    t.length(self.sender) : t.width - t.length(receiver_status)
                ]
            )
            + receiver_status
        )

    def render_messages_box(self) -> str:
        self.cleanup_messages()

        max_height = t.height - 2

        lines = ""

        for message in self.messages:
            lines += fill_message(message)

        lines_count = t.length(lines) // t.width
        if lines_count < max_height:
            lines += " " * t.width * (max_height - lines_count)

        return t.on_gray10(lines)

    def render_prompt(self) -> str:
        prompt = t.move_xy(0, t.height) + ">>> "

        if self._input == "":
            prompt += (
                t.save + t.gray(t.on_cyan("T") + "ype something...") + t.restore
            )
            return prompt

        for i, char in enumerate(self._input):
            if i == self._cursor:
                prompt += t.yellow_on_cyan(char)
                continue

            prompt += t.yellow(char)

        if self._cursor == len(self._input):
            prompt += t.on_cyan(" ")

        return prompt

    def draw(self):
        if self._last_title == "":
            util.print(t.hide_cursor, end="")

        title = self.render_title()
        messages_box = self.render_messages_box()
        prompt = self.render_prompt()

        if self._last_title != title:
            util.print(t.move_xy(0, 0) + title)
            self._last_title = title

        if self._last_messages_box != messages_box:
            util.print(t.move_xy(0, 1) + messages_box)
            self._last_messages_box = messages_box

        if self._last_prompt != prompt:
            util.print(t.move_xy(0, t.height) + t.clear_eol + prompt, end="")
            self._last_prompt = prompt

    def infinite_draw(self):
        while threading.main_thread().is_alive() and self._alive:
            self.draw()
            time.sleep(0.01)

    def non_blocking_draw(self):
        threading.Thread(target=self.infinite_draw).start()

    def input(self):
        while True:
            with t.cbreak():
                key = t.inkey()

            if key.name is not None:
                match key.name.lower():
                    case "key_up" | "key_home":
                        self._cursor = 0

                    case "key_down" | "key_end":
                        self._cursor = len(self._input)

                    case "key_right" | "key_pgdown":
                        self._cursor = min(self._cursor + 1, len(self._input))

                    case "key_left" | "key_pgup":
                        self._cursor = max(self._cursor - 1, 0)

                    case "key_enter":
                        input = self._input
                        self.on_input(input)
                        self._input = ""
                        self._cursor = 0
                        return input

                    case "key_backspace":
                        if self._cursor == 0:
                            continue

                        self._input = (
                            self._input[: self._cursor - 1]
                            + self._input[self._cursor :]
                        )
                        self._cursor -= 1
                    case "key_delete":
                        self._input = (
                            self._input[: self._cursor]
                            + self._input[self._cursor + 1 :]
                        )
                    case "key_escape":
                        raise KeyboardInterrupt()
                continue

            self._input = (
                self._input[: self._cursor]
                + str(key)
                + self._input[self._cursor :]
            )
            self._cursor += 1

    def infinite_input(self):
        while threading.main_thread().is_alive() and self._alive:
            self.input()

    def stop(self):
        self._alive = False

    def __del__(self):
        self._alive = False
