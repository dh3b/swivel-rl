from __future__ import annotations

import ctypes
import sys
import threading
import traceback
import uuid
from ctypes import wintypes
from typing import Callable

from .keys import parse_key

if sys.platform != "win32":
    raise RuntimeError("swivel_rl.win32_input is only available on Windows")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

ULONG_PTR = ctypes.c_size_t
LRESULT = ctypes.c_ssize_t
LPVOID = ctypes.c_void_p
HRAWINPUT = wintypes.HANDLE
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

WM_INPUT = 0x00FF
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_QUIT = 0x0012
HWND_MESSAGE = -3
WS_POPUP = 0x80000000

RID_INPUT = 0x10000003
RID_HEADER = 0x10000005
RIDI_DEVICENAME = 0x20000007

RIM_TYPEMOUSE = 0
RIDEV_REMOVE = 0x00000001
RIDEV_INPUTSINK = 0x00000100

MOUSE_MOVE_RELATIVE = 0x00
MOUSE_MOVE_ABSOLUTE = 0x01

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

MOUSEEVENTF_MOVE = 0x0001
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MAPVK_VK_TO_VSC = 0

EXTENDED_VIRTUAL_KEYS = {
    0x21,
    0x22,
    0x23,
    0x24,
    0x25,
    0x26,
    0x27,
    0x28,
    0x2D,
    0x2E,
}


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
        ("lPrivate", wintypes.DWORD),
    ]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", ctypes.c_ushort),
        ("usUsage", ctypes.c_ushort),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class RAWMOUSE_BUTTON_PARTS(ctypes.Structure):
    _fields_ = [
        ("usButtonFlags", ctypes.c_ushort),
        ("usButtonData", ctypes.c_ushort),
    ]


class RAWMOUSE_BUTTONS(ctypes.Union):
    _fields_ = [
        ("ulButtons", wintypes.ULONG),
        ("parts", RAWMOUSE_BUTTON_PARTS),
    ]


class RAWMOUSE(ctypes.Structure):
    _fields_ = [
        ("usFlags", ctypes.c_ushort),
        ("buttons", RAWMOUSE_BUTTONS),
        ("ulRawButtons", wintypes.ULONG),
        ("lLastX", wintypes.LONG),
        ("lLastY", wintypes.LONG),
        ("ulExtraInformation", wintypes.ULONG),
    ]


class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [
        ("MakeCode", ctypes.c_ushort),
        ("Flags", ctypes.c_ushort),
        ("Reserved", ctypes.c_ushort),
        ("VKey", ctypes.c_ushort),
        ("Message", wintypes.UINT),
        ("ExtraInformation", wintypes.ULONG),
    ]


class RAWHID(ctypes.Structure):
    _fields_ = [
        ("dwSizeHid", wintypes.DWORD),
        ("dwCount", wintypes.DWORD),
        ("bRawData", ctypes.c_ubyte * 1),
    ]


class RAWINPUT_DATA(ctypes.Union):
    _fields_ = [
        ("mouse", RAWMOUSE),
        ("keyboard", RAWKEYBOARD),
        ("hid", RAWHID),
    ]


class RAWINPUT(ctypes.Structure):
    _fields_ = [
        ("header", RAWINPUTHEADER),
        ("data", RAWINPUT_DATA),
    ]


class RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [
        ("hDevice", wintypes.HANDLE),
        ("dwType", wintypes.DWORD),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_DATA(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("data", INPUT_DATA),
    ]


user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wintypes.ATOM
user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
user32.UnregisterClassW.restype = wintypes.BOOL
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None
user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.RegisterRawInputDevices.argtypes = [ctypes.POINTER(RAWINPUTDEVICE), wintypes.UINT, wintypes.UINT]
user32.RegisterRawInputDevices.restype = wintypes.BOOL
user32.GetRawInputDeviceList.argtypes = [ctypes.POINTER(RAWINPUTDEVICELIST), ctypes.POINTER(wintypes.UINT), wintypes.UINT]
user32.GetRawInputDeviceList.restype = wintypes.UINT
user32.GetRawInputDeviceInfoW.argtypes = [wintypes.HANDLE, wintypes.UINT, LPVOID, ctypes.POINTER(wintypes.UINT)]
user32.GetRawInputDeviceInfoW.restype = wintypes.UINT
user32.GetRawInputData.argtypes = [HRAWINPUT, wintypes.UINT, LPVOID, ctypes.POINTER(wintypes.UINT), wintypes.UINT]
user32.GetRawInputData.restype = wintypes.UINT
user32.GetRawInputBuffer.argtypes = [LPVOID, ctypes.POINTER(wintypes.UINT), wintypes.UINT]
user32.GetRawInputBuffer.restype = wintypes.UINT
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
user32.MapVirtualKeyW.restype = wintypes.UINT

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE


def _handle_value(handle: object) -> int:
    value = getattr(handle, "value", handle)
    return int(value or 0)


def list_mouse_devices() -> list[dict[str, object]]:
    count = wintypes.UINT(0)
    if user32.GetRawInputDeviceList(None, ctypes.byref(count), ctypes.sizeof(RAWINPUTDEVICELIST)) == 0xFFFFFFFF:
        raise ctypes.WinError(ctypes.get_last_error())
    if count.value == 0:
        return []
    devices = (RAWINPUTDEVICELIST * count.value)()
    result = user32.GetRawInputDeviceList(devices, ctypes.byref(count), ctypes.sizeof(RAWINPUTDEVICELIST))
    if result == 0xFFFFFFFF:
        raise ctypes.WinError(ctypes.get_last_error())

    found = []
    for device in devices[:result]:
        if device.dwType != RIM_TYPEMOUSE:
            continue
        size = wintypes.UINT(0)
        if user32.GetRawInputDeviceInfoW(device.hDevice, RIDI_DEVICENAME, None, ctypes.byref(size)) == 0xFFFFFFFF:
            continue
        if size.value == 0:
            continue
        path_buffer = (wintypes.WCHAR * size.value)()
        written = user32.GetRawInputDeviceInfoW(
            device.hDevice,
            RIDI_DEVICENAME,
            ctypes.cast(path_buffer, LPVOID),
            ctypes.byref(size),
        )
        if written == 0xFFFFFFFF:
            continue
        found.append({"handle": device.hDevice, "path": path_buffer.value})
    return found


def select_mouse_devices(path_contains: str = "") -> list[tuple[wintypes.HANDLE, str]]:
    devices = list_mouse_devices()
    needle = path_contains.strip().lower()
    if needle:
        matches = [
            (device["handle"], str(device["path"]))
            for device in devices
            if needle in str(device["path"]).lower()
        ]
        if not matches:
            raise RuntimeError(f"No Raw Input mouse device matches {path_contains!r}")
        return matches
    if not devices:
        raise RuntimeError("No Raw Input mouse devices were found")
    return [(device["handle"], str(device["path"])) for device in devices]


def select_mouse_device(path_contains: str = "") -> tuple[wintypes.HANDLE, str]:
    return select_mouse_devices(path_contains)[0]


def _read_raw_input(rawhandle: wintypes.HANDLE) -> RAWINPUT | None:
    header = RAWINPUTHEADER()
    header_size = wintypes.UINT(ctypes.sizeof(RAWINPUTHEADER))
    result = user32.GetRawInputData(
        rawhandle,
        RID_HEADER,
        ctypes.byref(header),
        ctypes.byref(header_size),
        ctypes.sizeof(RAWINPUTHEADER),
    )
    if result == 0xFFFFFFFF or result == 0:
        return None

    data_size = wintypes.UINT(0)
    result = user32.GetRawInputData(
        rawhandle,
        RID_INPUT,
        None,
        ctypes.byref(data_size),
        ctypes.sizeof(RAWINPUTHEADER),
    )
    if result == 0xFFFFFFFF or data_size.value == 0:
        return None
    buffer = (ctypes.c_ubyte * data_size.value)()
    result = user32.GetRawInputData(
        rawhandle,
        RID_INPUT,
        ctypes.cast(buffer, LPVOID),
        ctypes.byref(data_size),
        ctypes.sizeof(RAWINPUTHEADER),
    )
    if result == 0xFFFFFFFF or result == 0:
        return None
    return ctypes.cast(buffer, ctypes.POINTER(RAWINPUT)).contents


class RawInputMouseSource:
    def __init__(
        self,
        on_mouse_delta: Callable[[int, int], None],
        device_path_contains: str = "",
        on_event: Callable[[str], None] | None = None,
    ) -> None:
        self._on_mouse_delta = on_mouse_delta
        self._device_path_contains = device_path_contains
        self._on_event = on_event or (lambda message: None)
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._message_log_count = 0
        self._hwnd: wintypes.HWND | None = None
        self._hinstance: wintypes.HINSTANCE | None = None
        self._class_name = ""
        self._wndproc_ref: object = None
        self._selected_handles: set[int] | None = None
        self._registered = False
        self.error: str | None = None
        self.device_path = ""

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._cleanup_window()
        self.error = None
        self.device_path = ""
        self._ready = threading.Event()
        self._message_log_count = 0
        self._thread = threading.Thread(target=self._thread_main, name="swivel-rl-rawinput", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=5.0):
            raise RuntimeError("Raw Input initialization timed out")
        if self.error:
            raise RuntimeError(self.error)

    def stop(self) -> None:
        if self._thread and self._thread.is_alive() and self._thread.ident is not None:
            if self._hwnd:
                user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
            user32.PostThreadMessageW(self._thread.ident, WM_QUIT, 0, 0)
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                user32.PostThreadMessageW(self._thread.ident, WM_QUIT, 0, 0)
                self._thread.join(timeout=1.0)
        self._unregister()
        self._cleanup_window()

    def _thread_main(self) -> None:
        try:
            self._initialize()
            self._on_event(f"rawinput thread started id={threading.get_ident()}")
        except BaseException as exc:
            self.error = f"Raw Input initialization failed: {exc}"
            self._ready.set()
            return
        self._ready.set()
        try:
            self._message_loop()
        finally:
            self._unregister()
            self._cleanup_window()

    def _initialize(self) -> None:
        self._class_name = f"SwivelRLRawInput_{uuid.uuid4().hex}"
        self._hinstance = kernel32.GetModuleHandleW(None)
        self._wndproc_ref = WNDPROC(self._wndproc)
        window_class = WNDCLASSEXW()
        window_class.cbSize = ctypes.sizeof(WNDCLASSEXW)
        window_class.lpfnWndProc = self._wndproc_ref
        window_class.hInstance = self._hinstance
        window_class.lpszClassName = self._class_name
        if not user32.RegisterClassExW(ctypes.byref(window_class)):
            raise ctypes.WinError(ctypes.get_last_error())

        self._hwnd = user32.CreateWindowExW(
            0,
            self._class_name,
            None,
            WS_POPUP,
            0,
            0,
            0,
            0,
            None,
            None,
            self._hinstance,
            None,
        )
        if not self._hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

        selected = select_mouse_devices(self._device_path_contains)
        self._selected_handles = {_handle_value(handle) for handle, _ in selected}
        self.device_path = " | ".join(path for _, path in selected)
        registration = RAWINPUTDEVICE()
        registration.usUsagePage = 0x01
        registration.usUsage = 0x02
        registration.dwFlags = RIDEV_INPUTSINK
        registration.hwndTarget = self._hwnd
        if not user32.RegisterRawInputDevices(
            ctypes.byref(registration),
            1,
            ctypes.sizeof(RAWINPUTDEVICE),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        self._registered = True
        self._on_event(
            f"rawinput registered devices={len(selected)} flags=INPUTSINK hwnd={_handle_value(self._hwnd)} paths={self.device_path}"
        )

    def _unregister(self) -> None:
        if not self._registered:
            return
        removal = RAWINPUTDEVICE()
        removal.usUsagePage = 0x01
        removal.usUsage = 0x02
        removal.dwFlags = RIDEV_REMOVE
        removal.hwndTarget = None
        user32.RegisterRawInputDevices(
            ctypes.byref(removal),
            1,
            ctypes.sizeof(RAWINPUTDEVICE),
        )
        self._registered = False

    def _cleanup_window(self) -> None:
        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
            self._hwnd = None
        if self._class_name and self._hinstance:
            user32.UnregisterClassW(self._class_name, self._hinstance)
            self._class_name = ""
        self._wndproc_ref = None

    def _message_loop(self) -> None:
        message = MSG()
        while True:
            result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result == -1:
                self.error = f"GetMessageW failed: {ctypes.WinError(ctypes.get_last_error())}"
                return
            if result == 0:
                return
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))

    def _wndproc(
        self,
        hwnd: wintypes.HWND,
        message: wintypes.UINT,
        wparam: wintypes.WPARAM,
        lparam: wintypes.LPARAM,
    ) -> LRESULT:
        try:
            if self._message_log_count < 20:
                self._on_event(f"window message=0x{message:04x} hwnd={_handle_value(hwnd)}")
                self._message_log_count += 1
            if message == WM_INPUT:
                self._on_event(f"wm_input lparam={_handle_value(lparam)}")
                raw = _read_raw_input(wintypes.HANDLE(lparam))
                if raw is not None:
                    self._process_raw(raw)
                self._drain_raw_buffer()
                return 0
            if message == WM_CLOSE:
                user32.DestroyWindow(hwnd)
                return 0
            if message == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, message, wparam, lparam)
        except Exception:
            self.error = traceback.format_exc()
            user32.PostQuitMessage(0)
            return 0

    def _process_raw(self, raw: RAWINPUT) -> None:
        device = _handle_value(raw.header.hDevice)
        if raw.header.dwType != RIM_TYPEMOUSE:
            self._on_event(f"raw ignored type={raw.header.dwType} device={device}")
            return
        mouse = raw.data.mouse
        self._on_event(
            f"raw device={device} dx={mouse.lLastX} dy={mouse.lLastY} flags={mouse.usFlags}"
        )
        if self._selected_handles is not None:
            if device not in self._selected_handles:
                self._on_event(f"raw ignored unselected device={device}")
                return
        if mouse.usFlags & MOUSE_MOVE_ABSOLUTE:
            self._on_event("raw ignored absolute move")
            return
        if mouse.lLastX or mouse.lLastY:
            self._on_mouse_delta(mouse.lLastX, mouse.lLastY)

    def _drain_raw_buffer(self) -> None:
        count = wintypes.UINT(0)
        size = wintypes.UINT(0)
        available = user32.GetRawInputBuffer(None, ctypes.byref(size), ctypes.sizeof(RAWINPUT))
        if available == 0 or available == 0xFFFFFFFF or size.value == 0:
            return
        buffer = (ctypes.c_ubyte * size.value)()
        received = user32.GetRawInputBuffer(
            ctypes.cast(buffer, LPVOID),
            ctypes.byref(size),
            ctypes.sizeof(RAWINPUT),
        )
        if received == 0 or received == 0xFFFFFFFF:
            return
        self._on_event(f"raw buffered={received}")
        base = ctypes.addressof(buffer)
        stride = ctypes.sizeof(RAWINPUT)
        for index in range(received):
            raw = ctypes.cast(ctypes.c_void_p(base + index * stride), ctypes.POINTER(RAWINPUT)).contents
            self._process_raw(raw)


class Win32KeyboardInjector:
    def send_key(self, virtual_key: int, down: bool) -> None:
        item = INPUT()
        item.type = INPUT_KEYBOARD
        scan_code = user32.MapVirtualKeyW(virtual_key, MAPVK_VK_TO_VSC)
        flags = 0
        if scan_code:
            item.data.ki.wScan = wintypes.WORD(scan_code)
            flags |= KEYEVENTF_SCANCODE
            if virtual_key in EXTENDED_VIRTUAL_KEYS:
                flags |= KEYEVENTF_EXTENDEDKEY
        else:
            item.data.ki.wVk = wintypes.WORD(virtual_key)
        if not down:
            flags |= KEYEVENTF_KEYUP
        item.data.ki.dwFlags = flags
        sent = user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(INPUT))
        if sent != 1:
            error = ctypes.get_last_error() or 1
            raise ctypes.WinError(error)


class HotkeyMonitor:
    def __init__(self, keys: tuple[str, ...] | list[str]) -> None:
        self._virtual_keys = [parse_key(key) for key in keys]
        self._active = False

    def poll(self) -> bool:
        if not self._virtual_keys:
            return False
        all_down = all(user32.GetAsyncKeyState(key) & 0x8000 for key in self._virtual_keys)
        if all_down and not self._active:
            self._active = True
            return True
        if not all_down:
            self._active = False
        return False
