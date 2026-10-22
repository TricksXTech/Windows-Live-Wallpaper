# InterLive - Windows 11 Live Video Wallpaper Engine

**InterLive** is a lightweight, hardware-accelerated live video wallpaper application designed for **Windows 11 (including 24H2)** and **Windows 10**. It embeds seamless, muted, looping MP4 videos directly onto your Windows desktop canvas—sitting cleanly **behind your desktop icons** and taskbar without blocking icon selection, dragging, or right-click context menus.

---

## Features

- **True Desktop Integration:** Hooks into the Windows desktop architecture (`Progman` / `WorkerW`) to render videos beneath `SHELLDLL_DefView` (desktop icons).
- **Windows 11 24H2 Ready:** Native support for the new internal `WorkerW` child container structure introduced in modern Windows 11 updates.
- **Auto-Installation & Program Setup:** On launch, the executable automatically sets itself up inside `C:\InterLive\InterLive.exe` as a permanent application.
- **Automatic Shortcut Creation:** Instantly creates:
  - **Desktop Shortcut:** `Desktop\InterLive Live Wallpaper.lnk`
  - **Start Menu Shortcut:** `Start Menu\Programs\InterLive Live Wallpaper.lnk`
- **Auto-Start on Laptop Restart / Boot:** Automatically starts on Windows reboot via:
  - Windows Registry: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
  - Windows Startup Folder: `AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\InterLive.lnk`
  - Runs silently in the background on startup without annoying popups, immediately displaying your live video wallpaper.
- **High-DPI Aware:** Queries physical display metrics via hardware GDI (`GetDeviceCaps`), ensuring edge-to-edge full-screen playback on 100%, 125%, 150%, and 200% display scaling.
- **Modern Control GUI:** Dark-themed management window to select MP4 files, preview active wallpapers, toggle autostart, and manage shortcuts.
- **System Tray Integration:** Runs silently in the background with a system tray icon for quick access to the control dialog, wallpaper switcher, autostart toggle, and application exit.
- **Zero Console Window:** Runs completely hidden without black command-prompt terminal windows popping up.

---

## Application Directory Structure

All active wallpaper assets, persistent settings, and the installed program binary reside in:

```text
C:\InterLive\
├── InterLive.exe    # The installed program binary
├── wallpaper.mp4    # The active desktop video wallpaper
├── config.json      # Configuration settings (video path, autostart state)
└── engine.log       # Diagnostic operational log
```

---

## Prerequisites

1. **Operating System:** Windows 10 or Windows 11 (64-bit).
2. **Python:** Python 3.10 or newer (64-bit).
   - During Python installation, ensure you check: **"Add Python to PATH"**.

---

## Step 1: Install Required Libraries

Open **Command Prompt (cmd)** or **PowerShell** and run:

```bash
# Upgrade pip to latest version
python -m pip install --upgrade pip

# Install PyQt6 (GUI, Media Player, Video Rendering Widgets)
pip install PyQt6

# Install PyInstaller (Standalone Executable Compiler)
pip install pyinstaller
```

### Library Details:
- **`PyQt6`**: Powers the GUI window (`QWidget`), hardware-accelerated video decoding and playback (`QMediaPlayer`, `QVideoWidget`), audio control (`QAudioOutput`), and system tray management (`QSystemTrayIcon`).
- **`pyinstaller`**: Packages the Python script, Qt dynamic link libraries (`.dll`), and dependencies into a single, self-contained `.exe` binary.
- **`ctypes`, `wintypes`, `winreg`**: Built into Python standard library; handles low-level Win32 User32/GDI32 desktop hooks, native COM shortcut creation (`IShellLinkW`), and Windows Registry autostart keys.

---

## Step 2: Running from Source Code

To test or run the application directly using Python:

```powershell
# Navigate to project folder
cd D:\ABC

# Run the script
python live_wallpaper.py
```

---

## Step 3: Compiling into a Standalone `.exe`

To package the script into a single standalone `.exe` that runs on any Windows machine:

```powershell
python -m PyInstaller --clean --onefile --noconsole --name "InterLive" "D:\ABC\live_wallpaper.py"
```

The resulting binary will be generated at:
```text
D:\ABC\dist\InterLive.exe
```

### PyInstaller Flags Breakdown

| Flag | Purpose |
| :--- | :--- |
| `--clean` | Cleans PyInstaller build cache and removes temporary files before building. |
| `--onefile` | Bundles all Python runtime code, Qt libraries, and C-extensions into a single standalone `.exe`. |
| `--noconsole` | Completely suppresses the black terminal window so the application runs silently in the background. |
| `--name "InterLive"` | Sets the output binary name to `InterLive.exe`. |

---

## How It Works

### 1. First Run & Program Setup
When you run `InterLive.exe`:
- It ensures `C:\InterLive` is created.
- Copies itself to `C:\InterLive\InterLive.exe` as the installed program.
- Generates high-res shortcuts on your **Desktop** and in your **Start Menu Programs**.
- Registers `InterLive` in Windows Startup (`HKCU\...\Run` and Startup folder) so your live wallpaper automatically starts whenever your laptop boots or restarts.

### 2. Startup on Reboot
When you restart your laptop:
- Windows automatically launches `InterLive.exe --autostart`.
- The engine waits for Windows Explorer and `Progman` to finish initializing.
- The wallpaper starts playing automatically on your desktop, and the app stays minimized in the system tray without popping up any setup dialog.

### 3. Control Window & System Tray
- Double-click the **InterLive Live Wallpaper** shortcut on your Desktop or click the system tray icon to open the Manager window.
- From the Manager window, you can:
  - Click **"Select Video"** to change the MP4 wallpaper at any time.
  - Toggle **"Auto-start on laptop restart / boot"**.
  - Click **"Create Shortcut"** if you ever need to restore your desktop shortcut.
  - Click **"Hide to Tray"** to dismiss the window while keeping the live wallpaper playing.
  - Right-click the system tray icon for quick access to settings or to **Exit Wallpaper**.
