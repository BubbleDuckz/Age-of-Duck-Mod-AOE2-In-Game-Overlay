"""Read-only game observation and a non-activating overlay. Never injects input."""
import ctypes as c
import os
import time
from ctypes import wintypes as w
from pathlib import Path
from PIL import ImageGrab

u = c.WinDLL('user32', use_last_error=True)
k = c.WinDLL('kernel32', use_last_error=True)
u.GetForegroundWindow.restype = w.HWND
u.GetAncestor.argtypes = [w.HWND, w.UINT]
u.GetAncestor.restype = w.HWND
u.GetWindowThreadProcessId.argtypes = [w.HWND, c.POINTER(w.DWORD)]
u.GetClientRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
u.ClientToScreen.argtypes = [w.HWND, c.POINTER(w.POINT)]
u.IsIconic.argtypes = [w.HWND]
u.GetCursorPos.argtypes = [c.POINTER(w.POINT)]
u.WindowFromPoint.argtypes = [w.POINT]
u.WindowFromPoint.restype = w.HWND
k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k.OpenProcess.restype = w.HANDLE
k.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)]
k.CloseHandle.argtypes = [w.HANDLE]
k.CreateMutexW.argtypes = [c.c_void_p,w.BOOL,w.LPCWSTR]
k.CreateMutexW.restype = w.HANDLE
u.GetWindowLongPtrW.argtypes = [w.HWND, c.c_int]
u.GetWindowLongPtrW.restype = c.c_ssize_t
u.SetWindowLongPtrW.argtypes = [w.HWND, c.c_int, c.c_ssize_t]
u.SetWindowLongPtrW.restype = c.c_ssize_t
u.SetWindowPos.argtypes = [w.HWND, w.HWND, c.c_int, c.c_int, c.c_int, c.c_int, w.UINT]
u.ShowWindow.argtypes = [w.HWND, c.c_int]


def dpi_aware():
    try:
        u.SetProcessDpiAwarenessContext(c.c_void_p(-4))
    except (AttributeError, OSError):
        u.SetProcessDPIAware()


_mutex = None

def single_instance():
    global _mutex
    _mutex=k.CreateMutexW(None,False,'Local\\AoE2TCQueueReminder-v1')
    if not _mutex:
        raise c.WinError(c.get_last_error())
    if c.get_last_error()==183:
        k.CloseHandle(_mutex)
        _mutex=None
        return False
    return True


def game_window(hwnd, allow_minimized=False):
    pid = w.DWORD()
    u.GetWindowThreadProcessId(hwnd, c.byref(pid))
    process = k.OpenProcess(0x1000, False, pid.value)
    if not process:
        return None
    try:
        path = c.create_unicode_buffer(32768)
        size = w.DWORD(len(path))
        if not k.QueryFullProcessImageNameW(process, 0, path, c.byref(size)):
            return None
        if Path(path.value).name.lower() not in ('aoe2de_s.exe', 'aoe2de.exe'):
            return None
    finally:
        k.CloseHandle(process)
    if u.IsIconic(hwnd):
        if not allow_minimized:return None
        if _last_game_context and _last_game_context[:2]==(hwnd,str(pid.value)):
            return _last_game_context
        return None
    rect = w.RECT()
    origin = w.POINT(0, 0)
    if not u.GetClientRect(hwnd, c.byref(rect)) or not u.ClientToScreen(hwnd, c.byref(origin)):
        return None
    if rect.right < 640 or rect.bottom < 480:
        return None
    return hwnd, str(pid.value), (origin.x, origin.y, origin.x + rect.right, origin.y + rect.bottom)


_last_game_hwnd = None
_last_game_context = None

def window_pid(hwnd):
    pid=w.DWORD();u.GetWindowThreadProcessId(hwnd,c.byref(pid));return pid.value

_null_companion_focus=False
_last_game_seen=0

def companion_focused():
    global _null_companion_focus, _last_game_seen
    hwnd=u.GetForegroundWindow()
    if hwnd:
        _null_companion_focus=False
        if hwnd!=_last_game_hwnd:_last_game_seen=0
        return window_pid(hwnd)==os.getpid()
    # A MA_NOACTIVATE overlay click can leave Windows with HWND(NULL).
    # Recognize only a hit on our own windows, then retain that interaction
    # until Windows reports a real foreground window again.
    point=w.POINT()
    if u.GetCursorPos(c.byref(point)):
        under=u.WindowFromPoint(point)
        if under and window_pid(under)==os.getpid():_null_companion_focus=True
    return _null_companion_focus or time.monotonic()-_last_game_seen<.35

def foreground_game():
    """Game focus includes this companion's windows, never unrelated apps."""
    global _last_game_hwnd, _last_game_context, _last_game_seen
    foreground=u.GetForegroundWindow()
    game=game_window(foreground)
    if game:
        companion_focused()
        _last_game_hwnd=game[0];_last_game_context=game;_last_game_seen=time.monotonic();return game
    if _last_game_hwnd and companion_focused():
        # Exclusive-fullscreen AoE can minimize as soon as our settings/overlay
        # gains focus. Retain its last screen geometry for UI only. Capture and
        # speech remain suspended while any companion window has focus.
        game=game_window(_last_game_hwnd,allow_minimized=True)
        if game:
            if _last_game_context and game[:2]==_last_game_context[:2]:return _last_game_context
            return game
        _last_game_hwnd=None;_last_game_context=None
    return None

_ENUM_PROC = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
u.EnumWindows.argtypes = [_ENUM_PROC, w.LPARAM]
u.IsWindowVisible.argtypes = [w.HWND]


def find_game_window():
    """The visible game window, even when it is not the foreground window."""
    found = []

    def visit(hwnd, _param):
        if u.IsWindowVisible(hwnd):
            game = game_window(hwnd)
            if game:
                found.append(game)
        return True
    u.EnumWindows(_ENUM_PROC(visit), 0)
    return found[0] if found else None


def grab_game(game):
    """Raw pixels of the game window, ignoring focus (used while setting up HUD areas)."""
    return ImageGrab.grab(bbox=game[2], all_screens=True)


def capture(game):
    # Only capture unobscured foreground gameplay. Companion focus preserves UI
    # context but freezes capture; unrelated apps suspend both panels.
    if not game or companion_focused() or foreground_game()!=game:return None
    im=ImageGrab.grab(bbox=game[2],all_screens=True)
    return im if foreground_game()==game else None


def prepare_overlay(widget):
    widget.update_idletasks()
    hwnd = u.GetAncestor(widget.winfo_id(), 2)
    # WS_EX_LAYERED | TRANSPARENT | TOOLWINDOW | NOACTIVATE.
    styles = u.GetWindowLongPtrW(hwnd, -20) | 0x80000 | 0x20 | 0x80 | 0x08000000
    u.SetWindowLongPtrW(hwnd, -20, styles)
    return hwnd


def show_overlay(hwnd, x, y, width=300, height=40):
    u.SetWindowPos(hwnd, w.HWND(-1), x, y, width, height, 0x0010)
    u.ShowWindow(hwnd, 4)  # SW_SHOWNOACTIVATE


def hide_overlay(hwnd):
    u.ShowWindow(hwnd, 0)


def overlay_flags(hwnd):
    flags = u.GetWindowLongPtrW(hwnd, -20)
    return {name: bool(flags & value) for name, value in
            [('click_through', 0x20), ('no_activate', 0x08000000), ('tool_window', 0x80), ('layered', 0x80000)]}
