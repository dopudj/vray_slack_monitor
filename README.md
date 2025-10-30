# V-Ray Slack Monitor

![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

A Windows system tray application that automatically monitors V-Ray render outputs and posts completed renders to Slack channels. Perfect for architects and designers who want to stay notified about render completion without being tied to their workstation.

![notification](./assets/vray_slack_monitor.gif)


## ✨ Features

- 🎨 **Automatic Render Detection** - Monitors all Export folders under your Projects directory
- 📤 **Instant Slack Notifications** - Uploads renders with project name and timestamp
- 🖥️ **System Tray Integration** - Runs quietly in the background
- 🎛️ **Control Panel** - Easy Start/Stop controls and live log viewer
- 📁 **Multi-Project Support** - Automatically detects and monitors all projects
- 📊 **Resizable Interface** - Expandable window with horizontal log scrolling

## 📸 Screenshot

```
┌───────────────────────────────────────────────────────────────────┐
│   V-Ray Slack Monitor                                             │
├───────────────────────────────────────────────────────────────────┤
│ Status: Running                                                   │
│                                                                   │
│                     [ Start ]  [ Stop ]                           │
│                                                                   │
│                  [Open Config]  [Open Log]                        │
│                                                                   │
│ Recent Log Entries:                                               │
│ ┌───────────────────────────────────────────────────────────────┐ │
│ │ 2025-10-30 08:30:15 - INFO - [Villa_Project] New render...    │ │
│ │ 2025-10-30 08:30:16 - Successfully uploaded...                │ │
│ │                                                               │ │
│ └───────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Windows 10/11
- Python 3.7+ (for development)
- Slack workspace with admin access
- V-Ray rendering software

### Installation (Executable)

1. **Download the latest release** from [Releases](https://github.com/yourusername/vray-slack-monitor/releases)
2. **Extract** `VRay-Slack-Monitor.exe` to a folder
3. **Configure** (see Configuration section below)
4. **Run** the executable

### Installation (From Source)

```bash
# Clone the repository
git clone https://github.com/yourusername/vray-slack-monitor.git
cd vray-slack-monitor

# Install dependencies
pip install -r requirements.txt

# Run the application
python vray_slack_notifier.py
```

## ⚙️ Configuration

### 1. Create Slack App

1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name your app (e.g., "V-Ray Render Monitor")
4. Select your workspace

### 2. Add Bot Permissions

1. Navigate to **"OAuth & Permissions"**
2. Under **"Bot Token Scopes"**, add:
   - `chat:write`
   - `files:write`
3. Click **"Install to Workspace"**
4. Copy the **"Bot User OAuth Token"** (starts with `xoxb-`)

### 3. Get Channel ID

1. Open Slack and go to your desired channel
2. Click the channel name at the top
3. Scroll down and copy the **"Channel ID"** (starts with `C`)

### 4. Configure Application

Create or edit `vray_config.json` in the same folder as the executable:

```json
{
    "slack_bot_token": "xoxb-your-bot-token-here",
    "channel": "C1234567890",
    "projects_root": "D:/Projects",
    "check_interval_minutes": 5
}
```

**Configuration Options:**

- `slack_bot_token`: Your Slack bot token from step 2
- `channel`: Channel ID where renders will be posted
- `projects_root`: Root directory containing your project folders
- `check_interval_minutes`: How often to check for file changes (default: 5)

### 5. Project Structure

The app automatically finds all folders named `Export` under your projects root:

```
D:/Projects/
├── Villa_Project/
│   └── Export/          ← Monitored
│       ├── render001-alpha.jpg
│       └── render001-effectResult.jpg
├── Office_Design/
│   └── Export/          ← Monitored
│       └── final.exr
└── House_Interior/
    └── Export/          ← Monitored
```

Filename filter
- Only files whose filename contains the substring "effectResult" (case-sensitive) will be selected for upload.  
  Examples that will be detected:
  - `effectResult.png`
  - `my_scene_effectResult_v001.exr`
  - `final111-effectResult.jpg`  

Files that do not include "effectResult" in the name will be ignored by the monitor.


## 🎮 Usage

### Running the Application

1. **Start**: Double-click `VRay-Slack-Monitor.exe`
2. **Control Panel**: Right-click the system tray icon → "Show Control Panel"
3. **Stop Monitoring**: Click "Stop" button or right-click tray icon → "Quit"

### System Tray Features

- **Right-click** the tray icon for menu:
  - Show Control Panel
  - Quit

### Control Panel Features

- **Start/Stop** buttons to control monitoring
- **Open Config** to edit settings
- **Open Log** to view detailed logs
- **Live log viewer** showing recent activity
- **Resizable window** for better log readability

## 🔧 Building Executable

To build your own executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable (no console window)
pyinstaller --onefile --windowed --name "VRay-Slack-Monitor" vray_slack_notifier.py

# Find executable in dist/ folder
```

## 📝 Supported File Formats

- `.png`
- `.jpg` / `.jpeg`
- `.exr`
- `.tif` / `.tiff`

## 🐛 Troubleshooting

### "Missing scope" error
- Make sure you added both `chat:write` and `files:write` scopes
- Reinstall the app to your workspace after adding scopes

### "Invalid channel" error
- Use the Channel ID (starts with `C`), not the channel name
- Get it from: Slack → Channel name → "Channel ID"

### Renders not detected
- Ensure your Export folders are under the `projects_root` path
- Check folder name is exactly "Export" (case-insensitive)
- Verify file formats are supported

### Token errors
- Bot token must start with `xoxb-`
- Copy the entire token, including all characters
- Make sure there are no extra spaces in the config file

## 📋 Requirements

```
slack-sdk>=3.19.0
watchdog>=2.1.9
pystray>=0.19.4
Pillow>=9.3.0
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for architects and interior designers using V-Ray
- Inspired by the need to monitor long-running renders remotely
- Uses Slack's API for instant notifications

## 📧 Support

If you encounter any issues or have questions:
- Open an [Issue](https://github.com/yourusername/vray-slack-monitor/issues)
- Check existing issues for solutions

## 🔮 Future Features

- [ ] Select multiple folders from UI
- [ ] Custom message templates

---

**Made with ❤️ for the architecture and design community**