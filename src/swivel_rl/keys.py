from __future__ import annotations

VK_MAP = {
    "BACK": 0x08,
    "TAB": 0x09,
    "CLEAR": 0x0C,
    "RETURN": 0x0D,
    "ENTER": 0x0D,
    "SHIFT": 0x10,
    "CONTROL": 0x11,
    "CTRL": 0x11,
    "ALT": 0x12,
    "PAUSE": 0x13,
    "CAPSLOCK": 0x14,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "PAGEUP": 0x21,
    "PGUP": 0x21,
    "PAGEDOWN": 0x22,
    "PGDN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
    "LWIN": 0x5B,
    "RWIN": 0x5C,
    "APPS": 0x5D,
}

for _i in range(1, 25):
    VK_MAP[f"F{_i}"] = 0x6F + _i

for _i in range(10):
    VK_MAP[f"NUMPAD{_i}"] = 0x60 + _i


def parse_key(value: object) -> int:
    if isinstance(value, int):
        return value
    token = str(value).strip().upper()
    if not token:
        raise ValueError("Key name cannot be empty")
    if token in VK_MAP:
        return VK_MAP[token]
    if len(token) == 1 and ("A" <= token <= "Z" or "0" <= token <= "9"):
        return ord(token)
    raise ValueError(f"Unsupported key name: {value}")
