import os
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import scrolledtext, messagebox

# Configuration
CONFIG_FILE = "vray_config.json"
LOG_FILE = "vray_monitor.log"
SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.exr', '.tif', '.tiff'}
STABILIZATION_TIME = 5  # seconds
CHECK_INTERVAL = 300  # 5 minutes in seconds

# Default configuration
DEFAULT_CONFIG = {
    "slack_bot_token": "xoxb-your-bot-token-here",
    "channel": "C1234567890",
    "projects_root": "D:/Users/Pete/Documents/Projects",
    "check_interval_minutes": 5
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

class RenderHandler(FileSystemEventHandler):
    def __init__(self, slack_client, channel, project_name):
        self.slack_client = slack_client
        self.channel = channel
        self.project_name = project_name
        self.pending_files = {}
        
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.suffix.lower() in SUPPORTED_FORMATS:
            if "effectResult" in file_path.stem:
                logging.info(f"[{self.project_name}] New render detected: {file_path.name}")
                self.pending_files[str(file_path)] = time.time()
            else:
                logging.info(f"[{self.project_name}] Skipping non-effectResult file: {file_path.name}")
    
    def check_and_upload_pending(self):
        current_time = time.time()
        files_to_upload = []
        
        for file_path, detection_time in list(self.pending_files.items()):
            if current_time - detection_time >= STABILIZATION_TIME:
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    files_to_upload.append(file_path)
                del self.pending_files[file_path]
        
        for file_path in files_to_upload:
            self.upload_to_slack(file_path)
    
    def upload_to_slack(self, file_path):
        try:
            file_path = Path(file_path)
            file_name = file_path.name
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            logging.info(f"[{self.project_name}] Uploading {file_name} to {self.channel}...")
            
            response = self.slack_client.files_upload_v2(
                channel=self.channel,
                file=str(file_path),
                title=file_name,
                initial_comment=f"🎨 *{self.project_name}* - Render complete\n📁 File: *{file_name}*\n⏰ Completed: {timestamp}"
            )
            
            logging.info(f"[{self.project_name}] Successfully uploaded {file_name}")
            
        except SlackApiError as e:
            logging.error(f"[{self.project_name}] Error uploading to Slack:")
            logging.error(f"  Error: {e.response['error']}")
            logging.error(f"  Full response: {e.response.data}")
            logging.error(f"  Status code: {e.response.status_code}")
            if 'needed' in e.response.data:
                logging.error(f"  Needed scopes: {e.response.data['needed']}")
            if 'provided' in e.response.data:
                logging.error(f"  Provided scopes: {e.response.data['provided']}")
        except Exception as e:
            logging.error(f"[{self.project_name}] Unexpected error: {str(e)}")
            logging.error(f"  Exception type: {type(e).__name__}")
            import traceback
            logging.error(f"  Traceback: {traceback.format_exc()}")

class MonitorService:
    def __init__(self):
        self.config = None
        self.slack_client = None
        self.observers = []
        self.handlers = []
        self.running = False
        self.monitor_thread = None
        
    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            logging.info(f"Creating default config: {CONFIG_FILE}")
            with open(CONFIG_FILE, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG
        
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    
    def find_export_folders(self, root_path):
        """Recursively find all folders named 'Export' under root_path"""
        export_folders = []
        
        if not os.path.exists(root_path):
            logging.warning(f"Projects root path does not exist: {root_path}")
            return export_folders
        
        for dirpath in os.walk(root_path):
            # Check if current directory is named 'Export' (case-insensitive)
            current_folder_name = os.path.basename(dirpath).lower()
            if current_folder_name == 'export':
                # Extract project name from path
                rel_path = os.path.relpath(dirpath, root_path)
                # Get the parent folder name as project name
                path_parts = rel_path.split(os.sep)
                project_name = path_parts[0] if len(path_parts) > 1 else rel_path
                
                export_folders.append({
                    'name': project_name,
                    'path': dirpath
                })
                
                logging.info(f"Found Export folder for project: {project_name}")
        
        return export_folders
    
    def start_monitoring(self):
        if self.running:
            logging.warning("Monitoring is already running")
            return False
        
        self.config = self.load_config()
        slack_token = self.config.get('slack_bot_token')
        
        if not slack_token or slack_token == "xoxb-your-bot-token-here":
            logging.error("Please configure your Slack bot token in vray_config.json")
            return False
        
        self.slack_client = WebClient(token=slack_token)
        
        try:
            auth_test = self.slack_client.auth_test()
            logging.info(f"Connected to Slack as: {auth_test['user']}")
        except SlackApiError as e:
            logging.error(f"Error connecting to Slack: {e.response['error']}")
            return False
        
        channel = self.config.get('channel')
        projects_root = self.config.get('projects_root')
        
        if not channel:
            logging.error("Channel not specified in config")
            return False
        
        if not projects_root:
            logging.error("Projects root path not specified in config")
            return False
        
        # Validate channel ID format
        if not channel.startswith('C'):
            logging.error("=" * 60)
            logging.error("CONFIGURATION ERROR: Invalid channel format")
            logging.error("=" * 60)
            logging.error(f"Channel must be a Channel ID (starts with 'C'), not a name.")
            logging.error(f"You provided: {channel}")
            logging.error("")
            logging.error("To get your channel ID:")
            logging.error("1. Open Slack in your browser or desktop app")
            logging.error("2. Go to the channel you want to use")
            logging.error("3. Click the channel name at the top")
            logging.error("4. Scroll down and copy the 'Channel ID'")
            logging.error("5. Paste it in vray_config.json")
            logging.error("")
            logging.error("Example: \"channel\": \"C1234567890\"")
            logging.error("=" * 60)
            return False
        
        logging.info(f"Using channel ID: {channel}")
        
        # Find all export folders
        export_folders = self.find_export_folders(projects_root)
        
        if not export_folders:
            logging.warning(f"No 'Export' folders found in {projects_root}")
            return False
        
        # Setup observers for each folder
        for folder_info in export_folders:
            handler = RenderHandler(self.slack_client, channel, folder_info['name'])
            observer = Observer()
            observer.schedule(handler, folder_info['path'], recursive=True)
            observer.start()
            
            self.observers.append(observer)
            self.handlers.append(handler)
            
            logging.info(f"Monitoring: {folder_info['name']} at {folder_info['path']}")
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logging.info(f"Started monitoring {len(export_folders)} project folders")
        return True
    
    def _monitor_loop(self):
        check_interval = self.config.get('check_interval_minutes', 5) * 60
        
        while self.running:
            time.sleep(1)
            for handler in self.handlers:
                handler.check_and_upload_pending()
    
    def stop_monitoring(self):
        if not self.running:
            return
        
        logging.info("Stopping monitoring...")
        self.running = False
        
        for observer in self.observers:
            observer.stop()
        
        for observer in self.observers:
            observer.join()
        
        self.observers = []
        self.handlers = []
        logging.info("Monitoring stopped")

class ControlWindow:
    def __init__(self, monitor_service):
        self.monitor_service = monitor_service
        self.window = None
        
    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
            return
        
        self.window = tk.Tk()
        self.window.title("V-Ray Slack Monitor")
        self.window.geometry("700x500")
        self.window.minsize(600, 400)
        self.window.resizable(True, True)
        
        # Status frame
        status_frame = tk.Frame(self.window, pady=10)
        status_frame.pack(fill=tk.X)
        
        self.status_label = tk.Label(
            status_frame, 
            text="Status: " + ("Running" if self.monitor_service.running else "Stopped"),
            font=("Arial", 12, "bold"),
            fg="green" if self.monitor_service.running else "red"
        )
        self.status_label.pack()
        
        # Buttons frame
        btn_frame = tk.Frame(self.window, pady=10)
        btn_frame.pack()
        
        self.start_btn = tk.Button(
            btn_frame, 
            text="Start", 
            command=self.start_monitoring,
            width=15,
            height=2,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold")
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            btn_frame, 
            text="Stop", 
            command=self.stop_monitoring,
            width=15,
            height=2,
            bg="#f44336",
            fg="white",
            font=("Arial", 10, "bold")
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Config and Log buttons
        file_btn_frame = tk.Frame(self.window, pady=10)
        file_btn_frame.pack()
        
        tk.Button(
            file_btn_frame,
            text="Open Config",
            command=self.open_config,
            width=15,
            height=1
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            file_btn_frame,
            text="Open Log",
            command=self.open_log,
            width=15,
            height=1
        ).pack(side=tk.LEFT, padx=5)
        
        # Log display
        log_label = tk.Label(self.window, text="Recent Log Entries:", font=("Arial", 10))
        log_label.pack(pady=(10, 5))
        
        # Create a frame for the log text with scrollbar
        log_frame = tk.Frame(self.window)
        log_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.NONE,  # No word wrap - show full lines
            state=tk.DISABLED,
            font=("Consolas", 9)  # Monospace font for better log readability
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Add horizontal scrollbar
        h_scrollbar = tk.Scrollbar(log_frame, orient=tk.HORIZONTAL, command=self.log_text.xview)
        self.log_text.configure(xscrollcommand=h_scrollbar.set)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Update log display
        self.update_log_display()
        
        # Update button states
        self.update_button_states()
        
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.window.mainloop()
    
    def update_button_states(self):
        if self.monitor_service.running:
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.status_label.config(text="Status: Running", fg="green")
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Stopped", fg="red")
    
    def start_monitoring(self):
        if self.monitor_service.start_monitoring():
            messagebox.showinfo("Success", "Monitoring started successfully!")
            self.update_button_states()
            self.update_log_display()
        else:
            messagebox.showerror("Error", "Failed to start monitoring. Check log for details.")
    
    def stop_monitoring(self):
        self.monitor_service.stop_monitoring()
        messagebox.showinfo("Stopped", "Monitoring stopped")
        self.update_button_states()
        self.update_log_display()
    
    def open_config(self):
        if os.path.exists(CONFIG_FILE):
            os.startfile(CONFIG_FILE)
        else:
            messagebox.showwarning("Not Found", f"{CONFIG_FILE} not found")
    
    def open_log(self):
        if os.path.exists(LOG_FILE):
            os.startfile(LOG_FILE)
        else:
            messagebox.showwarning("Not Found", f"{LOG_FILE} not found")
    
    def update_log_display(self):
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-20:]  # Last 20 lines
                
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, ''.join(recent_lines))
            self.log_text.config(state=tk.DISABLED)
            self.log_text.see(tk.END)
    
    def hide_window(self):
        if self.window:
            self.window.withdraw()

def create_image():
    """Create system tray icon"""
    width = 64
    height = 64
    color1 = (0, 120, 215)
    color2 = (255, 255, 255)
    
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle([16, 16, 48, 48], fill=color2)
    dc.rectangle([20, 20, 44, 28], fill=color1)
    dc.rectangle([20, 32, 44, 40], fill=color1)
    
    return image

def main():
    monitor_service = MonitorService()
    control_window = ControlWindow(monitor_service)
    
    # Show control window on startup
    window_thread = threading.Thread(target=control_window.show, daemon=True)
    window_thread.start()
    
    # Auto-start monitoring
    monitor_service.start_monitoring()
    
    def on_quit(icon, item):
        monitor_service.stop_monitoring()
        icon.stop()
        if control_window.window:
            control_window.window.quit()
    
    def on_show(icon, item):
        if control_window.window and control_window.window.winfo_exists():
            control_window.window.deiconify()
            control_window.window.lift()
            control_window.window.focus_force()
        else:
            threading.Thread(target=control_window.show, daemon=True).start()
    
    # Create system tray icon
    icon = pystray.Icon(
        "vray_monitor",
        create_image(),
        "V-Ray Slack Monitor",
        menu=pystray.Menu(
            item('Show Control Panel', on_show),
            item('Quit', on_quit)
        )
    )
    
    # Run system tray icon
    icon.run()

if __name__ == "__main__":
    main()