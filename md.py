from components import Component, Text, Row, Bold, Italic, Underline, Colored


def parse(text: str) -> Component:
    parts = _parse(text)
    if not parts:
        return Text("")
    if len(parts) == 1:
        return parts[0]
    return Row(*parts)


def _parse(text: str) -> list[Component]:
    parts: list[Component] = []
    buf = ""
    i = 0

    while i < len(text):

        # Bold: **...**
        if text[i:i+2] == "**":
            if buf:
                parts.append(Text(buf))
                buf = ""
            end = text.find("**", i + 2)
            if end == -1:
                buf += "**"
                i += 2
            else:
                parts.append(Bold(*_parse(text[i+2:end])))
                i = end + 2

        # Underline: __...__
        elif text[i:i+2] == "__":
            if buf:
                parts.append(Text(buf))
                buf = ""
            end = text.find("__", i + 2)
            if end == -1:
                buf += "__"
                i += 2
            else:
                parts.append(Underline(*_parse(text[i+2:end])))
                i = end + 2

        # Italic: *...* (не **...**)
        elif text[i] == "*":
            if buf:
                parts.append(Text(buf))
                buf = ""
            j = i + 1
            end = -1
            while j < len(text):
                if text[j] == "*" and text[j:j+2] != "**":
                    end = j
                    break
                j += 1
            if end == -1:
                buf += "*"
                i += 1
            else:
                parts.append(Italic(*_parse(text[i+1:end])))
                i = end + 1

        # Colored: [text](color)
        elif text[i] == "[":
            close_bracket = text.find("](", i + 1)
            if close_bracket == -1:
                buf += "["
                i += 1
            else:
                close_paren = text.find(")", close_bracket + 2)
                if close_paren == -1:
                    buf += "["
                    i += 1
                else:
                    if buf:
                        parts.append(Text(buf))
                        buf = ""
                    color = text[close_bracket + 2:close_paren]
                    parts.append(Colored(color, *_parse(text[i+1:close_bracket])))
                    i = close_paren + 1

        else:
            buf += text[i]
            i += 1

    if buf:
        parts.append(Text(buf))

    return parts
