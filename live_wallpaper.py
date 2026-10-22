import os
import sys
import json
import shutil
import ctypes
import datetime
import time
import winreg
from ctypes import wintypes

# Ensure thread is attached to the interactive Default desktop
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
ole32 = ctypes.windll.ole32

try:
    h_default = user32.OpenDesktopW("Default", 0, False, 0x01FF)
    if h_default:
        user32.SetThreadDesktop(h_default)
except Exception:
    pass

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QFileDialog,
    QSystemTrayIcon,
    QMenu,
    QMessageBox,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

APP_DIR = r"C:\InterLive"
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
SAVED_VIDEO_PATH = os.path.join(APP_DIR, "wallpaper.mp4")
LOG_PATH = os.path.join(APP_DIR, "engine.log")
INSTALLED_EXE = os.path.join(APP_DIR, "InterLive.exe")


def log(msg: str):
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {msg}\n")
    except Exception:
        pass


# COM Structures and GUIDs for native Windows IShellLinkW shortcut creation
class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_byte * 8),
    ]


CLSID_ShellLink = GUID(
    0x00021401,
    0x0000,
    0x0000,
    (ctypes.c_byte * 8)(0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46),
)
IID_IShellLinkW = GUID(
    0x000214F9,
    0x0000,
    0x0000,
    (ctypes.c_byte * 8)(0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46),
)
IID_IPersistFile = GUID(
    0x0000010B,
    0x0000,
    0x0000,
    (ctypes.c_byte * 8)(0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46),
)


def create_windows_shortcut(
    target: str,
    lnk_path: str,
    args: str = "",
    desc: str = "",
    icon: str = "",
) -> bool:
    try:
        ole32.CoInitialize(None)
        p_sl = ctypes.c_void_p()
        hr = ole32.CoCreateInstance(
            ctypes.byref(CLSID_ShellLink),
            None,
            1,
            ctypes.byref(IID_IShellLinkW),
            ctypes.byref(p_sl),
        )
        if hr != 0:
            return False

        vtable_sl = ctypes.cast(
            p_sl, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
        ).contents

        # SetPath (offset 20)
        SetPath = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.LPCWSTR)(
            vtable_sl[20]
        )
        SetPath(p_sl, target)

        # SetArguments (offset 11)
        if args:
            SetArguments = ctypes.WINFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p, wintypes.LPCWSTR
            )(vtable_sl[11])
            SetArguments(p_sl, args)

        # SetDescription (offset 7)
        if desc:
            SetDesc = ctypes.WINFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p, wintypes.LPCWSTR
            )(vtable_sl[7])
            SetDesc(p_sl, desc)

        # SetWorkingDirectory (offset 9)
        work_dir = os.path.dirname(target)
        if os.path.isdir(work_dir):
            SetWorkDir = ctypes.WINFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p, wintypes.LPCWSTR
            )(vtable_sl[9])
            SetWorkDir(p_sl, work_dir)

        # SetIconLocation (offset 17)
        if icon:
            SetIcon = ctypes.WINFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_int
            )(vtable_sl[17])
            SetIcon(p_sl, icon, 0)

        # QueryInterface for IPersistFile (offset 0)
        QI = ctypes.WINFUNCTYPE(
            ctypes.c_long,
            ctypes.c_void_p,
            ctypes.POINTER(GUID),
            ctypes.POINTER(ctypes.c_void_p),
        )(vtable_sl[0])
        p_pf = ctypes.c_void_p()
        hr = QI(p_sl, ctypes.byref(IID_IPersistFile), ctypes.byref(p_pf))
        if hr != 0:
            return False

        vtable_pf = ctypes.cast(
            p_pf, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
        ).contents

        # IPersistFile::Save (offset 6)
        Save = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, wintypes.LPCWSTR, wintypes.BOOL
        )(vtable_pf[6])
        hr = Save(p_pf, lnk_path, True)

        # Release interfaces
        Release_proto = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)
        Release_proto(vtable_pf[2])(p_pf)
        Release_proto(vtable_sl[2])(p_sl)

        return hr == 0
    except Exception as e:
        log(f"Failed to create shortcut at {lnk_path}: {e}")
        return False


def get_current_executable() -> str:
    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable)
    return os.path.abspath(__file__)


def install_application() -> str:
    """Ensures InterLive is installed into C:\\InterLive\\InterLive.exe and creates shortcuts."""
    current_exe = get_current_executable()
    target_exe = current_exe

    if getattr(sys, "frozen", False):
        try:
            os.makedirs(APP_DIR, exist_ok=True)
            if current_exe.lower() != INSTALLED_EXE.lower():
                try:
                    shutil.copy2(current_exe, INSTALLED_EXE)
                    log(f"Application installed to {INSTALLED_EXE}")
                    target_exe = INSTALLED_EXE
                except Exception as e:
                    log(f"Could not copy to {INSTALLED_EXE} (using current): {e}")
                    target_exe = current_exe
            else:
                target_exe = INSTALLED_EXE
        except Exception as e:
            log(f"Install error: {e}")

    setup_all_shortcuts(target_exe)
    # Default to auto-start enabled if not previously configured
    if not is_autostart_configured():
        set_autostart_enabled(True, target_exe)

    return target_exe


def setup_all_shortcuts(exe_path: str = ""):
    if not exe_path:
        exe_path = INSTALLED_EXE if os.path.isfile(INSTALLED_EXE) else get_current_executable()

    # 1. Desktop shortcut
    desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    if os.path.isdir(desktop_dir):
        desktop_lnk = os.path.join(desktop_dir, "InterLive Live Wallpaper.lnk")
        create_windows_shortcut(
            exe_path,
            desktop_lnk,
            args="",
            desc="InterLive - Windows 11 Live Video Wallpaper Engine",
            icon=exe_path,
        )
        log(f"Desktop shortcut created: {desktop_lnk}")

    # 2. Start Menu Programs shortcut
    programs_dir = os.path.join(
        os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"
    )
    if os.path.isdir(programs_dir):
        programs_lnk = os.path.join(programs_dir, "InterLive Live Wallpaper.lnk")
        create_windows_shortcut(
            exe_path,
            programs_lnk,
            args="",
            desc="InterLive - Windows 11 Live Video Wallpaper Engine",
            icon=exe_path,
        )
        log(f"Start Menu shortcut created: {programs_lnk}")


def is_autostart_configured() -> bool:
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if "autostart" in cfg:
                    return True
        except Exception:
            pass
    return False


def is_autostart_enabled() -> bool:
    # Check Windows Registry
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ
        ) as key:
            val, _ = winreg.QueryValueEx(key, "InterLive")
            if val:
                return True
    except Exception:
        pass

    # Check Startup folder
    startup_dir = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup",
    )
    startup_lnk = os.path.join(startup_dir, "InterLive.lnk")
    return os.path.isfile(startup_lnk)


def set_autostart_enabled(enable: bool, exe_path: str = ""):
    if not exe_path:
        exe_path = INSTALLED_EXE if os.path.isfile(INSTALLED_EXE) else get_current_executable()

    # 1. Update Windows Registry Run key
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enable:
                winreg.SetValueEx(
                    key, "InterLive", 0, winreg.REG_SZ, f'"{exe_path}" --autostart'
                )
                log(f"Registry autostart registered: '{exe_path}' --autostart")
            else:
                try:
                    winreg.DeleteValue(key, "InterLive")
                    log("Registry autostart deleted.")
                except FileNotFoundError:
                    pass
    except Exception as e:
        log(f"Registry autostart setting error: {e}")

    # 2. Update Windows Startup folder shortcut
    startup_dir = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup",
    )
    startup_lnk = os.path.join(startup_dir, "InterLive.lnk")
    if enable:
        try:
            os.makedirs(startup_dir, exist_ok=True)
            create_windows_shortcut(
                exe_path,
                startup_lnk,
                args="--autostart",
                desc="InterLive Auto-start live wallpaper on reboot",
                icon=exe_path,
            )
            log("Startup folder shortcut created.")
        except Exception as e:
            log(f"Startup shortcut error: {e}")
    else:
        if os.path.isfile(startup_lnk):
            try:
                os.remove(startup_lnk)
                log("Startup folder shortcut removed.")
            except Exception:
                pass

    # 3. Save state to config.json
    try:
        cfg = {}
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        cfg["autostart"] = enable
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND

user32.SendMessageTimeoutW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_size_t),
]
user32.SendMessageTimeoutW.restype = ctypes.c_ssize_t

user32.FindWindowExW.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
]
user32.FindWindowExW.restype = wintypes.HWND

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL

user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
user32.SetParent.restype = wintypes.HWND

user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL


def get_desktop_target_hwnd(max_retries: int = 15) -> int:
    """Finds the desktop wallpaper host window. Retries during system reboot until ready."""
    for attempt in range(max_retries):
        progman = user32.FindWindowW("Progman", None)
        if progman:
            log(f"Progman HWND: {progman:#010x} (attempt {attempt + 1})")
            result = ctypes.c_size_t(0)
            user32.SendMessageTimeoutW(
                progman,
                0x052C,
                0,
                0,
                0x0000,
                1000,
                ctypes.byref(result),
            )

            # 1. Primary check for Windows 11 (24H2): WorkerW child inside Progman behind icons
            workerw = user32.FindWindowExW(progman, 0, "WorkerW", None)
            if workerw:
                log(f"Found active child WorkerW inside Progman: {workerw:#010x}")
                return workerw

            # 2. Sibling check for Windows 10 / earlier Win 11 builds
            target_sibling = 0

            def enum_windows_cb(hwnd, lparam):
                nonlocal target_sibling
                shelldll = user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
                if shelldll:
                    w = user32.FindWindowExW(0, hwnd, "WorkerW", None)
                    if w:
                        target_sibling = w
                        log(f"Found WorkerW sibling behind SHELLDLL_DefView: {w:#010x}")
                        return False
                return True

            user32.EnumWindows(WNDENUMPROC(enum_windows_cb), 0)
            if target_sibling:
                return target_sibling

            log(f"Fallback directly targeting Progman: {progman:#010x}")
            return progman

        time.sleep(1)

    log("Failed to locate Progman or WorkerW after retries.")
    return 0


def get_physical_screen_size():
    try:
        hdc = user32.GetDC(0)
        w = gdi32.GetDeviceCaps(hdc, 118)  # DESKTOPHORZRES
        h = gdi32.GetDeviceCaps(hdc, 117)  # DESKTOPVERTRES
        user32.ReleaseDC(0, hdc)
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    if w <= 0 or h <= 0:
        w, h = 1920, 1080
    return w, h


def create_tray_icon() -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setBrush(QColor("#2563EB"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 28, 28, 6, 6)

    painter.setBrush(QColor("#FFFFFF"))
    triangle = QPainterPath()
    triangle.moveTo(12, 9)
    triangle.lineTo(23, 16)
    triangle.lineTo(12, 23)
    triangle.closeSubpath()
    painter.drawPath(triangle)
    painter.end()

    return QIcon(pixmap)


class WallpaperWindow(QMainWindow):
    def __init__(self, video_path: str):
        super().__init__()
        self.video_path = video_path

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)

        width, height = get_physical_screen_size()
        self.setGeometry(0, 0, width, height)

        self.video_widget = QVideoWidget(self)
        self.video_widget.setGeometry(0, 0, width, height)
        self.video_widget.setAspectRatioMode(
            Qt.AspectRatioMode.KeepAspectRatioByExpanding
        )
        self.setCentralWidget(self.video_widget)

        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)

        self.audio_output.setMuted(True)
        self.audio_output.setVolume(0.0)

        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
        self.media_player.mediaStatusChanged.connect(self.on_media_status)
        self.media_player.errorOccurred.connect(self.on_media_error)
        self.media_player.setSource(QUrl.fromLocalFile(self.video_path))

    def on_media_status(self, status):
        log(f"MediaStatus: {status}")
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.media_player.setPosition(0)
            self.media_player.play()

    def on_media_error(self, error, error_string):
        log(f"MediaPlayer Error: {error} - {error_string}")

    def inject_to_desktop(self):
        width, height = get_physical_screen_size()
        log(f"Applying physical resolution: {width} x {height}")

        self.setGeometry(0, 0, width, height)
        self.video_widget.setGeometry(0, 0, width, height)

        self.show()

        target_hwnd = get_desktop_target_hwnd()
        qt_hwnd = int(self.winId())
        log(f"Injecting Qt HWND {qt_hwnd:#010x} into Desktop Target {target_hwnd:#010x}")

        if target_hwnd:
            res = user32.SetParent(qt_hwnd, target_hwnd)
            log(f"SetParent returned: {res:#010x}")

            SWP_SHOWWINDOW = 0x0040
            SWP_NOACTIVATE = 0x0010
            user32.SetWindowPos(
                qt_hwnd,
                0,
                0,
                0,
                width,
                height,
                SWP_SHOWWINDOW | SWP_NOACTIVATE,
            )
            log(f"SetWindowPos applied: 0, 0, {width}, {height}")

        self.media_player.play()
        log("Media player play() initiated.")

        # Invalidate desktop icons to compose them crisply over video
        progman = user32.FindWindowW("Progman", None)
        if progman:
            shelldll = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
            if shelldll:
                user32.InvalidateRect(shelldll, None, True)
                user32.UpdateWindow(shelldll)

    def stop_playback(self):
        self.media_player.stop()


class SetupDialog(QWidget):
    def __init__(self, on_confirmed_callback, is_active=False):
        super().__init__()
        self.on_confirmed_callback = on_confirmed_callback
        self.selected_file_path = ""
        self.is_active = is_active

        self.setWindowTitle("InterLive - Live Wallpaper Manager")
        self.setFixedSize(540, 310)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet("""
            QWidget {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel#TitleLabel {
                font-size: 17px;
                font-weight: 700;
                color: #FFFFFF;
            }
            QLabel#StatusLabel {
                font-size: 12px;
                font-weight: 600;
                color: #10B981;
            }
            QLabel#SubLabel {
                font-size: 12px;
                color: #94A3B8;
            }
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: #E2E8F0;
            }
            QCheckBox {
                font-size: 13px;
                color: #CBD5E1;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1E293B;
            }
            QCheckBox::indicator:hover {
                border-color: #3B82F6;
            }
            QCheckBox::indicator:checked {
                background-color: #2563EB;
                border-color: #2563EB;
            }
            QPushButton {
                font-size: 13px;
                font-weight: 600;
                border-radius: 6px;
                padding: 9px 16px;
                border: none;
            }
            QPushButton#BrowseBtn {
                background-color: #334155;
                color: #F8FAFC;
            }
            QPushButton#BrowseBtn:hover {
                background-color: #475569;
            }
            QPushButton#ShortcutBtn {
                background-color: transparent;
                color: #94A3B8;
                border: 1px solid #334155;
                padding: 7px 12px;
                font-size: 12px;
            }
            QPushButton#ShortcutBtn:hover {
                background-color: #1E293B;
                color: #FFFFFF;
            }
            QPushButton#ConfirmBtn {
                background-color: #2563EB;
                color: #FFFFFF;
            }
            QPushButton#ConfirmBtn:hover {
                background-color: #1D4ED8;
            }
            QPushButton#ConfirmBtn:disabled {
                background-color: #1E293B;
                color: #64748B;
            }
            QPushButton#HideBtn {
                background-color: transparent;
                color: #94A3B8;
                border: 1px solid #334155;
            }
            QPushButton#HideBtn:hover {
                background-color: #1E293B;
                color: #FFFFFF;
            }
        """)

        self.init_ui()
        self.center_window()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(12)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(3)
        title_label = QLabel("InterLive Wallpaper Manager", self)
        title_label.setObjectName("TitleLabel")

        status_text = (
            "● Live Wallpaper Active on Desktop"
            if self.is_active
            else "Select a video to set as your desktop background"
        )
        self.status_label = QLabel(status_text, self)
        self.status_label.setObjectName("StatusLabel")
        if not self.is_active:
            self.status_label.setStyleSheet("color: #94A3B8;")

        header_layout.addWidget(title_label)
        header_layout.addWidget(self.status_label)
        layout.addLayout(header_layout)

        file_layout = QHBoxLayout()
        file_layout.setSpacing(10)
        self.path_input = QLineEdit(self)
        placeholder = (
            SAVED_VIDEO_PATH
            if os.path.isfile(SAVED_VIDEO_PATH)
            else "Choose an MP4 video..."
        )
        self.path_input.setText(placeholder)
        self.path_input.setReadOnly(True)

        self.browse_btn = QPushButton("Select Video", self)
        self.browse_btn.setObjectName("BrowseBtn")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(self.select_file)

        file_layout.addWidget(self.path_input)
        file_layout.addWidget(self.browse_btn)
        layout.addLayout(file_layout)

        # Autostart checkbox & shortcut recreation
        options_layout = QHBoxLayout()
        self.autostart_checkbox = QCheckBox(
            "Auto-start on laptop restart / boot", self
        )
        self.autostart_checkbox.setChecked(is_autostart_enabled())
        self.autostart_checkbox.stateChanged.connect(self.on_autostart_changed)
        options_layout.addWidget(self.autostart_checkbox)

        options_layout.addStretch()

        self.shortcut_btn = QPushButton("Create Shortcut", self)
        self.shortcut_btn.setObjectName("ShortcutBtn")
        self.shortcut_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.shortcut_btn.setToolTip("Create or restore desktop and start menu shortcuts")
        self.shortcut_btn.clicked.connect(self.recreate_shortcuts)
        options_layout.addWidget(self.shortcut_btn)
        layout.addLayout(options_layout)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.hide_btn = QPushButton("Hide to Tray", self)
        self.hide_btn.setObjectName("HideBtn")
        self.hide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hide_btn.clicked.connect(self.close)
        button_layout.addWidget(self.hide_btn)

        button_layout.addStretch()

        self.confirm_btn = QPushButton("Set as Wallpaper", self)
        self.confirm_btn.setObjectName("ConfirmBtn")
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.clicked.connect(self.confirm_selection)
        button_layout.addWidget(self.confirm_btn)

        layout.addLayout(button_layout)

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def on_autostart_changed(self, state):
        enable = state == Qt.CheckState.Checked.value or state == 2
        set_autostart_enabled(enable)

    def recreate_shortcuts(self):
        setup_all_shortcuts()
        QMessageBox.information(
            self,
            "Shortcuts Updated",
            "InterLive shortcuts have been created on your Desktop and in your Start Menu!",
        )

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select MP4 Video",
            "",
            "MP4 Video Files (*.mp4)",
        )
        if file_path:
            self.selected_file_path = file_path
            self.path_input.setText(file_path)
            self.confirm_btn.setEnabled(True)

    def confirm_selection(self):
        target = self.selected_file_path or (
            SAVED_VIDEO_PATH if os.path.isfile(SAVED_VIDEO_PATH) else ""
        )
        if not target or not os.path.isfile(target):
            QMessageBox.warning(
                self, "Invalid File", "Please select a valid MP4 file first."
            )
            return

        os.makedirs(APP_DIR, exist_ok=True)
        target_path = SAVED_VIDEO_PATH

        if self.selected_file_path and self.selected_file_path != target_path:
            try:
                shutil.copy2(self.selected_file_path, target_path)
            except Exception as e:
                QMessageBox.critical(
                    self, "Storage Error", f"Failed to save video:\n{e}"
                )
                return

        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({"video_path": target_path}, f, indent=2)
        except Exception:
            pass

        self.status_label.setText("● Live Wallpaper Active on Desktop")
        self.status_label.setStyleSheet("color: #10B981;")
        self.on_confirmed_callback(target_path)
        self.close()


class LiveWallpaperApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.wallpaper_window = None
        self.setup_dialog = None

        # Install application to C:\InterLive and create shortcuts
        install_application()

        self.setup_tray_icon()
        self.bootstrap()

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(create_tray_icon(), self.app)
        self.tray_icon.setToolTip("InterLive Wallpaper (Click to open controls)")

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2563EB;
                color: #FFFFFF;
            }
        """)

        open_action = tray_menu.addAction("Open Control Window")
        open_action.triggered.connect(self.open_setup)

        change_action = tray_menu.addAction("Change Wallpaper Video")
        change_action.triggered.connect(self.change_wallpaper)

        tray_menu.addSeparator()

        self.autostart_action = tray_menu.addAction("Start on Laptop Boot")
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(is_autostart_enabled())
        self.autostart_action.triggered.connect(self.toggle_tray_autostart)

        shortcut_action = tray_menu.addAction("Create Desktop Shortcut")
        shortcut_action.triggered.connect(lambda: setup_all_shortcuts())

        tray_menu.addSeparator()

        exit_action = tray_menu.addAction("Exit Wallpaper")
        exit_action.triggered.connect(self.exit_application)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def toggle_tray_autostart(self):
        enable = self.autostart_action.isChecked()
        set_autostart_enabled(enable)

    def on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.open_setup()

    def bootstrap(self):
        os.makedirs(APP_DIR, exist_ok=True)
        log("Bootstrapping InterLive...")
        active_video = self.get_configured_video()

        is_autostart_launch = "--autostart" in sys.argv

        if active_video and os.path.isfile(active_video):
            log(f"Active video found: {active_video}")
            self.launch_engine(active_video)
            # If launched manually, present control dialog; if autostarted on boot, remain silent in tray
            if not is_autostart_launch:
                self.open_setup(is_active=True)
            else:
                log("Silently active on desktop after Windows boot.")
        else:
            log("No active video configured, opening setup dialog.")
            self.open_setup(is_active=False)

    def get_configured_video(self) -> str:
        if os.path.isfile(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    path = data.get("video_path", "")
                    if os.path.isfile(path):
                        return path
            except (json.JSONDecodeError, OSError):
                pass

        if os.path.isfile(SAVED_VIDEO_PATH):
            return SAVED_VIDEO_PATH

        return ""

    def launch_engine(self, video_path: str):
        log(f"Launching engine with video: {video_path}")
        if self.wallpaper_window:
            self.wallpaper_window.stop_playback()
            self.wallpaper_window.close()
            self.wallpaper_window = None

        self.wallpaper_window = WallpaperWindow(video_path)
        self.wallpaper_window.inject_to_desktop()

    def open_setup(self, is_active=True):
        if not self.setup_dialog or not self.setup_dialog.isVisible():
            self.setup_dialog = SetupDialog(
                self.launch_engine, is_active=is_active
            )
            self.setup_dialog.show()
        self.setup_dialog.raise_()
        self.setup_dialog.activateWindow()

    def change_wallpaper(self):
        log("Change wallpaper requested.")
        if self.wallpaper_window:
            self.wallpaper_window.stop_playback()
            self.wallpaper_window.close()
            self.wallpaper_window = None

        if os.path.isfile(CONFIG_PATH):
            try:
                os.remove(CONFIG_PATH)
            except OSError:
                pass

        self.open_setup(is_active=False)

    def exit_application(self):
        log("Exiting application...")
        if self.wallpaper_window:
            self.wallpaper_window.stop_playback()
            self.wallpaper_window.close()

        self.tray_icon.hide()
        self.app.quit()

    def run(self):
        return self.app.exec()


if __name__ == "__main__":
    app_instance = LiveWallpaperApp()
    sys.exit(app_instance.run())
