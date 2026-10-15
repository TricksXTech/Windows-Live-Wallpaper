# InterLive - Windows 11 Live Video Wallpaper Engine

**InterLive** is a lightweight, hardware-accelerated live video wallpaper application designed for **Windows 11 (including 24H2)** and **Windows 10**. It embeds seamless, muted, looping MP4 videos directly onto your Windows desktop canvas—sitting cleanly **behind your desktop icons** and taskbar without blocking icon selection, dragging, or right-click context menus.

---

## Features

- **True Desktop Integration:** Hooks into the Windows desktop architecture (`Progman` / `WorkerW`) to render videos beneath `SHELLDLL_DefView` (desktop icons).
- **Windows 11 24H2 Ready:** Native support for the new internal `WorkerW` child container structure introduced in modern Windows 11 updates.
- **High-DPI Aware:** Queries physical display metrics via hardware GDI (`GetDeviceCaps`), ensuring edge-to-edge full-screen playback on 100%, 125%, 150%, and 200% display scaling.
- **Modern Control GUI:** Dark-themed management window to select MP4 files, preview active wallpapers, and save configurations.
- **System Tray Integration:** Runs silently in the background with a system tray icon for quick access to the control dialog, wallpaper switcher, and application exit.
- **Zero Console Window:** Runs completely hidden without black command-prompt terminal windows popping up.

---

## File Architecture

All active wallpaper assets and persistent settings are stored in the standardized application directory:

```text
C:\InterLive\
├── wallpaper.mp4   # The currently active wallpaper video
├── config.json     # Configuration file storing video paths
└── engine.log      # Diagnostic logging (HWNDs, player states, resolutions)
```

---

## Prerequisites

1. **Operating System:** Windows 10 or Windows 11 (64-bit).
2. **Python:** Python 3.10 or newer (64-bit).
   - During Python installation, ensure you check the box: **"Add Python to PATH"**.

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
- **`PyQt6`**: Powers the GUI window (`QWidget`), video decoding and playback (`QMediaPlayer`, `QVideoWidget`), audio control (`QAudioOutput`), and system tray management (`QSystemTrayIcon`).
- **`pyinstaller`**: Packages the Python script, Qt dynamic link libraries (`.dll`), and dependencies into a single, self-contained `.exe` binary.
- **`ctypes` & `wintypes`**: Built into Python standard library; used for low-level Windows User32/GDI32 Win32 API interop.

---

## Step 2: Running from Source Code

To test or run the application directly using Python:

```powershell
# Navigate to the project folder
cd D:\ABC

# Run the script
python live_wallpaper.py
```

---

## Step 3: Compiling into a Standalone `.exe`

You can compile the script into a single executable that runs independently without requiring Python to be installed on other systems.

### Recommended Build Command (Standard User Mode)

```powershell
python -m PyInstaller --clean --onefile --noconsole --name "InterLive_App" "D:\ABC\live_wallpaper.py"
```

> **Why this is recommended:** Running as a standard user process (`asInvoker`) allows the application to cleanly parent into Windows Explorer (`explorer.exe`, which runs at Medium Integrity). This avoids Windows User Interface Privilege Isolation (UIPI) restrictions and eliminates annoying UAC administrator prompts on startup.

---

### Alternative Build Command (Administrator Mode)

If you specifically require the `.exe` to request Windows Administrator privileges on launch:

```powershell
python -m PyInstaller --clean --onefile --noconsole --uac-admin --name "InterLive_Admin" "D:\ABC\live_wallpaper.py"
```

---

### PyInstaller Flags Breakdown

| Flag | Purpose |
| :--- | :--- |
| `--clean` | Cleans PyInstaller build cache and removes temporary files before building. |
| `--onefile` | Bundles all Python code, Qt libraries, and C-extensions into a single `.exe`. |
| `--noconsole` | Hides the black terminal/command prompt window so the app runs silently in the background. |
| `--name <name>` | Sets the output binary name (e.g., `InterLive_App.exe`). |
| `--uac-admin` | Adds an administrative elevation manifest (`requireAdministrator`) to the executable. |

The compiled output will be generated inside the `dist\` folder:
```text
D:\ABC\dist\InterLive_App.exe
```

---

## How to Use the Application

1. **Launch:** Double-click `InterLive_App.exe`.
2. **Setup:**
   - If a video is already configured at `C:\InterLive\wallpaper.mp4`, playback begins automatically on the desktop, and the Control Window appears.
   - If launching for the first time, click **"Select Video"** to choose any standard `.mp4` file.
   - Click **"Set as Wallpaper"**. The video will be copied to `C:\InterLive\wallpaper.mp4` and injected behind your desktop icons immediately.
3. **Hide:** Click **"Hide to Tray"** or close the window. The video continues playing on your desktop.
4. **Control via System Tray:**
   - Click or double-click the blue tray icon in the Windows taskbar corner to reopen the Control Window.
   - Right-click the tray icon to access:
     - **Open Control Window**
     - **Change Wallpaper Video**
     - **Exit Wallpaper** (stops video and cleanly terminates the process)

---

## Troubleshooting

### 1. Wallpaper is not covering the full screen
- The engine uses GDI `GetDeviceCaps` to pull native screen dimensions (`1920 x 1080`). If your display scaling changes, reopening the app or restarting it from the tray menu will recalibrate the resolution to match your current display settings.

### 2. "PermissionError: [WinError 5] Access is denied" during PyInstaller build
- An instance of the `.exe` is currently running in the background. Stop all active instances before recompiling:
  ```powershell
  taskkill /F /IM InterLive*
  ```

### 3. Desktop icons disappearing or occluded
- The engine automatically issues `InvalidateRect` and `UpdateWindow` to `SHELLDLL_DefView` whenever a wallpaper starts. If icons ever need a manual refresh, click any blank space on your desktop and press **F5**.

### 4. Supported Video Formats
- Standard **H.264 video with AAC audio (in `.mp4` container)** is natively supported and hardware-accelerated by the Windows Media Foundation backend. High resolutions (1080p, 2K, 4K) run at minimal CPU usage (~1-3%).
