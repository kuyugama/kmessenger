import json
from blessed import Terminal

t = Terminal()


def _wrap(value: str | Component) -> Component:
    return Text(value) if isinstance(value, str) else value


class Component:
    def render(self) -> str:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.render()

    def __add__(self, other: Component | str) -> Row:
        return Row(self, _wrap(other))

    def __radd__(self, other: Component | str) -> Row:
        return Row(_wrap(other), self)


class Text(Component):
    def __init__(self, text: str):
        self.text = text

    def render(self) -> str:
        return self.text


class Row(Component):
    def __init__(self, *children: Component | str):
        self.children = [_wrap(c) for c in children]

    def __add__(self, other: Component | str) -> Row:
        return Row(*self.children, _wrap(other))

    def render(self) -> str:
        return "".join(c.render() for c in self.children)


class Bold(Component):
    def __init__(self, *children: Component | str):
        self.children = [_wrap(c) for c in children]

    def render(self) -> str:
        return t.bold("".join(c.render() for c in self.children))


class Italic(Component):
    def __init__(self, *children: Component | str):
        self.children = [_wrap(c) for c in children]

    def render(self) -> str:
        return t.italic("".join(c.render() for c in self.children))


class Underline(Component):
    def __init__(self, *children: Component | str):
        self.children = [_wrap(c) for c in children]

    def render(self) -> str:
        return t.underline("".join(c.render() for c in self.children))


class Colored(Component):
    def __init__(self, color: str, *children: Component | str):
        self.color = color
        self.children = [_wrap(c) for c in children]

    def render(self) -> str:
        formatter = getattr(t, self.color)
        return formatter("".join(c.render() for c in self.children))


def _collect(component: Component, segments: list[dict], bold: bool, italic: bool, underline: bool, color: str | None):
    if isinstance(component, Text):
        segments.append({
            "text": component.text,
            "bold": bold,
            "italic": italic,
            "underline": underline,
            "color": color,
        })
    elif isinstance(component, Row):
        for child in component.children:
            _collect(child, segments, bold, italic, underline, color)
    elif isinstance(component, Bold):
        for child in component.children:
            _collect(child, segments, True, italic, underline, color)
    elif isinstance(component, Italic):
        for child in component.children:
            _collect(child, segments, bold, True, underline, color)
    elif isinstance(component, Underline):
        for child in component.children:
            _collect(child, segments, bold, italic, True, color)
    elif isinstance(component, Colored):
        for child in component.children:
            _collect(child, segments, bold, italic, underline, component.color)


def serialize(component: Component | str) -> bytes:
    if isinstance(component, str):
        component = Text(component)
    segments: list[dict] = []
    _collect(component, segments, bold=False, italic=False, underline=False, color=None)
    return json.dumps(segments, ensure_ascii=False).encode()


def deserialize(data: bytes) -> Component:
    segments: list[dict] = json.loads(data.decode())
    if not segments:
        return Text("")
    children = [_segment_to_component(s) for s in segments]
    return children[0] if len(children) == 1 else Row(*children)


def _segment_to_component(segment: dict) -> Component:
    result: Component = Text(segment["text"])
    if segment.get("bold"):
        result = Bold(result)
    if segment.get("italic"):
        result = Italic(result)
    if segment.get("underline"):
        result = Underline(result)
    if segment.get("color"):
        result = Colored(segment["color"], result)
    return result
