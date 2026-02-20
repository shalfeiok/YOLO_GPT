"""Window and screen capture (SOLID: Single Responsibility).

- Screen/window: GDI + mss (Windows). IWindowCapture.
- Захват окна в фоне/под другими окнами: сначала PrintWindow (из буфера процесса), затем BitBlt,
  Redraw+PrintWindow; для свёрнутого — временно Restore → PrintWindow → Minimize. Fallback — регион экрана.
  Варианты и быстродействие: см. docs/CAPTURE_BACKGROUND_WINDOWS.md.
- Camera/video: OpenCV VideoCapture. Единый интерфейс read() → (ret, frame) для конвейера захват → очередь → инференс → превью.
"""
import ctypes
from typing import Any, Optional, Union

import numpy as np

from app.interfaces import IWindowCapture

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]

# PrintWindow: full content (UWP/DirectX)
PW_RENDERFULLCONTENT = 0x2
RDW_INVALIDATE = 0x0001
RDW_UPDATENOW = 0x0100
RDW_ERASENOW = 0x0200
# ShowWindow
SW_RESTORE = 9
SW_MINIMIZE = 6

# Только захват из буфера процесса (GDI) — без экрана, наложение других окон не мешает. Окно может быть неактивным/свёрнутым.
_PRINT_PW = "print_pw"
_PRINT_0 = "print_0"
_BITBLT = "bitblt"
_REDRAW_PRINT = "redraw_print"
_RESTORE_PRINT = "restore_print"  # для свёрнутого окна: временно восстановить → PrintWindow → свернуть
_WINDOW_METHOD_ORDER = (_PRINT_PW, _PRINT_0, _BITBLT, _REDRAW_PRINT)


class WindowCaptureService(IWindowCapture):
    """Captures window or primary monitor on Windows. GDI-first for stability."""

    def __init__(self) -> None:
        self._win32: Optional[object] = None
        self._mss: Any = None
        self._mss_failed: bool = False  # skip mss after first failure (avoid repeated hang)
        self._window_method_cache: dict[int, str] = {}
        self._init_win32()

    def _init_win32(self) -> None:
        try:
            import win32gui
            import win32ui
            import win32con
            import win32api
            self._win32 = type("Win32", (), {"gui": win32gui, "ui": win32ui, "con": win32con, "api": win32api})()
            # Чтобы GetWindowRect и экран (mss/GDI) были в одних координатах при масштабировании DPI
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                import logging
                logging.getLogger(__name__).debug('Capture backend operation failed', exc_info=True)
        except ImportError:
            self._win32 = None

    def _ensure_mss(self) -> bool:
        """Lazy-init mss (never in __init__ to avoid hang on startup). Returns True if usable."""
        if self._mss_failed or self._mss is not None:
            return self._mss is not None
        try:
            import mss
            self._mss = mss.mss()
            return True
        except Exception:
            self._mss_failed = True
            return False

    def list_windows(self) -> list[tuple[int, str]]:
        if self._win32 is None:
            return []
        out: list[tuple[int, str]] = []
        wg = self._win32.gui

        def enum_cb(hwnd: int, _: object) -> bool:
            if wg.IsWindowVisible(hwnd):
                title = wg.GetWindowText(hwnd)
                if title and title.strip():
                    out.append((hwnd, title.strip()))
            return True

        wg.EnumWindows(enum_cb, None)
        return out

    def _is_image_empty(self, arr: Optional[np.ndarray], threshold: float = 3.0) -> bool:
        if arr is None or arr.size == 0:
            return True
        return float(arr.mean()) < threshold

    def _capture_bitblt(self, hwnd: int, w: int, h: int) -> Optional[np.ndarray]:
        try:
            wg = self._win32.gui
            ui = self._win32.ui
            con = self._win32.con
            hwnd_dc = wg.GetWindowDC(hwnd)
            mfc_dc = ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
            save_dc.SelectObject(bitmap)
            save_dc.BitBlt((0, 0), (w, h), mfc_dc, (0, 0), con.SRCCOPY)
            bmpstr = bitmap.GetBitmapBits(True)
            wg.ReleaseDC(hwnd, hwnd_dc)
            mfc_dc.DeleteDC()
            save_dc.DeleteDC()
            ui.DeleteObject(bitmap.GetHandle())
            arr = np.frombuffer(bmpstr, dtype=np.uint8)
            arr = arr.reshape((h, w, 4))
            return arr[:, :, [2, 1, 0]].copy()
        except Exception:
            return None

    def _capture_printwindow(self, hwnd: int, w: int, h: int, flags: int = 0x2) -> Optional[np.ndarray]:
        try:
            import ctypes
            wg = self._win32.gui
            ui = self._win32.ui
            user32 = ctypes.windll.user32
            hwnd_dc = wg.GetWindowDC(hwnd)
            mfc_dc = ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
            save_dc.SelectObject(bitmap)
            result = user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), flags)
            wg.ReleaseDC(hwnd, hwnd_dc)
            mfc_dc.DeleteDC()
            save_dc.DeleteDC()
            if not result:
                ui.DeleteObject(bitmap.GetHandle())
                return None
            bmpstr = bitmap.GetBitmapBits(True)
            ui.DeleteObject(bitmap.GetHandle())
            arr = np.frombuffer(bmpstr, dtype=np.uint8)
            arr = arr.reshape((h, w, 4))
            return arr[:, :, [2, 1, 0]].copy()
        except Exception:
            return None

    def _capture_screen_region(self, left: int, top: int, width: int, height: int) -> Optional[np.ndarray]:
        """Capture screen region via mss (lazy). On failure disables mss for next calls."""
        if not self._ensure_mss() or self._mss is None:
            return None
        try:
            mon = self._mss.monitors[0]
            m_left = mon["left"]
            m_top = mon["top"]
            m_right = m_left + mon["width"]
            m_bottom = m_top + mon["height"]
            x1 = max(left, m_left)
            y1 = max(top, m_top)
            x2 = min(left + width, m_right)
            y2 = min(top + height, m_bottom)
            w = max(0, x2 - x1)
            h = max(0, y2 - y1)
            if w <= 0 or h <= 0:
                return None
            region = {"left": x1, "top": y1, "width": w, "height": h}
            shot = self._mss.grab(region)
            arr = np.array(shot)
            return arr[:, :, :3].copy()
        except Exception:
            self._mss_failed = True
            return None

    def _capture_redraw_then_printwindow(self, hwnd: int, w: int, h: int) -> Optional[np.ndarray]:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.RedrawWindow(hwnd, None, None, RDW_INVALIDATE | RDW_UPDATENOW | RDW_ERASENOW)
            frame = self._capture_printwindow(hwnd, w, h, 0)
            if frame is not None and not self._is_image_empty(frame):
                return frame
            return self._capture_printwindow(hwnd, w, h, PW_RENDERFULLCONTENT)
        except Exception:
            return None

    def _capture_restore_then_printwindow(self, hwnd: int, w: int, h: int) -> Optional[np.ndarray]:
        """Для свёрнутого окна: временно восстановить, PrintWindow (из буфера процесса), снова свернуть."""
        import ctypes
        import time
        user32 = ctypes.windll.user32
        try:
            if not user32.IsIconic(hwnd):
                return None
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.05)
            frame = self._capture_printwindow(hwnd, w, h, PW_RENDERFULLCONTENT)
            if frame is None or self._is_image_empty(frame):
                frame = self._capture_printwindow(hwnd, w, h, 0)
            user32.ShowWindow(hwnd, SW_MINIMIZE)
            return frame
        except Exception:
            try:
                user32.ShowWindow(hwnd, SW_MINIMIZE)
            except Exception:
                import logging
                logging.getLogger(__name__).debug('Capture backend operation failed', exc_info=True)
            return None

    def _capture_client_area_screen(self, hwnd: int) -> Optional[np.ndarray]:
        try:
            import ctypes
            wg = self._win32.gui
            user32 = ctypes.windll.user32

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            rect = wg.GetClientRect(hwnd)
            left, top, right, bottom = rect
            cw = right - left
            ch = bottom - top
            if cw <= 0 or ch <= 0:
                return None
            pt = POINT()
            pt.x = 0
            pt.y = 0
            user32.ClientToScreen(hwnd, ctypes.byref(pt))
            return self._capture_screen_region(pt.x, pt.y, cw, ch)
        except Exception:
            return None

    def _try_capture_by_method(
        self, hwnd: int, method: str, left: int, top: int, w: int, h: int
    ) -> Optional[np.ndarray]:
        if method == _PRINT_PW:
            return self._capture_printwindow(hwnd, w, h, PW_RENDERFULLCONTENT)
        if method == _PRINT_0:
            return self._capture_printwindow(hwnd, w, h, 0)
        if method == _BITBLT:
            return self._capture_bitblt(hwnd, w, h)
        if method == _REDRAW_PRINT:
            return self._capture_redraw_then_printwindow(hwnd, w, h)
        if method == _RESTORE_PRINT:
            return self._capture_restore_then_printwindow(hwnd, w, h)
        return None

    def _get_virtual_screen_bounds(self) -> Optional[tuple[int, int, int, int]]:
        """(left, top, width, height) виртуального экрана в пикселях. None если win32 недоступен."""
        if self._win32 is None:
            return None
        try:
            wg = self._win32.gui
            left = wg.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
            top = wg.GetSystemMetrics(77)    # SM_YVIRTUALSCREEN
            width = wg.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
            height = wg.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
            if width <= 0 or height <= 0:
                return None
            return (left, top, width, height)
        except Exception:
            return None

    def capture_window(self, hwnd: int) -> Optional[np.ndarray]:
        """Захват окна без наложения других окон: сначала PrintWindow (буфер окна), затем область экрана (mss/GDI)."""
        if self._win32 is None:
            return None
        wg = self._win32.gui
        try:
            if not wg.IsWindow(hwnd):
                return None
            left, top, right, bottom = wg.GetWindowRect(hwnd)
            w = right - left
            h = bottom - top
            if w <= 0 or h <= 0:
                try:
                    placement = wg.GetWindowPlacement(hwnd)
                    if placement and len(placement) >= 5:
                        rn = placement[4]
                        left, top, right, bottom = rn[0], rn[1], rn[2], rn[3]
                        w = right - left
                        h = bottom - top
                except Exception:
                    import logging
                    logging.getLogger(__name__).debug('Capture backend operation failed', exc_info=True)
                if w <= 0 or h <= 0:
                    return None
            # Сначала PrintWindow — содержимое окна без наложения других окон (в т.ч. неактивное)
            for method in (_PRINT_PW, _PRINT_0, _BITBLT, _REDRAW_PRINT, _RESTORE_PRINT):
                frame = self._try_capture_by_method(hwnd, method, left, top, w, h)
                if frame is not None and not self._is_image_empty(frame):
                    return frame
            # Fallback: область экрана (могут попасть другие окна)
            bounds = self._get_virtual_screen_bounds()
            if bounds:
                vs_left, vs_top, vs_w, vs_h = bounds
                x1 = max(left, vs_left)
                y1 = max(top, vs_top)
                x2 = min(left + w, vs_left + vs_w)
                y2 = min(top + h, vs_top + vs_h)
                w = max(0, x2 - x1)
                h = max(0, y2 - y1)
                left, top = x1, y1
                if w <= 0 or h <= 0:
                    return None
            frame = self._capture_screen_region(left, top, w, h)
            if frame is not None and not self._is_image_empty(frame):
                return frame
            return self._capture_rect_gdi(left, top, w, h)
        except Exception:
            return None

    def _capture_rect_gdi(self, left: int, top: int, width: int, height: int) -> Optional[np.ndarray]:
        """Захват прямоугольной области экрана через GDI (для fallback при захвате окна)."""
        if self._win32 is None or width <= 0 or height <= 0:
            return None
        try:
            wg = self._win32.gui
            ui = self._win32.ui
            con = self._win32.con
            hdc = wg.GetDC(0)
            if not hdc:
                return None
            mfc_dc = ui.CreateDCFromHandle(hdc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)
            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (left, top), con.SRCCOPY)
            wg.ReleaseDC(0, hdc)
            bmpstr = bitmap.GetBitmapBits(True)
            mfc_dc.DeleteDC()
            save_dc.DeleteDC()
            ui.DeleteObject(bitmap.GetHandle())
            arr = np.frombuffer(bmpstr, dtype=np.uint8)
            arr = arr.reshape((height, width, 4))
            return arr[:, :, [2, 1, 0]].copy()
        except Exception:
            return None

    def _capture_primary_gdi(self) -> Optional[np.ndarray]:
        """Full screen via GDI (fallback when mss hangs/crashes)."""
        if self._win32 is None:
            return None
        try:
            wg = self._win32.gui
            left = wg.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
            top = wg.GetSystemMetrics(77)   # SM_YVIRTUALSCREEN
            w = wg.GetSystemMetrics(78)    # SM_CXVIRTUALSCREEN
            h = wg.GetSystemMetrics(79)    # SM_CYVIRTUALSCREEN
            if w <= 0 or h <= 0:
                return None
            return self._capture_rect_gdi(left, top, w, h)
        except Exception:
            return None

    def capture_primary_monitor(self) -> Optional[np.ndarray]:
        """Primary monitor: try mss (lazy), then GDI fallback if mss fails/hangs."""
        if self._ensure_mss() and self._mss is not None:
            try:
                mon = self._mss.monitors[0]
                shot = self._mss.grab(mon)
                arr = np.array(shot)
                return arr[:, :, :3].copy()
            except Exception:
                self._mss_failed = True
        return self._capture_primary_gdi()


# --- OpenCV capture (камера / видеофайл), как в статье Киберфорум ---


class OpenCVFrameSource:
    """Источник кадров через OpenCV VideoCapture: камера (0) или видеофайл (путь).
    Интерфейс как у cv2.VideoCapture: read() → (ret, frame), release(), is_opened().
    """

    def __init__(self, source: Union[int, str]) -> None:
        self._cap: Any = None
        if cv2 is not None:
            self._cap = cv2.VideoCapture(source)

    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def read(self) -> tuple[bool, Optional[np.ndarray]]:
        """Следующий кадр. (True, BGR) или (False, None)."""
        if self._cap is None:
            return False, None
        ret, frame = self._cap.read()
        if not ret or frame is None:
            return False, None
        return True, frame

    def release(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                import logging
                logging.getLogger(__name__).debug('Capture backend operation failed', exc_info=True)
            self._cap = None
