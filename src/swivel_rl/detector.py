from __future__ import annotations

import ctypes
from pathlib import Path

from .win32_input import kernel32, user32

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class RocketLeagueDetector:
    def __init__(self, process_names: tuple[str, ...] | list[str]) -> None:
        self._targets = {str(name).strip().lower() for name in process_names if str(name).strip()}
        kernel32.OpenProcess.argtypes = [wintypes_DWORD(), wintypes_BOOL(), wintypes_DWORD()]
        kernel32.OpenProcess.restype = wintypes_HANDLE()
        kernel32.CloseHandle.argtypes = [wintypes_HANDLE()]
        kernel32.CloseHandle.restype = wintypes_BOOL()
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes_HANDLE(),
            wintypes_DWORD(),
            ctypes.c_wchar_p,
            ctypes.POINTER(wintypes_DWORD()),
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes_BOOL()
        user32.GetForegroundWindow.argtypes = []
        user32.GetForegroundWindow.restype = wintypes_HANDLE()
        user32.GetWindowThreadProcessId.argtypes = [wintypes_HANDLE(), ctypes.POINTER(wintypes_DWORD())]
        user32.GetWindowThreadProcessId.restype = wintypes_DWORD()

    @property
    def target_names(self) -> set[str]:
        return set(self._targets)

    def foreground_process_name(self) -> str:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        process_id = wintypes_DWORD()()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if process_id.value == 0:
            return ""
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id.value)
        if not handle:
            return ""
        try:
            size = wintypes_DWORD()(260)
            buffer = ctypes.create_unicode_buffer(size.value)
            ok = kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size))
            if not ok:
                return ""
            return Path(buffer.value).name.lower()
        finally:
            kernel32.CloseHandle(handle)

    def is_target_foreground(self) -> bool:
        name = self.foreground_process_name()
        return bool(name) and name in self._targets


def wintypes_DWORD():
    from ctypes import wintypes

    return wintypes.DWORD


def wintypes_BOOL():
    from ctypes import wintypes

    return wintypes.BOOL


def wintypes_HANDLE():
    from ctypes import wintypes

    return wintypes.HANDLE
