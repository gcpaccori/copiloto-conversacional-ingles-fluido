import sys

def set_clickthrough(hwnd: int, enable: bool) -> None:
    """Make a window click-through on Windows (WS_EX_TRANSPARENT)."""
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    get_style = user32.GetWindowLongW
    set_style = user32.SetWindowLongW
    get_style.argtypes = [wintypes.HWND, wintypes.INT]
    get_style.restype = wintypes.LONG
    set_style.argtypes = [wintypes.HWND, wintypes.INT, wintypes.LONG]
    set_style.restype = wintypes.LONG

    style = get_style(hwnd, GWL_EXSTYLE)
    style |= WS_EX_LAYERED
    if enable:
        style |= WS_EX_TRANSPARENT
    else:
        style &= ~WS_EX_TRANSPARENT
    set_style(hwnd, GWL_EXSTYLE, style)
