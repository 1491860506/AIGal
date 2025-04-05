import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, simpledialog
import tkinter.font as tkFont
from tkinter import messagebox
import os
import threading
import queue
import zipfile
import sys
import json
import re
import random
from ttkbootstrap import *
import time
import datetime
import shutil
import requests
import textwrap
import webbrowser
import ctypes
import math
import subprocess
from typing import Optional, Tuple, Any, Dict, Callable

VERSION = 105



# Import necessary modules
try:
    import gui_functions
    import handle_prompt
    import GPT
except ImportError:
    print("gui_functions.py not found. Some functionality may be missing.")

try:
    import renpy
    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

config_file = os.path.join(game_directory,"config.json")
default_config = {
    "剧情": {
        "language": "中文",
        "story_title": "",
        "if_on": False,
        "outline_content_entry": ""
    },
    "模型": {
        "default_config_name": "",  # To remember the last selected config for LLM
        "configs": {},
        "default_setting": {},
        "大纲_setting": [],
        "选项_setting": [],
        "故事开头_setting": [],
        "故事继续_setting": [],
        "故事结尾_setting": [],
        "全部人物绘画_setting": [],
        "单个人物绘画_setting": [],
        "故事地点绘画_setting": [],
        "背景音乐生成_setting": [],
        "开头音乐生成_setting": [],
        "结尾音乐生成_setting": [],
        "故事总结_setting": [],
        "本地导入_setting": [],
        "翻译_setting": []
    },
    "提示词": [
        {
            "kind": "大纲",
            "content": []
        },
        {
            "kind": "选项",
            "content": []
        },
        {
            "kind": "故事开头",
            "content": []
        },
        {
            "kind": "故事继续",
            "content": []
        },
        {
            "kind": "故事结尾",
            "content": []
        },
        {
            "kind": "全部人物绘画",
            "content": []
        },
        {
            "kind": "单个人物绘画",
            "content": []
        },
        {
            "kind": "故事地点绘画",
            "content": []
        },
        {
            "kind": "背景音乐生成",
            "content": []
        },
        {
            "kind": "开头音乐生成",
            "content": []
        },
        {
            "kind": "结尾音乐生成",
            "content": []
        },
        {
            "kind": "故事总结",
            "content": []
        },
        {
            "kind": "本地导入",
            "content": []
        },
        {
            "kind": "翻译",
            "content": []
        }
    ],
    "SOVITS": {
        "if_cloud": False,
        "api_key": "",
        "path1": "",
        "text1": "",
        "model1": "",
        "path2": "",
        "text2": "",
        "model2": "",
        "path3": "",
        "text3": "",
        "model3": "",
        "path4": "",
        "text4": "",
        "model4": "",
        "path5": "",
        "text5": "",
        "model5": "",
        "path6": "",
        "text6": "",
        "model6": "",
        "path7": "",
        "text7": "",
        "model7": ""
    },
    "AI_draw": {
        "cloud_on": False,
        "default_config_name": "",
        "configs": {},
        "character_config": [],
        "background_config": [],
        "convey_context": "不传入",
        "context_entry": "",
        "draw_non_main_character": False,
        "character_priorities":[],
        "background_priorities":[]
    },
    "AI音乐": {
        "if_on": False,
        "opening_if_on":False,
        "ending_if_on":False,
        "base_url": "",
        "api_key": ""
    }
}




def version_to_string(version):
    major = version // 100
    minor = (version % 100) // 10
    patch = version % 10
    return f"{major}.{minor}.{patch}"

def format_bytes(bytes_size):
    """Format bytes to KB, MB, GB, etc."""
    for unit in ['Bytes', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            break
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} {unit}"

class DownloadProgressDialog(Toplevel):
    def __init__(self, parent, download_url, filename):
        Toplevel.__init__(self, parent)
        self.withdraw()
        self.title("下载更新")
        self.resizable(False, False)  # 禁止调整窗口大小
        self.transient(parent)  # Make it a child of the main window
        self.grab_set() # Grab all events for this window

        self.download_url = download_url
        self.filename = filename  # Store filename as attribute

        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=280, mode="determinate")
        self.progress_bar.pack(padx=10, pady=5)  # Reduced pady

        self.percentage_label = tk.Label(self, text="0%")
        self.percentage_label.pack()

        self.size_label = tk.Label(self, text="0.00 Bytes / 0.00 Bytes")
        self.size_label.pack()

        self.speed_label = tk.Label(self, text="0.00 Bytes/s")
        self.speed_label.pack()

        # --- 定位和显示 ---
        # 确保在显示前设置好所有几何属性
        # 注意：place_window_center 通常会自己设置 geometry，所以先调用它
        self.place_window_center() # <--- 先计算并设置位置
        # 如果 place_window_center 不设置大小，或者你想强制大小，再调用 geometry
        # self.geometry("300x150") # <-- 如果 place_window_center 不管大小，则在这里设置

        self.update_idletasks() # 确保窗口尺寸计算完成

        self.deiconify() # <-- 添加：设置完位置和大小后显示

        self.start_time = None
        self.last_update_time=None
        self.last_downloaded_size = 0
        self.download_thread = threading.Thread(target=self.download_file)
        self.download_thread.start()

    def download_file(self):
        try:
            response = requests.get(self.download_url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            chunk_size = 8192
            self.start_time = time.time()
            self.last_update_time = self.start_time

            updates_dir = os.path.dirname(game_directory)
            filepath = os.path.join(updates_dir, self.filename)

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        percent_complete = (downloaded_size / total_size) * 100
                        self.progress_bar['value'] = percent_complete
                        self.percentage_label.config(text=f"{int(percent_complete)}%")
                        self.size_label.config(text=f"{format_bytes(downloaded_size)} / {format_bytes(total_size)}")
                        current_time = time.time()
                        time_diff = current_time - self.last_update_time
                        if time_diff > 0.1:
                            speed = (downloaded_size - self.last_downloaded_size) / time_diff
                            self.speed_label.config(text=f"{format_bytes(speed)}/s")
                            self.last_downloaded_size = downloaded_size
                            self.last_update_time = current_time
                        self.update_idletasks()

            # Run external updater after downloading.
            self.master.after(0, lambda: self.run_updater(filepath))
            self.destroy()

        except requests.exceptions.RequestException as e:
            messagebox.showerror("下载错误", f"下载失败: {e}")
            self.destroy()
        except Exception as e:
            messagebox.showerror("下载错误", f"发生错误: {e}")
            self.destroy()


    def run_updater(self, zip_file_path):
        try:
            app_dir = game_directory
            # Start the updater, passing required arguments
            updater_path = os.path.join(game_directory, "updater.exe")
            params = f'"{zip_file_path}" "{app_dir}"'
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                updater_path,
                params,
                None,
                1
            )
            self.master.destroy()
            sys.exit() # Exit the main application

        except Exception as e:
            messagebox.showerror("更新错误", f"启动更新程序失败: {e}")

class UpdateDialog(Toplevel):
    def __init__(self, parent, version,update_info,url):
        Toplevel.__init__(self, parent)
        self.withdraw()
        self.title("软件更新")
        self.geometry("300x300")  # 设置窗口大小
        self.resizable(False, False)  # 禁止调整窗口大小
        self.transient(parent) # Make it a child of the main window
        self.grab_set() # Grab all events for this window.

        # Text area frame
        text_frame = Frame(self)
        text_frame.pack(expand=True, fill=BOTH, padx=5, pady=5)

        self.update_info_text = Text(text_frame, wrap="word", height=7)  # Adjust height
        self.update_info_text.insert("1.0", update_info)
        self.update_info_text.config(state=DISABLED)  # Make it read-only
        self.update_info_text.pack(expand=True, fill=BOTH)

        # Button frame
        button_frame = Frame(self)
        button_frame.pack(pady=5) # Place it at the bottom

        yes_button = Button(button_frame, text="是", command=self.yes_click)
        yes_button.pack(side=LEFT, padx=5)

        no_button = Button(button_frame, text="否", command=self.no_click)
        no_button.pack(side=RIGHT, padx=5)
        self.protocol("WM_DELETE_WINDOW", self.no_click)

        # --- 定位和显示 ---
        self.place_window_center() # <--- 计算并设置位置
        # self.geometry("300x300") # <--- 如果 place_window_center 不管大小，则在这里设置
        self.update_idletasks()
        self.deiconify() # <-- 添加：设置完后显示

    def yes_click(self):
        self.result = True
        self.destroy()

    def no_click(self):
        self.result = False
        self.destroy()

class LocationSelectionDialog(Toplevel):
    """Dialog for selecting locations to redraw."""
    def __init__(self, parent, locations):
        super().__init__(parent)
        self.withdraw() # Hide initially
        self.title("选择重绘地点")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.locations = locations
        self.vars = {} # Dictionary to hold BooleanVars for checkboxes
        self.result = None # Store selected locations

        main_frame = ttk.Frame(self, padding="15 10 15 10")
        main_frame.pack(fill="both", expand=True)

        label = ttk.Label(main_frame, text="请勾选需要重绘背景图的地点:")
        label.pack(pady=(0, 10))

        # --- Checkbox Area with Scrollbar ---
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill="both", expand=True, pady=5)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        checkbox_container = ttk.Frame(canvas) # Frame inside canvas

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas_window = canvas.create_window((0, 0), window=checkbox_container, anchor="nw")

        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        checkbox_container.bind("<Configure>", on_frame_configure)

        # Populate checkboxes
        for location in self.locations:
            var = tk.BooleanVar(value=True) # Default to checked
            self.vars[location] = var
            cb = ttk.Checkbutton(checkbox_container, text=location, variable=var)
            cb.pack(anchor="w", padx=5, pady=2)

        # --- Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        cancel_button = ttk.Button(button_frame, text="取消", command=self.on_cancel, width=10)
        cancel_button.pack(side="right", padx=5)

        ok_button = ttk.Button(button_frame, text="确定", command=self.on_ok, style="Accent.TButton", width=10)
        ok_button.pack(side="right", padx=5)

        # --- Finalize ---
        self.update_idletasks() # Calculate size
        width = self.winfo_reqwidth() + 40 # Add some padding
        height = min(self.winfo_reqheight() + 40, 500) # Limit max height
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify() # Show

    def on_ok(self):
        self.result = [loc for loc, var in self.vars.items() if var.get()]
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

class HoverButton(tk.Canvas):
    """
    A custom button widget with a tooltip that appears on hover.
    
    The button is rendered as a stylish circle with a question mark inside.
    When the user hovers over the button, a customizable tooltip appears.
    """
    
    def __init__(
        self, 
        parent: tk.Widget,
        tooltip_text: str,
        width: int = 30,
        height: int = 30,
        button_color: str = "#4285F4",  # Google blue
        button_hover_color: str = "#3367D6",  # Darker blue
        button_press_color: str = "#1A73E8",  # Even darker blue for press effect
        text_color: str = "white",
        tooltip_max_width: int = 40,
        tooltip_bg: str = "#333333",
        tooltip_fg: str = "white",
        tooltip_font: Tuple[str, int, str] = ("Microsoft YaHei", 12),
        tooltip_padding: int = 5,
        tooltip_offset: Tuple[int, int] = (25, 25),
        tooltip_border_color: str = "#555555",  # Added border color option
        tooltip_shadow: bool = True,  # Added shadow effect option
        tooltip_radius: int = 5,  # Added corner radius option
        tooltip_animation: bool = True,  # Added animation option
        command: Optional[Callable] = None,
        **kwargs: Dict[str, Any]
    ):
        """
        Initialize the HoverButton widget.
        
        Args:
            parent: Parent widget
            tooltip_text: Text to display in tooltip
            width: Width of the button
            height: Height of the button
            button_color: Background color of the button
            button_hover_color: Background color when hovering
            button_press_color: Background color when pressed
            text_color: Color of the question mark text
            tooltip_max_width: Maximum width of tooltip text in characters
            tooltip_bg: Background color of tooltip
            tooltip_fg: Foreground (text) color of tooltip
            tooltip_font: Font for tooltip text
            tooltip_padding: Internal padding of tooltip
            tooltip_offset: (x, y) offset from button for tooltip positioning
            tooltip_border_color: Color of tooltip border
            tooltip_shadow: Whether to show shadow effect
            tooltip_radius: Radius for rounded corners (if supported)
            tooltip_animation: Whether to animate tooltip appearance
            command: Function to call when button is clicked
            **kwargs: Additional arguments for tk.Canvas
        """
        # Set default background to parent's background if not specified
        if 'background' not in kwargs:
            kwargs['background'] = 'white'
            
        # Initialize the Canvas
        super().__init__(
            parent, 
            width=width, 
            height=height, 
            highlightthickness=0,
            **kwargs
        )
        
        # Store parameters
        self.parent = parent
        self.button_color = button_color
        self.button_hover_color = button_hover_color
        self.button_press_color = button_press_color
        self.text_color = text_color
        self.tooltip_text = tooltip_text
        self.tooltip_max_width = tooltip_max_width
        self.tooltip_bg = tooltip_bg
        self.tooltip_fg = tooltip_fg
        self.tooltip_font = tooltip_font
        self.tooltip_padding = tooltip_padding
        self.tooltip_offset = tooltip_offset
        self.tooltip_border_color = tooltip_border_color
        self.tooltip_shadow = tooltip_shadow
        self.tooltip_radius = tooltip_radius
        self.tooltip_animation = tooltip_animation
        self.command = command
        self.tooltip: Optional[tk.Toplevel] = None
        self.tooltip_timer = None  # For delayed showing/hiding
        
        # Create button visuals
        self._create_button()
        
        # Bind events
        self._bind_events()
    
    def _create_button(self) -> None:
        """Create the button's visual elements."""
        # More subtle padding for better proportions
        padding = 2
        
        # Create outer ring for subtle border effect
        self.outer_ring = self.create_oval(
            1, 1, 
            self.winfo_reqwidth() - 1, 
            self.winfo_reqheight() - 1, 
            fill="", 
            outline="#DDDDDD", 
            width=1
        )
        
        # Create main button circle
        self.oval = self.create_oval(
            padding, padding, 
            self.winfo_reqwidth() - padding, 
            self.winfo_reqheight() - padding, 
            fill=self.button_color, 
            outline="", 
            width=0
        )
        
        # Calculate center position
        center_x = self.winfo_reqwidth() // 2
        center_y = self.winfo_reqheight() // 2
        
        # Create question mark text with slight shadow effect for depth
        self.question_mark_shadow = self.create_text(
            center_x + 1, center_y + 1, 
            text="?", 
            fill="white",  # Semi-transparent black for shadow
            font=("Microsoft YaHei", 14, "bold")
        )
        
        self.question_mark = self.create_text(
            center_x, center_y, 
            text="?", 
            fill=self.text_color,
            font=("Microsoft YaHei", 14, "bold")
        )
    
    def _bind_events(self) -> None:
        """Bind mouse events to the button."""
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
    
    def on_enter(self, event=None) -> None:
        """Handle mouse enter event."""
        # Cancel any pending hide operations
        if self.tooltip_timer:
            self.after_cancel(self.tooltip_timer)
            self.tooltip_timer = None
            
        self.itemconfig(self.oval, fill=self.button_hover_color)
        
        # Slightly delay the tooltip appearance for a more polished feel
        self.tooltip_timer = self.after(200, self.show_tooltip)
    
    def on_leave(self, event=None) -> None:
        """Handle mouse leave event."""
        # Cancel any pending show operations
        if self.tooltip_timer:
            self.after_cancel(self.tooltip_timer)
            self.tooltip_timer = None
            
        self.itemconfig(self.oval, fill=self.button_color)
        
        # Slightly delay hiding for better UX
        self.tooltip_timer = self.after(100, self.hide_tooltip)
    
    def on_press(self, event=None) -> None:
        """Handle mouse button press event."""
        # Visual feedback for button press
        self.itemconfig(self.oval, fill=self.button_press_color)
    
    def on_release(self, event=None) -> None:
        """Handle mouse button release event."""
        self.itemconfig(self.oval, fill=self.button_hover_color)
        
        # Trigger the command if provided
        if self.command is not None:
            self.command()
    
    def show_tooltip(self) -> None:
        """Display the tooltip."""
        if self.tooltip is not None:
            return

        # Wrap the text to fit the tooltip width
        wrapped_text = textwrap.fill(self.tooltip_text, width=self.tooltip_max_width)

        # Create the tooltip window
        self.tooltip = tk.Toplevel(self.parent)
        self.tooltip.overrideredirect(True)  # Remove window decorations
        
        # Make sure tooltip is on top of other windows
        self.tooltip.attributes("-topmost", True)
        
        # Set initial off-screen position to avoid flicker
        self.tooltip.wm_geometry("+0+0")
        
        # Add transparency if available (for smoother appearance)
        try:
            self.tooltip.attributes("-alpha", 0.0 if self.tooltip_animation else 1.0)
            has_alpha = True
        except:
            has_alpha = False

        # Create a frame with styled border
        frame = tk.Frame(
            self.tooltip, 
            background=self.tooltip_bg,
            borderwidth=1, 
            relief="solid",
            highlightbackground=self.tooltip_border_color,
            highlightthickness=1
        )
        
        # Add shadow effect if enabled
        if self.tooltip_shadow:
            try:
                # Try to use drop shadow if available
                frame.tk.call("wm", "attributes", self.tooltip, "-transparentcolor", "")
                frame.configure(borderwidth=2)
            except:
                # Fallback to a simple border
                pass
                
        frame.pack(fill="both", expand=True)
        
        # Create a label for the tooltip text
        label = tk.Label(
            frame, 
            text=wrapped_text, 
            background=self.tooltip_bg,
            foreground=self.tooltip_fg,
            borderwidth=0,
            font=self.tooltip_font, 
            justify="left",
            padx=self.tooltip_padding + 3,  # Extra padding for better appearance
            pady=self.tooltip_padding + 1
        )
        label.pack()

        # Calculate position after tooltip size is known
        self.tooltip.update_idletasks()
        
        # Position tooltip relative to the button
        x = self.winfo_rootx() + self.tooltip_offset[0]
        y = self.winfo_rooty() + self.tooltip_offset[1]
        
        # Adjust position if tooltip would go off screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        tooltip_width = self.tooltip.winfo_reqwidth()
        tooltip_height = self.tooltip.winfo_reqheight()
        
        if x + tooltip_width > screen_width:
            x = screen_width - tooltip_width - 10
        
        if y + tooltip_height > screen_height:
            y = self.winfo_rooty() - tooltip_height - 10  # Show above instead
            if y < 0:  # If not enough space above either
                y = 10  # Just show at top of screen
            
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        # Animate the tooltip appearance if animation is enabled
        if self.tooltip_animation and has_alpha:
            self.tooltip.deiconify()
            self._animate_tooltip_show()
        else:
            # Make tooltip visible without animation
            self.tooltip.deiconify()
            
    def _animate_tooltip_show(self, alpha=0.0):
        """Animate the tooltip appearance by gradually increasing opacity."""
        if not self.tooltip:
            return
            
        if alpha < 1.0:
            alpha += 0.1
            try:
                self.tooltip.attributes("-alpha", alpha)
                self.after(20, lambda: self._animate_tooltip_show(alpha))
            except:
                # If animation fails, just show the tooltip
                if self.tooltip:
                    self.tooltip.attributes("-alpha", 1.0)
    
    def _animate_tooltip_hide(self):
        """Animate the tooltip disappearance."""
        if not self.tooltip:
            return
            
        try:
            alpha = float(self.tooltip.attributes("-alpha"))
            if alpha > 0.1:
                alpha -= 0.1
                self.tooltip.attributes("-alpha", alpha)
                self.after(20, self._animate_tooltip_hide)
            else:
                self._destroy_tooltip()
        except:
            self._destroy_tooltip()
            
    def _destroy_tooltip(self):
        """Destroy the tooltip widget."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
    
    def hide_tooltip(self) -> None:
        """Hide the tooltip."""
        if self.tooltip:
            if self.tooltip_animation:
                try:
                    self._animate_tooltip_hide()
                except:
                    self._destroy_tooltip()
            else:
                self._destroy_tooltip()
    
    def configure(self, **kwargs) -> None:
        """Configure widget options."""
        update_visuals = False
        
        if 'tooltip_text' in kwargs:
            self.tooltip_text = kwargs.pop('tooltip_text')
        
        if 'command' in kwargs:
            self.command = kwargs.pop('command')
            
        if 'button_color' in kwargs:
            self.button_color = kwargs.pop('button_color')
            update_visuals = True
            
        if 'text_color' in kwargs:
            self.text_color = kwargs.pop('text_color')
            update_visuals = True
        
        if 'button_hover_color' in kwargs:
            self.button_hover_color = kwargs.pop('button_hover_color')
            
        if 'button_press_color' in kwargs:
            self.button_press_color = kwargs.pop('button_press_color')
        
        if update_visuals:
            self.itemconfig(self.oval, fill=self.button_color)
            self.itemconfig(self.question_mark, fill=self.text_color)
            
        super().configure(**kwargs)
        
    # Alias for configure
    config = configure
    
    def destroy(self) -> None:
        """Clean up resources when widget is destroyed."""
        # Cancel any pending timers
        if self.tooltip_timer:
            self.after_cancel(self.tooltip_timer)
        
        # Ensure tooltip is destroyed
        if self.tooltip:
            self.tooltip.destroy()
            
        super().destroy()

class ModelSettingTab:
    def __init__(self, parent, llm_config_tab: 'GUI', tab_name):
        # 主框架
        self.frame = ttk.Frame(parent)
        self.llm_config_tab = llm_config_tab
        self.tab_name = tab_name
        self.config = llm_config_tab.config
        self.config_file = llm_config_tab.config_file
        self.config_names = llm_config_tab.config_names  # LLM配置名称
        self.all_model_names = llm_config_tab.model_names  # 特定模型名称

        # 设置容器
        self.settings = []  # 存储所有SettingRow实例
        self.hover_button = None  # 确保hover_button是一个属性

        # 创建主UI
        self.create_widgets()
        self.load_settings()  # 创建标签页时加载设置

    def create_widgets(self):
        # 创建主容器，使用垂直布局，添加内边距提高美观性
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill="both", expand=True, padx=15, pady=15)

        # ===== 顶部控制区 =====
        top_section = ttk.Frame(main_container)
        top_section.pack(fill="x", pady=(0, 15))
        
        # 标题和说明 - 使用更美观的字体和间距
        title_frame = ttk.Frame(top_section)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text=f"{self.tab_name}模型设置", 
                              font=("Microsoft YaHei", 14, "bold"),
                              foreground="#333333")
        title_label.pack(side=tk.LEFT)
        
        # 添加分隔线增强视觉效果
        ttk.Separator(top_section, orient="horizontal").pack(fill="x", pady=(0, 15))
        
        # 按钮区域 - 使用更现代的布局
        button_frame = ttk.Frame(top_section)
        button_frame.pack(fill="x", pady=(0, 10))
        
        # 左侧按钮组
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=tk.LEFT)
        
        add_button = ttk.Button(left_buttons, text="➕ 新增设置", 
                             command=self.add_setting, 
                             style="ActionButton.TButton", 
                             width=12)
        add_button.pack(side=tk.LEFT, padx=(0, 10))
        
        save_button = ttk.Button(left_buttons, text="💾 保存设置", 
                              command=self.save_settings, 
                              style="Accent.TButton", 
                              width=12)
        save_button.pack(side=tk.LEFT, padx=5)
        
        # 右侧提示工具
        left_controls = ttk.Frame(button_frame)
        left_controls.pack(side=tk.LEFT)
        
        tip_text = ("程序会首先使用最高优先级下的模型：同一优先级下权重越高的模型被选中的概率越大，"
                   "当该优先级下的全部模型均超出尝试次数而失败时，程序会选择下一优先级。"
                   "当对应项未选择接入模型时，则使用默认配置，否则优先使用对应项下的配置")
        


        self.llm_hover_button = HoverButton(left_controls, tooltip_text=tip_text)
        self.llm_hover_button.pack(side="left")
        
        # ===== 标题行 =====
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill="x", pady=(0, 8))
        
        # 使用更美观的表头
        header_style = {"font": ("Microsoft YaHei", 10, "bold"), "foreground": "#333333"}
        
        # 使用Grid布局确保对齐
        header_frame.columnconfigure(0, weight=45)  # 配置列
        header_frame.columnconfigure(1, weight=25)  # 模型列
        header_frame.columnconfigure(2, weight=10)  # 权重列
        header_frame.columnconfigure(3, weight=10)  # 优先级列
        header_frame.columnconfigure(4, weight=10)  # 删除按钮列
        
        ttk.Label(header_frame, text="配置", **header_style).grid(
            row=0, column=0, sticky="w", padx=10, pady=5)
        ttk.Label(header_frame, text="模型", **header_style).grid(
            row=0, column=1, sticky="w", padx=10, pady=5)
        ttk.Label(header_frame, text="权重", **header_style).grid(
            row=0, column=2, sticky="w", padx=10, pady=5)
        ttk.Label(header_frame, text="优先级", **header_style).grid(
            row=0, column=3, sticky="w", padx=10, pady=5)
        ttk.Label(header_frame, text="操作", **header_style).grid(
            row=0, column=4, sticky="w", padx=10, pady=5)
        
        # 添加更醒目的分隔线
        separator = ttk.Separator(main_container, orient="horizontal")
        separator.pack(fill="x", pady=(0, 10))

        # ===== 创建带滚动条的条目区域 =====
        # 外层框架用于容纳Canvas和滚动条
        self.scroll_container = ttk.Frame(main_container)
        self.scroll_container.pack(fill="both", expand=True, padx=5)
        
        # 创建Canvas并设置更好的背景色和边框
        self.canvas = tk.Canvas(self.scroll_container, 
                              highlightthickness=1,
                              highlightbackground="#e0e0e0",
                              bg="#ffffff")
        self.scrollbar = ttk.Scrollbar(self.scroll_container, 
                                     orient="vertical", 
                                     command=self.canvas.yview)
        
        # 设置Canvas的yscrollcommand为自定义方法，控制滚动条显示/隐藏
        self.canvas.configure(yscrollcommand=self._scrollbar_set)
        
        # 放置Canvas
        self.canvas.pack(side="left", fill="both", expand=True)
        # 滚动条最初不要pack，让它根据内容自动控制显示
        
        # 创建内部框架来放置设置行
        self.entries_container = ttk.Frame(self.canvas, padding=5)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.entries_container, anchor="nw", width=self.canvas.winfo_width())
        
        # 绑定Canvas大小变化和entries_container大小变化事件
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.entries_container.bind("<Configure>", self._on_entries_configure)

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)  # Windows 滚轮
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)  # Linux 滚轮向上
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)  # Linux 滚轮向下
        
        # 确保滚轮绑定在整个frame及子组件上
        self._bind_mousewheel(self.frame)


    def _bind_mousewheel(self, widget):
        """递归地将鼠标滚轮事件绑定到指定组件及其所有子组件"""
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel)  # Linux 滚轮向上
        widget.bind("<Button-5>", self._on_mousewheel)  # Linux 滚轮向下
        for child in widget.winfo_children():
            self._bind_mousewheel(child)

    def _on_mousewheel(self, event):

        try:
            # 在 Windows 系统上，滚轮滚动事件的 delta 值是 120 的倍数
            if event.num == 4:  # Linux
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # Linux
                self.canvas.yview_scroll(1, "units")
            else:  # Windows
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except:
            pass
    def create_tooltip(self, widget, text):
        """为组件创建一个简单的工具提示"""
        def enter(event):
            # 创建工具提示窗口
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # 创建工具提示顶级窗口
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)  # 无边框窗口
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            # 创建工具提示内容
            label = ttk.Label(self.tooltip, text=text, justify='left',
                           background="#ffffaa", relief="solid", borderwidth=1,
                           wraplength=350, padding=(10, 5))
            label.pack()
            
        def leave(event):
            # 销毁工具提示窗口
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def _scrollbar_set(self, first, last):
        """
        自定义滚动条设置方法，根据内容决定是否显示滚动条
        """
        # 调用滚动条的set方法更新滚动位置
        self.scrollbar.set(first, last)
        
        # 判断是否需要显示滚动条
        if float(first) <= 0.0 and float(last) >= 1.0:
            # 内容完全可见，隐藏滚动条
            self.scrollbar.pack_forget()
        else:
            # 内容超出可见范围，显示滚动条
            if not self.scrollbar.winfo_ismapped():
                self.scrollbar.pack(side="right", fill="y")
    
    def _on_canvas_configure(self, event):
        """当Canvas大小变化时调整内部框架宽度并检查滚动条状态"""
        # 更新内部框架的宽度以匹配Canvas
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        
        # 每当Canvas大小变化时，也检查是否需要滚动条
        self.entries_container.update_idletasks()  # 确保尺寸更新
        entries_height = self.entries_container.winfo_reqheight()
        canvas_height = event.height
        
        # 更新滚动条状态
        if entries_height <= canvas_height:
            # 内容完全适合，隐藏滚动条
            self.scrollbar.pack_forget()
        else:
            # 内容超出范围，显示滚动条
            if not self.scrollbar.winfo_ismapped():
                self.scrollbar.pack(side="right", fill="y")
        
    def _on_entries_configure(self, event):
        """当内部框架大小变化时更新Canvas滚动区域并检查是否需要滚动条"""
        # 更新Canvas的滚动区域以包含所有内容
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 检查内容高度与Canvas高度的关系
        entries_height = self.entries_container.winfo_reqheight()
        canvas_height = self.canvas.winfo_height()
        
        # 更新滚动条状态
        if entries_height <= canvas_height:
            # 内容完全适合，隐藏滚动条
            self.scrollbar.pack_forget()
        else:
            # 内容超出范围，显示滚动条
            if not self.scrollbar.winfo_ismapped():
                self.scrollbar.pack(side="right", fill="y")
        
    def add_setting(self):
        # 保持原有代码...
        setting = SettingRow(self.entries_container, self, len(self.settings) + 1)
        self.settings.append(setting)
        
        # 设置交替背景颜色
        if len(self.settings) % 2 == 0:
            setting.frame.configure(style="EvenRow.TFrame")
        else:
            setting.frame.configure(style="OddRow.TFrame")
        
        setting.frame.pack(fill="x", pady=1)
        
        # 确保滚动区域更新以显示新添加的设置行
        self.entries_container.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 滚动到底部以显示新添加的行
        self.canvas.yview_moveto(1.0)
        
        # 添加完新行后，重新检查是否需要显示滚动条
        entries_height = self.entries_container.winfo_reqheight()
        canvas_height = self.canvas.winfo_height()
        if entries_height > canvas_height:
            if not self.scrollbar.winfo_ismapped():
                self.scrollbar.pack(side="right", fill="y")


    def delete_setting(self, setting_row_to_delete):
        # 原有代码不变...
        try:
            index_to_delete = -1
            for i, setting in enumerate(self.settings):
                if setting is setting_row_to_delete:
                    index_to_delete = i
                    break
                    
            if index_to_delete != -1:
                setting_row_to_delete.destroy()
                self.settings.pop(index_to_delete)
                
                # 更新交替背景
                for i, setting in enumerate(self.settings):
                    if i % 2 == 0:
                        setting.frame.configure(style="EvenRow.TFrame")
                    else:
                        setting.frame.configure(style="OddRow.TFrame")
                        
                # 更新滚动区域
                self.entries_container.update_idletasks()
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                
                # 删除行后检查是否还需要滚动条
                entries_height = self.entries_container.winfo_reqheight()
                canvas_height = self.canvas.winfo_height()
                if entries_height <= canvas_height:
                    self.scrollbar.pack_forget()
            else:
                print(f"警告：要删除的SettingRow在 {self.tab_name} 标签中未找到")
        except Exception as e:
            print(f"删除设置行时出错: {e}")
            self.llm_config_tab.show_message_bubble("Error", f"删除设置时出错: {e}")

    def save_settings(self):
        """将内部列表中的设置保存到配置文件"""
        settings_data = []
        # 遍历设置对象的整个列表
        for setting_index, setting in enumerate(self.settings):
            weight_str = setting.weight_var.get()
            priority_str = setting.priority_var.get()
            config_val = setting.config_var.get()
            model_val = setting.model_var.get()

            # 基本验证
            if not config_val:
                self.llm_config_tab.show_message_bubble("Error", f"配置项不能为空 (行: {setting_index + 1})")
                return
            if not model_val:
                self.llm_config_tab.show_message_bubble("Error", f"模型项不能为空 (行: {setting_index + 1})")
                return
            if not weight_str or not setting.validate_positive_int(weight_str, internal_call=True):
                self.llm_config_tab.show_message_bubble("Error", f"权重必须是正整数 (行: {setting_index + 1})")
                return
            if not priority_str or not setting.validate_nature_int(priority_str, internal_call=True):
                self.llm_config_tab.show_message_bubble("Error", f"优先级必须是非负整数 (行: {setting_index + 1})")
                return

            try:
                settings_data.append({
                    "config": config_val,
                    "model": model_val,
                    "weigh": int(weight_str),
                    "priority": int(priority_str)
                })
            except ValueError:
                # 这理想情况下应该被上面的验证捕获，但作为后备
                self.llm_config_tab.show_message_bubble("Error", f"权重或优先级格式无效 (行: {setting_index + 1})")
                return

        # 直接保存为字典列表
        try:
            if "模型" not in self.config: self.config["模型"] = {}  # 确保基础键存在
            self.config["模型"][self.tab_name + "_setting"] = settings_data
            self.llm_config_tab.save_config()
            self.llm_config_tab.show_message_bubble("Success", f"{self.tab_name} 设置已保存！")
        except Exception as e:
            self.llm_config_tab.show_message_bubble("Error", f"保存 {self.tab_name} 设置时出错: {e}")

    def load_settings(self):
        # 大部分原有代码不变...
        self.settings.clear()
        for widget in self.entries_container.winfo_children():
            widget.destroy()

        try:
            # 加载设置代码...
            if "模型" not in self.config: self.config["模型"] = {}
            settings_data = self.config["模型"].get(self.tab_name + "_setting", [])
            # 排序和数据格式验证代码...
            
            for i, data in enumerate(settings_data):
                setting = SettingRow(self.entries_container, self, len(self.settings) + 1,
                                   config_value=data.get("config", ""),
                                   model_value=data.get("model", ""),
                                   weight_value=str(data.get("weigh", "1")),
                                   priority_value=str(data.get("priority", "0")))
                                   
                # 设置交替背景颜色
                if i % 2 == 0:
                    setting.frame.configure(style="EvenRow.TFrame")
                else:
                    setting.frame.configure(style="OddRow.TFrame")
                
                self.settings.append(setting)
                setting.frame.pack(fill="x", pady=1)

        except Exception as e:
            self.llm_config_tab.show_message_bubble("Error", f"加载 {self.tab_name} 设置时出错: {e}")
            print("Error", f"加载 {self.tab_name} 设置时出错: {e}")

        # 确保滚动区域更新
        self.entries_container.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 加载完成后检查是否需要滚动条
        def check_scrollbar_need():
            entries_height = self.entries_container.winfo_reqheight()
            canvas_height = self.canvas.winfo_height()
            if entries_height <= canvas_height:
                # 内容完全适合，隐藏滚动条
                self.scrollbar.pack_forget()
            else:
                # 内容超出范围，显示滚动条
                if not self.scrollbar.winfo_ismapped():
                    self.scrollbar.pack(side="right", fill="y")
        
        # 稍微延迟检查，确保所有尺寸计算准确
        self.frame.after(100, check_scrollbar_need)
        



# --- Modified SettingRow Class (No changes needed from previous refinement) ---
class SettingRow:
    # Note: row_num is now just for logical tracking if needed, not for gridding
    def __init__(self, parent_container, model_setting_tab, row_num,
                 config_value="", model_value="", weight_value="1", priority_value="0"):

        self.parent_container = parent_container # The container where this row's frame will eventually be packed
        self.model_setting_tab = model_setting_tab
        self.row_num = row_num # Logical row number
        self.config_names = model_setting_tab.config_names # LLM Config names (main dropdown)
        # Use the specific model names passed from the main GUI class
        self.all_model_names = model_setting_tab.all_model_names
        self.llm_config_tab = model_setting_tab.llm_config_tab

        # The main frame for this row, its parent is the entries_container passed in
        self.frame = ttk.Frame(parent_container)
        # DO NOT grid/pack self.frame here - it's handled by _update_model_setting_pagination

        # --- Widgets inside self.frame ---
        # Use grid within this specific row's frame for alignment
        col_weight_config = 3
        col_weight_model = 4
        col_weight_entry = 1
        col_weight_delete = 1

        self.frame.columnconfigure(0, weight=col_weight_config)
        self.frame.columnconfigure(1, weight=col_weight_model)
        self.frame.columnconfigure(2, weight=col_weight_entry)
        self.frame.columnconfigure(3, weight=col_weight_entry)
        self.frame.columnconfigure(4, weight=col_weight_delete)

        # Config Dropdown (LLM Config Name)
        self.config_var = tk.StringVar(value=config_value)
        self.config_dropdown = ttk.Combobox(self.frame, textvariable=self.config_var,
                                            values=self.config_names, state="readonly", width=15) # Adjusted width
        self.config_dropdown.grid(row=0, column=0, padx=(0, 5), pady=1, sticky="ew") # Sticky ew
        self.config_dropdown.bind("<<ComboboxSelected>>", self.clear_selection)
        self.config_dropdown.bind("<Button-1>", self.clear_selection) # Added Button-1 binding

        # Model Dropdown (Specific Model Name like gpt-4)
        self.model_var = tk.StringVar(value=model_value)
        self.model_dropdown = ttk.Combobox(self.frame, textvariable=self.model_var,
                                           values=self.all_model_names, state="readonly", width=20) # Adjusted width
        self.model_dropdown.grid(row=0, column=1, padx=5, pady=1, sticky="ew") # Sticky ew
        self.model_dropdown.bind("<<ComboboxSelected>>", self.clear_selection)
        self.model_dropdown.bind("<Button-1>", self.clear_selection) # Added Button-1 binding

        # Weight Entry
        self.weight_var = tk.StringVar(value=str(weight_value)) # Ensure string
        self.weight_entry = tk.Entry(self.frame, textvariable=self.weight_var, width=5) # Reduced width
        self.weight_entry.grid(row=0, column=2, padx=5, pady=1, sticky="ew") # Sticky ew
        self.weight_entry.config(validate="key", validatecommand=(self.frame.register(self.validate_positive_int), '%P'))

        # Priority Entry
        self.priority_var = tk.StringVar(value=str(priority_value)) # Ensure string
        self.priority_entry = tk.Entry(self.frame, textvariable=self.priority_var, width=5) # Reduced width
        self.priority_entry.grid(row=0, column=3, padx=5, pady=1, sticky="ew") # Sticky ew
        self.priority_entry.config(validate="key", validatecommand=(self.frame.register(self.validate_nature_int), '%P'))

        # Delete Button
        self.delete_button = ttk.Button(self.frame, text="🗑 删除", command=self.delete,
                                   bootstyle="danger", width=5) # Added width
        self.delete_button.grid(row=0, column=4, padx=(5,0), pady=1, sticky="ew") # Sticky ew
        
        self.config_dropdown.bind("<MouseWheel>", lambda event: "break")
        self.model_dropdown.bind("<MouseWheel>", lambda event: "break")
        

    def delete(self):
        """Calls the parent tab's delete method, passing self."""
        self.model_setting_tab.delete_setting(self)

    def destroy(self):
        """Destroys the frame and its children."""
        self.frame.destroy()

    def update_row_num(self):
        """No longer needed for pack layout"""
        pass

    def clear_selection(self, event=None):
        # Use the method from the main GUI class passed down
        self.llm_config_tab.clear_dropdown_selection(event)

    # Keep validation methods within the class that uses them for registration
    def validate_positive_int(self, new_value, internal_call=False):
        if new_value == "":
            return True
        try:
            value = int(new_value)
            is_valid = value > 0
            if not internal_call and self.weight_entry.winfo_exists(): # Check if widget exists
                self.weight_entry.config(foreground="black" if is_valid else "red")
            return is_valid
        except ValueError:
            if not internal_call and self.weight_entry.winfo_exists():
                self.weight_entry.config(foreground="red")
            return False
        except tk.TclError: # Handle error if widget is destroyed during validation
            return False

    def validate_nature_int(self, new_value, internal_call=False):
        if new_value == "":
            return True
        try:
            value = int(new_value)
            is_valid = value >= 0
            if not internal_call and self.priority_entry.winfo_exists(): # Check if widget exists
                self.priority_entry.config(foreground="black" if is_valid else "red")
            return is_valid
        except ValueError:
            if not internal_call and self.priority_entry.winfo_exists():
                self.priority_entry.config(foreground="red")
            return False
        except tk.TclError: # Handle error if widget is destroyed during validation
            return False



class PromptConfigTab:
    def __init__(self, parent, llm_config_tab):
        self.frame = ttk.Frame(parent)
        self.llm_config_tab = llm_config_tab
        self.config = llm_config_tab.config
        self.config_file = llm_config_tab.config_file
        
        # 添加变量跟踪当前选择
        self.current_kind_var = tk.StringVar()
        self.current_id_var = tk.StringVar()
        
        # 设置颜色和样式
        self.bg_color = "#f7f7f7"
        self.accent_color = "#3498db"
        self.hover_color = "#2980b9"
        
        self.create_widgets()
        self.load_prompt_settings()

    def create_widgets(self):
        """创建提示词配置标签页的小部件"""
        # 设置提示词类型和对应数量的数据
        self.kind_number_data = [
            {"kind": "大纲", "number": 6},
            {"kind": "选项", "number": 6},
            {"kind": "故事开头", "number": 6},
            {"kind": "故事继续", "number": 6},
            {"kind": "故事结尾", "number": 6},
            {"kind": "全部人物绘画", "number": 2},
            {"kind": "单个人物绘画", "number": 2},
            {"kind": "故事地点绘画", "number": 2},
            {"kind": "背景音乐生成", "number": 2},
            {"kind": "开头音乐生成", "number": 6},
            {"kind": "结尾音乐生成", "number": 6},
            {"kind": "故事总结", "number": 6},
            {"kind": "本地导入", "number": 6},
            {"kind": "重写提示词", "number": 1},
            {"kind": "首页背景生成", "number": 2},
            {"kind": "翻译", "number": 6}
        ]
        
        # 创建主容器，采用垂直布局
        main_container = ttk.Frame(self.frame, padding="15 10")
        main_container.pack(fill="both", expand=True)
        
        # ===== 标题区域 =====
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text="提示词管理", font=("Microsoft YaHei", 16, "bold"))
        title_label.pack(side="left")
        
        subtitle_label = ttk.Label(title_frame, text="配置不同场景的AI提示词模板", 
                                  font=("Microsoft YaHei", 10))
        subtitle_label.pack(side="left", padx=(15, 0), pady=(5, 0))
        
        # ===== 控制按钮区 =====
        control_frame = ttk.Frame(main_container)
        control_frame.pack(fill="x", pady=(0, 15))
        
        # 左侧 - 操作按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side="left")
        
        # 导入按钮
        import_button = ttk.Button(
            button_frame, 
            text="📥 导入提示词", 
            command=self.import_prompt_config,
            width=15
        )
        import_button.pack(side="left", padx=(0, 10))
        
        # 导出按钮
        export_button = ttk.Button(
            button_frame, 
            text="📤 导出提示词", 
            command=self.export_prompt_config,
            width=15
        )
        export_button.pack(side="left", padx=10)
        
        # 保存按钮
        save_button = ttk.Button(
            button_frame, 
            text="💾 保存配置", 
            command=self.save_prompt_config,
            style="Accent.TButton",
            width=12
        )
        save_button.pack(side="left", padx=10)
        
        # 测试按钮
        test_button = ttk.Button(
            button_frame, 
            text="🔍 测试提示词", 
            command=self.test_prompt,
            width=15
        )
        test_button.pack(side="left", padx=10)
        
        # ===== 选择器区域 =====
        selector_frame = ttk.LabelFrame(main_container, text="选择提示词", padding=(15, 10))
        selector_frame.pack(fill="x", pady=(0, 15))
        
        # 采用网格布局保持对齐
        selector_grid = ttk.Frame(selector_frame)
        selector_grid.pack(fill="x", pady=5)
        
        # 提示词类型选择
        ttk.Label(selector_grid, text="提示词类型:", 
                font=("Microsoft YaHei", 10, "bold")).grid(row=0, column=0, padx=(0, 10), pady=5, sticky="e")
        
        self.kind_var = tk.StringVar()
        self.kind_dropdown = ttk.Combobox(
            selector_grid, 
            textvariable=self.kind_var,
            values=[item["kind"] for item in self.kind_number_data], 
            state="readonly",
            width=20
        )
        self.kind_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.kind_dropdown.bind("<<ComboboxSelected>>", self.update_id_dropdown)
        
        # 编号选择
        ttk.Label(selector_grid, text="提示词编号:", 
                font=("Microsoft YaHei", 10, "bold")).grid(row=0, column=2, padx=(20, 10), pady=5, sticky="e")
        
        self.id_var = tk.StringVar()
        self.id_dropdown = ttk.Combobox(
            selector_grid, 
            textvariable=self.id_var, 
            values=[], 
            state="readonly",
            width=10
        )
        self.id_dropdown.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.id_dropdown.bind("<<ComboboxSelected>>", self.load_prompt_content)
        
        # ===== 编辑区域 =====
        editor_frame = ttk.LabelFrame(main_container, text="编辑提示词", padding=(15, 10))
        editor_frame.pack(fill="both", expand=True)
        
        # 提示文本
        hint_text = ("在此编辑提示词模板。您可以使用变量 {variable_name} 来表示需要在运行时替换的值。"
                    "提示词应当简明扼要，明确指示AI需要执行的任务和期望的输出格式。")
        
        hint_label = ttk.Label(editor_frame, text=hint_text, wraplength=600, 
                             foreground="gray", justify="left")
        hint_label.pack(fill="x", pady=(0, 10))
        
        # 创建文本编辑框和滚动条
        text_frame = ttk.Frame(editor_frame)
        text_frame.pack(fill="both", expand=True)
        
        # 垂直滚动条
        scrollbar_y = ttk.Scrollbar(text_frame, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")
        
        # 水平滚动条
        scrollbar_x = ttk.Scrollbar(text_frame, orient="horizontal")
        scrollbar_x.pack(side="bottom", fill="x")
        
        # 创建具有行号的文本编辑框
        self.prompt_text = Text(
            text_frame, 
            wrap="none",  # 允许水平滚动
            width=80, 
            height=20,
            font=("Consolas", 10),  # 使用等宽字体
            undo=True,  # 启用撤销功能
            padx=5,
            pady=5,
            bg="#ffffff",  # 白色背景
            fg="#333333",  # 深灰色文本
            insertbackground="#333333",  # 光标颜色
            selectbackground="#a0c8e8",  # 选择颜色
            xscrollcommand=scrollbar_x.set,
            yscrollcommand=scrollbar_y.set
        )
        self.prompt_text.pack(side="left", fill="both", expand=True)
        
        # 配置滚动条
        scrollbar_y.config(command=self.prompt_text.yview)
        scrollbar_x.config(command=self.prompt_text.xview)
        
        # 添加文本编辑键盘快捷键
        self.prompt_text.bind("<Control-a>", self._select_all)
        self.prompt_text.bind("<Control-z>", self._undo)
        self.prompt_text.bind("<Control-y>", self._redo)
        
        # ===== 状态栏 =====
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill="x", pady=(10, 0))
        
        # 左侧状态信息
        self.status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side="left")
        
        # 右侧帮助提示
        help_label = ttk.Label(
            status_frame, 
            text="提示: Ctrl+Z 撤销, Ctrl+Y 重做, Ctrl+A 全选", 
            foreground="gray"
        )
        help_label.pack(side="right")

    def _select_all(self, event=None):
        """全选文本"""
        self.prompt_text.tag_add("sel", "1.0", "end")
        return "break"
    
    def _undo(self, event=None):
        """撤销操作"""
        try:
            self.prompt_text.edit_undo()
        except:
            pass
        return "break"
    
    def _redo(self, event=None):
        """重做操作"""
        try:
            self.prompt_text.edit_redo()
        except:
            pass
        return "break"

    def test_prompt(self):
        """测试提示词，并在新窗口中显示结果"""
        self.save_current_prompt()  # 先保存当前编辑的提示词
        
        kind = self.kind_var.get()
        if not kind:
            self.llm_config_tab.show_message_bubble("Error", "没有选中对应的提示词")
            return
        
        self.status_var.set("正在测试提示词...")
        
        try:
            a, b = handle_prompt.process_prompt(kind)  # 调用函数
            self.open_result_window(a, b)  # 打开结果窗口
            self.status_var.set("测试完成")
        except Exception as e:
            self.llm_config_tab.show_message_bubble("Error", f"测试失败: {str(e)}")
            self.status_var.set("测试失败")

    def open_result_window(self, a, b):
        """打开显示测试结果的窗口"""
        new_window = Toplevel(self.frame)
        new_window.withdraw()  # 创建后立即隐藏
        new_window.title("提示词测试结果")
        new_window.resizable(True, True)  # 允许调整大小
        new_window.grab_set()
        new_window.focus_set()
        new_window.transient(self.frame)
        
        # 获取屏幕宽度和高度
        screen_width = new_window.winfo_screenwidth()
        screen_height = new_window.winfo_screenheight()
        
        # 计算窗口位置
        window_width = 800
        window_height = 600
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 创建主容器
        main_frame = ttk.Frame(new_window, padding=15)
        main_frame.pack(fill="both", expand=True)
        
        # 创建标题
        title_label = ttk.Label(
            main_frame, 
            text="提示词测试结果", 
            font=("Microsoft YaHei", 14, "bold")
        )
        title_label.pack(pady=(0, 15))
        
        # 创建笔记本，用选项卡显示结果
        result_tabs = ttk.Notebook(main_frame)
        result_tabs.pack(fill="both", expand=True)
        
        # 提示词1选项卡
        tab1 = ttk.Frame(result_tabs, padding=10)
        result_tabs.add(tab1, text="提示词1")
        
        # 文本框与滚动条
        tab1_frame = ttk.Frame(tab1)
        tab1_frame.pack(fill="both", expand=True)
        
        scroll1_y = ttk.Scrollbar(tab1_frame, orient="vertical")
        scroll1_y.pack(side="right", fill="y")
        
        scroll1_x = ttk.Scrollbar(tab1_frame, orient="horizontal")
        scroll1_x.pack(side="bottom", fill="x")
        
        a_text = Text(
            tab1_frame,
            wrap="none",
            font=("Consolas", 10),
            padx=5,
            pady=5,
            bg="#ffffff",
            xscrollcommand=scroll1_x.set,
            yscrollcommand=scroll1_y.set
        )
        a_text.pack(side="left", fill="both", expand=True)
        a_text.insert(tk.END, a)
        a_text.config(state=tk.DISABLED)
        
        scroll1_y.config(command=a_text.yview)
        scroll1_x.config(command=a_text.xview)
        
        # 提示词2选项卡
        tab2 = ttk.Frame(result_tabs, padding=10)
        result_tabs.add(tab2, text="提示词2")
        
        # 文本框与滚动条
        tab2_frame = ttk.Frame(tab2)
        tab2_frame.pack(fill="both", expand=True)
        
        scroll2_y = ttk.Scrollbar(tab2_frame, orient="vertical")
        scroll2_y.pack(side="right", fill="y")
        
        scroll2_x = ttk.Scrollbar(tab2_frame, orient="horizontal")
        scroll2_x.pack(side="bottom", fill="x")
        
        b_text = Text(
            tab2_frame,
            wrap="none",
            font=("Consolas", 10),
            padx=5,
            pady=5,
            bg="#ffffff",
            xscrollcommand=scroll2_x.set,
            yscrollcommand=scroll2_y.set
        )
        b_text.pack(side="left", fill="both", expand=True)
        b_text.insert(tk.END, b)
        b_text.config(state=tk.DISABLED)
        
        scroll2_y.config(command=b_text.yview)
        scroll2_x.config(command=b_text.xview)
        
        # 底部按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(15, 0))
        
        close_button = ttk.Button(
            button_frame, 
            text="关闭", 
            command=new_window.destroy,
            width=10
        )
        close_button.pack(side="right")
        
        copy_button = ttk.Button(
            button_frame, 
            text="复制当前选项卡内容", 
            command=lambda: self._copy_tab_content(result_tabs, a_text, b_text),
            width=20
        )
        copy_button.pack(side="right", padx=10)
        
        # 设置窗口位置和大小
        new_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        new_window.update_idletasks()
        
        # 显示窗口
        new_window.deiconify()
        new_window.wait_window(new_window)

    def _copy_tab_content(self, notebook, text1, text2):
        """复制当前选项卡的内容"""
        current_tab = notebook.index(notebook.select())
        text_widget = text1 if current_tab == 0 else text2
        
        # 保存当前文本到剪贴板
        self.frame.clipboard_clear()
        self.frame.clipboard_append(text_widget.get("1.0", tk.END))
        
        # 显示消息
        self.llm_config_tab.show_message_bubble("Success", "内容已复制到剪贴板")

    def export_prompt_config(self):
        """将提示词配置导出到JSON文件"""
        # 先保存当前编辑的提示词
        self.save_current_prompt()
        
        # 加载完整的提示词配置
        prompt_config = self.load_prompt_settings()
        
        # 打开文件对话框选择导出路径
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            title="导出提示词配置"
        )
        
        if not filepath:
            return
            
        try:
            # 使用缩进格式化JSON以提高可读性
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(prompt_config, f, indent=4, ensure_ascii=False)
                
            self.llm_config_tab.show_message_bubble("Success", f"提示词导出成功: {filepath}")
            self.status_var.set(f"导出成功: {os.path.basename(filepath)}")
            
        except Exception as e:
            self.llm_config_tab.show_message_bubble("Error", f"导出错误: {e}")
            self.status_var.set("导出失败")

    def import_prompt_config(self):
        """从JSON文件导入提示词配置"""
        # 打开文件对话框选择导入路径
        filepath = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            title="导入提示词配置"
        )
        
        if not filepath:
            return
            
        try:
            # 从文件中读取JSON数据
            with open(filepath, "r", encoding="utf-8") as f:
                imported_config = json.load(f)
                
            # 验证导入的数据
            if not isinstance(imported_config, list):
                raise ValueError("无效的JSON格式：应为列表。")
                
            for item in imported_config:
                if not isinstance(item, dict) or "kind" not in item or "content" not in item:
                    raise ValueError("无效的JSON格式：每个项目必须是包含'kind'和'content'键的字典。")
                    
            # 将导入的数据保存到配置中
            self.config["提示词"] = imported_config
            self.llm_config_tab.save_config()  # 保存
            
            # 更新UI
            self.load_prompt_settings()  # 重新加载设置
            self.update_id_dropdown()  # 更新下拉菜单
            self.save_current_prompt()
            
            self.llm_config_tab.show_message_bubble("Success", f"提示词已从 {filepath} 导入")
            self.status_var.set(f"导入成功: {os.path.basename(filepath)}")
            
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.llm_config_tab.show_message_bubble("Error", f"文件错误: {e}")
            self.status_var.set("导入失败: 文件错误")
        except ValueError as e:
            self.llm_config_tab.show_message_bubble("Error", f"数据格式错误: {e}")
            self.status_var.set("导入失败: 格式错误")
        except Exception as e:
            self.llm_config_tab.show_message_bubble("Error", f"导入错误: {e}")
            self.status_var.set("导入失败")

    def update_id_dropdown(self, event=None):
        """根据所选类型更新ID下拉菜单"""
        self.save_current_prompt()  # 更改前保存
        selected_kind = self.kind_var.get()
        
        # 清除combobox选择高亮
        try:
            if event and hasattr(event, "widget"):
                event.widget.selection_clear()
        except:
            pass
            
        for item in self.kind_number_data:
            if item["kind"] == selected_kind:
                num_prompts = item["number"]
                id_values = [str(i) for i in range(1, num_prompts + 1)]
                self.id_dropdown['values'] = id_values
                
                if id_values:
                    self.id_var.set(id_values[0])  # 选择第一个ID
                    self.load_prompt_content()  # 加载内容
                else:
                    self.id_var.set("")
                    self.prompt_text.delete("1.0", tk.END)  # 清空文本区域
                    
                self.current_kind_var.set(selected_kind)
                self.current_id_var.set(self.id_var.get())
                
                self.status_var.set(f"已选择: {selected_kind} - {self.id_var.get()}")
                return

    def load_prompt_content(self, event=None):
        """从配置文件加载提示词内容"""
        self.save_current_prompt()  # 更改前保存
        selected_kind = self.kind_var.get()
        selected_id = self.id_var.get()
        
        # 清除combobox选择高亮
        try:
            if event and hasattr(event, "widget"):
                event.widget.selection_clear()
        except:
            pass
        
        if not selected_kind or not selected_id:
            self.prompt_text.delete("1.0", tk.END)  # 清空文本区域
            self.current_kind_var.set("")
            self.current_id_var.set("")
            return
            
        prompt_config = self.load_prompt_settings()
        found = False
        
        for kind_config in prompt_config:
            if kind_config["kind"] == selected_kind:
                for content in kind_config["content"]:
                    if content["id"] == selected_id:
                        self.prompt_text.delete("1.0", tk.END)  # 清除现有文本
                        self.prompt_text.insert("1.0", content["prompt"])  # 插入加载的文本
                        found = True
                        break
                if found:
                    break
        
        # 如果未找到提示词，清空文本区域
        if not found:
            self.prompt_text.delete("1.0", tk.END)
            
        self.current_kind_var.set(selected_kind)
        self.current_id_var.set(selected_id)
        self.status_var.set(f"已加载: {selected_kind} - {selected_id}")

    def save_current_prompt(self):
        """将当前提示词保存到配置文件"""
        selected_kind = self.current_kind_var.get()
        selected_id = self.current_id_var.get()
        prompt_content = self.prompt_text.get("1.0", tk.END).strip()
        
        if not selected_kind or not selected_id:
            return  # 无需保存
            
        # 加载现有提示词配置
        prompt_config = self.load_prompt_settings()
        
        # 查找种类，如果存在，否则创建它
        kind_found = False
        for kind_config in prompt_config:
            if kind_config["kind"] == selected_kind:
                kind_found = True
                # 查找提示词，如果存在，否则创建它
                id_found = False
                for content in kind_config["content"]:
                    if content["id"] == selected_id:
                        content["prompt"] = prompt_content
                        id_found = True
                        break
                if not id_found:
                    kind_config["content"].append({"id": selected_id, "prompt": prompt_content})
                break  # 已找到种类，退出循环
        if not kind_found:
            # 未找到种类，创建种类和提示词
            prompt_config.append({
                "kind": selected_kind,
                "content": [{"id": selected_id, "prompt": prompt_content}]
            })
            
        # 保存提示词配置
        try:
            self.config["提示词"] = prompt_config  # 更新配置字典
            self.llm_config_tab.save_config()  # 保存更改到文件
            return True
        except Exception as e:
            self.llm_config_tab.show_message_bubble("Error", f"保存错误: {e}")
            return False

    def save_prompt_config(self):
        """保存提示词配置到配置文件"""
        if self.save_current_prompt():
            self.llm_config_tab.show_message_bubble("Success", "提示词配置已保存！")
            self.status_var.set("配置已保存")

    def load_prompt_settings(self):
        """从配置文件加载提示词配置"""
        try:
            prompt_config = self.config.get("提示词", [])
            return prompt_config
        except KeyError:
            # 处理配置中缺少'提示词'键的情况
            return []
        except Exception as e:
            self.llm_config_tab.show_message_bubble("Error", f"加载提示词配置出错: {e}")
            print("Error", f"加载提示词配置出错: {e}")
            return []



class ModelSelectionDialog(Toplevel):
    def __init__(self, parent, all_models, existing_models):
        super().__init__(parent)
        self.withdraw()  # Create hidden first
        self.title("选择需要导入的模型")
        
        # Configure theme and style
        self.configure(padx=10, pady=10)
        
        # Initialize variables
        self.result = None
        self.all_models = all_models
        self.existing_models = existing_models
        self.selections = {}
        self.tooltips = []  # Store tooltip objects
        self.page_size = 36
        self.current_page = 0
        self.num_cols = 3
        self.num_rows = 12
        self.max_text_length = 40  # Maximum length for displayed text
        
        # Initialize selection variables
        for model in self.all_models:
            is_existing = model in self.existing_models
            self.selections[model] = tk.BooleanVar(value=is_existing)

        self.filtered_models = self.all_models
        self.update_total_pages()
        self.create_widgets()

        # Position and display
        self.adjust_dialog_size()
        self.place_window_center()
        self.update_idletasks()
        self.deiconify()  # Show after positioning

    def create_widgets(self):
        """Creates the widgets for model selection, including pagination and filtering."""
        # Main container frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True)
        
        # Title frame
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 10))
        
        title_label = ttk.Label(title_frame, text="选择模型", font=("", 12, "bold"))
        title_label.pack(side="left")
        
        # Filter frame
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill="x", pady=(0, 10))
        
        filter_label = ttk.Label(filter_frame, text="筛选:")
        filter_label.pack(side="left", padx=(0, 5))
        
        self.filter_entry = ttk.Entry(filter_frame)
        self.filter_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.filter_entry.bind("<Return>", lambda e: self.apply_filter())
        
        filter_button = ttk.Button(filter_frame, text="筛选", command=self.apply_filter)
        filter_button.pack(side="left")
        
        # Page navigation frame
        page_frame = ttk.Frame(main_frame)
        page_frame.pack(fill="x", pady=(0, 10))
        
        page_label = ttk.Label(page_frame, text="页面:")
        page_label.pack(side="left", padx=(0, 5))
        
        self.page_var = tk.StringVar()
        self.page_var.set(self.get_page_label(self.current_page))
        self.page_labels = [self.get_page_label(i) for i in range(self.total_pages)]
        
        self.page_dropdown = ttk.Combobox(page_frame, textvariable=self.page_var, 
                                          values=self.page_labels, state="readonly", width=30)
        self.page_dropdown.pack(side="left", fill="x", expand=True)
        self.page_dropdown.bind("<<ComboboxSelected>>", self.on_page_change)
        
        # Navigation buttons
        nav_frame = ttk.Frame(page_frame)
        nav_frame.pack(side="right")
        
        prev_button = ttk.Button(nav_frame, text="上一页", command=self.prev_page,
                                width=8)
        prev_button.pack(side="left", padx=2)
        
        next_button = ttk.Button(nav_frame, text="下一页", command=self.next_page,
                                width=8)
        next_button.pack(side="left", padx=2)

        # Checkbutton Frame with a clean separator above and below
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=5)
        
        self.checkbutton_frame = ttk.Frame(main_frame)
        self.checkbutton_frame.pack(fill="both", expand=True, pady=10)
        
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=5)

        # Selection options
        select_frame = ttk.Frame(main_frame)
        select_frame.pack(fill="x", pady=(0, 10))
        
        select_all = ttk.Button(select_frame, text="全选", command=self.select_all, width=10)
        select_all.pack(side="left", padx=2)
        
        deselect_all = ttk.Button(select_frame, text="取消全选", command=self.deselect_all, width=10)
        deselect_all.pack(side="left", padx=2)
        
        # Button Frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(5, 0))
        
        # Right-aligned buttons
        button_container = ttk.Frame(button_frame)
        button_container.pack(side="right")
        
        cancel_button = ttk.Button(button_container, text="取消", command=self.on_cancel, width=10)
        cancel_button.pack(side="right", padx=5)
        
        ok_button = ttk.Button(button_container, text="确定", command=self.on_ok, width=10)
        ok_button.pack(side="right", padx=5)
        
        # Initialize checkbuttons
        self.update_checkbuttons()

    def truncate_text(self, text):
        """Truncate text if longer than max_text_length"""
        if len(text) > self.max_text_length:
            return text[:self.max_text_length] + "..."
        return text

    def create_tooltip(self, widget, text):
        """Create tooltip for a widget"""
        # Store tooltip info to prevent garbage collection
        tooltip_id = None
        
        def enter(event):
            nonlocal tooltip_id
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Create tooltip window
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            label = ttk.Label(tooltip, text=text, background="#FFFFDD", 
                             relief="solid", borderwidth=1, padding=(5, 2))
            label.pack()
            
            tooltip_id = tooltip
            
        def leave(event):
            nonlocal tooltip_id
            if tooltip_id:
                tooltip_id.destroy()
                tooltip_id = None
                
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
        self.tooltips.append((widget, text))  # Keep reference to prevent garbage collection

    def update_checkbuttons(self):
        """Updates the checkbuttons displayed based on the current page."""
        # Clear existing checkbuttons and tooltips
        for widget in self.checkbutton_frame.winfo_children():
            widget.destroy()
        self.tooltips = []

        start_index = self.current_page * self.page_size
        end_index = min(start_index + self.page_size, len(self.filtered_models))
        
        # Create checkbutton grid
        for i in range(self.num_rows):
            self.checkbutton_frame.grid_rowconfigure(i, weight=1)
            
        for i in range(self.num_cols):
            self.checkbutton_frame.grid_columnconfigure(i, weight=1)

        for i in range(start_index, end_index):
            model = self.filtered_models[i]
            row = (i - start_index) // self.num_cols
            col = (i - start_index) % self.num_cols
            
            # Create truncated text for display
            display_text = self.truncate_text(model)
            
            cb = ttk.Checkbutton(self.checkbutton_frame, text=display_text, 
                               variable=self.selections[model], bootstyle="round-toggle")
            cb.grid(row=row, column=col, padx=5, pady=2, sticky="w")
            
            # Add tooltip for long names
            if len(model) > self.max_text_length:
                self.create_tooltip(cb, model)

    def get_page_label(self, page_num):
        """Returns the formatted page label based on page number and range."""
        start_index = page_num * self.page_size
        end_index = min(start_index + self.page_size, len(self.filtered_models))

        if start_index < end_index:
            first_model = self.filtered_models[start_index]
            last_model = self.filtered_models[end_index - 1]
            first_letter = first_model[0].upper()
            last_letter = last_model[0].upper()
            return f"第 {page_num + 1} 页 ({first_letter}-{last_letter}) [{end_index-start_index}项]"
        else:
            return f"第 {page_num + 1} 页 (空页)"

    def on_page_change(self, event=None):
        """Handles page changes from the dropdown."""
        selected_page_label = self.page_dropdown.get()
        # Extract page number from label format "第 X 页 ..."
        page_num = int(selected_page_label.split()[1]) - 1
        self.current_page = page_num
        self.update_checkbuttons()
        if event and hasattr(event, 'widget'):
            event.widget.selection_clear()

    def next_page(self):
        """Go to next page if available"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.page_var.set(self.get_page_label(self.current_page))
            self.update_checkbuttons()

    def prev_page(self):
        """Go to previous page if available"""
        if self.current_page > 0:
            self.current_page -= 1
            self.page_var.set(self.get_page_label(self.current_page))
            self.update_checkbuttons()

    def select_all(self):
        """Select all models on current page"""
        start_index = self.current_page * self.page_size
        end_index = min(start_index + self.page_size, len(self.filtered_models))
        
        for i in range(start_index, end_index):
            model = self.filtered_models[i]
            self.selections[model].set(True)

    def deselect_all(self):
        """Deselect all models on current page"""
        start_index = self.current_page * self.page_size
        end_index = min(start_index + self.page_size, len(self.filtered_models))
        
        for i in range(start_index, end_index):
            model = self.filtered_models[i]
            self.selections[model].set(False)

    def apply_filter(self):
        """Applies the filter based on the text in the filter entry."""
        filter_text = self.filter_entry.get().lower()

        if not filter_text:
            self.filtered_models = self.all_models
        else:
            self.filtered_models = [
                model for model in self.all_models if filter_text in model.lower()
            ]

        self.current_page = 0  # Reset to first page after filtering
        self.update_total_pages()
        self.page_labels = [self.get_page_label(i) for i in range(self.total_pages)]
        self.page_var.set(self.get_page_label(self.current_page))
        self.page_dropdown['values'] = self.page_labels
        self.update_checkbuttons()
        self.adjust_dialog_size()
        self.place_window_center()

    def update_total_pages(self):
        """Updates the total number of pages based on the filtered models."""
        self.total_pages = max(1, (len(self.filtered_models) + self.page_size - 1) // self.page_size)

    def place_window_center(self):
        """Center the dialog on the screen"""
        self.update_idletasks()
        
        # Get the screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Calculate position x, y
        width = self.winfo_width()
        height = self.winfo_height()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.geometry(f"+{x}+{y}")

    def adjust_dialog_size(self):
        """Adjusts the dialog size based on the number of models and their lengths."""
        # Use max_text_length instead of actual model length for calculations
        num_models = min(self.page_size, len(self.filtered_models))
        
        # Calculate width based on truncated text length
        char_width = 10  # Average character width in pixels
        checkbutton_padding = 40  # Padding and checkbox width
        
        # Calculate width per column
        col_width = self.max_text_length * char_width + checkbutton_padding
        
        # Calculate total width with padding
        width_padding = 50
        frame_width = col_width * self.num_cols + width_padding
        frame_width = max(frame_width, 650)  # Minimum width
        
        # Calculate height based on number of rows with padding for other widgets
        row_height = 30  # Height per row
        height_padding = 250  # Additional height for other UI elements
        frame_height = self.num_rows * row_height + height_padding
        
        self.geometry(f"{frame_width}x{frame_height}")

    def on_ok(self):
        add_models = []
        remove_models = []

        for model, selected in self.selections.items():
            if selected.get() and model not in self.existing_models:
                add_models.append(model)
            elif not selected.get() and model in self.existing_models:
                remove_models.append(model)

        self.result = {"add": add_models, "remove": remove_models}
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()




class LogRedirector:
    """一个简单的类，用于将输出重定向到日志文件。"""
    def __init__(self, log_file):
        self.log = open(log_file, 'a', encoding="utf-8")  # 打开文件以追加模式写入
        self.stdout = sys.stdout       # 保存原始的标准输出
        self.stderr = sys.stderr       # 保存原始的标准错误

    def write(self, message):
        """将消息写入日志文件"""
        self.log.write(message)
        self.log.flush()  # 确保及时写入文件

    def flush(self):
        """强制刷新缓冲区"""
        self.log.flush()

    def close(self):
        """在程序结束时关闭日志文件。"""
        self.log.close()







class ThemedNotebook(ttk.Notebook):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        
        # --- 创建自定义样式 ---
        style = ttk.Style()
        
        # 定义现代化配色方案
        self.bg_color = "#f7f7f7"               # 更柔和的背景色
        self.tab_bg_color = "#e9e9e9"           # 未选中标签背景
        self.tab_fg_color = "#555555"           # 深灰色文本，不用纯黑色
        self.selected_tab_bg_color = "#ffffff"  # 白色选中背景
        self.selected_tab_fg_color = "#2c8dca"  # 蓝色选中文本，增加突出效果
        self.hover_color = "#f0f0f0"            # 悬停颜色
        self.border_color = "#dddddd"           # 浅色边框
        
        # 配置笔记本整体样式
        style.configure("TNotebook", 
                       background=self.bg_color,
                       borderwidth=0,
                       tabmargins=[2, 5, 2, 0])  # 调整标签页边距
        
        # 配置标签样式
        style.configure("TNotebook.Tab",
                       background=self.tab_bg_color,
                       foreground=self.tab_fg_color,
                       borderwidth=3,
                       bordercolor=self.border_color,
                       padding=[12, 6],          # 水平方向增加更多空间
                       font=("Microsoft YaHei", 11))  # 稍微小一点的字体更精致
        
        # 配置鼠标悬停和选中效果
        style.map("TNotebook.Tab",
                 background=[("selected", self.selected_tab_bg_color),
                             ("active", self.hover_color)],
                 foreground=[("selected", self.selected_tab_fg_color)],
                 expand=[("selected", [1, 1, 1, 0])],  # 选中标签微微放大
                 bordercolor=[("selected", self.selected_tab_fg_color)])  # 选中时边框颜色变化
        
        # 去除默认焦点虚线边框
        style.configure("TNotebook.Tab", focuscolor=style.configure(".")["background"])
        
        # 应用自定义样式
        self.configure(style="TNotebook")
        
        # 添加底部边框效果
        self.bottom_border = tk.Frame(self.master, height=1, bg=self.border_color)
        self.bottom_border.pack(fill="x", side="top")
        
        # 绑定标签切换事件以更新高亮效果
        self.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
        # 初始化标签指示器效果
        self._tab_indicator = None
        
    def _on_tab_changed(self, event):
        """当标签页切换时更新视觉效果"""
        # 实现平滑的标签指示器动画效果
        tab_id = self.select()
        tab_idx = self.index(tab_id)
        
        # 获取当前选中标签的位置和大小信息
        bbox = self.bbox(tab_idx)
        if bbox:
            x, y, width, height = bbox
            
            # 创建或更新标签下方的指示线
            if not self._tab_indicator:
                self._tab_indicator = tk.Frame(self, 
                                             background=self.selected_tab_fg_color,
                                             height=2)
            
            # 放置在底部作为选中指示器
            self._tab_indicator.place(x=x, y=y+height-2, width=width, height=2)
            
            # 确保指示器在顶层可见
            self._tab_indicator.lift()




class GUI:
    def __init__(self, master):
        #self.config = configparser.ConfigParser()
        self.config_file = os.path.join(game_directory,"config.json")
        self.master = master
        self.load_config()

        # --- Font Configuration ---
        self.default_font = tkFont.Font(family="Microsoft YaHei", size=10)  
        master.option_add("*Font", self.default_font)
        style = ttk.Style()
        style.configure('.', font=("Microsoft YaHei", 10))

        master.title("AI GAL")

        # Notebook (Tabs)
        self.notebook = ThemedNotebook(master) 
        self.home_tab = ttk.Frame(self.notebook, style="TFrame") # Apply style
        self.notebook.add(self.home_tab, text="🏠 首页")
        self.create_home_tab_content()

        self.llm_config_tab = ttk.Frame(self.notebook, style="TFrame") # Apply style
        self.notebook.add(self.llm_config_tab, text="🐳 LLM配置")
        self.create_llm_config_tab_content()

        self.sovits_tab = ttk.Frame(self.notebook, style="TFrame") # Apply style
        self.notebook.add(self.sovits_tab, text="🎤 语音配置")
        self.create_sovits_tab_content()

        self.ai_draw_config_tab = ttk.Frame(self.notebook, style="TFrame")  # Apply style
        self.notebook.add(self.ai_draw_config_tab, text="🎨 AI绘画配置")
        self.create_ai_draw_config_tab_content()

        # AI Music Tab - Use the Separate Class and apply style
        self.ai_music_config_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.ai_music_config_tab, text="♫ AI音乐配置")
        self.create_ai_music_config_tab_content()

        self.snapshot_tab = ttk.Frame(self.notebook, style="TFrame") # Apply style
        self.notebook.add(self.snapshot_tab, text="📷 快照")
        self.create_snapshot_tab_content()

        self.log_tab = ttk.Frame(self.notebook, style="TFrame") # Apply style
        self.notebook.add(self.log_tab, text="📝 日志")
        self.create_log_tab_content()

        self.regenerate_tab = ttk.Frame(self.notebook, style="TFrame") # Apply style
        self.notebook.add(self.regenerate_tab, text="✨ 生成")
        self.create_regenerate_tab_content()

        self.about_tab = ttk.Frame(self.notebook, style="TFrame") # Apply style
        self.notebook.add(self.about_tab, text="ℹ️ 关于")
        self.create_about_tab_content()

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.notebook.pack(expand=True, fill="both")
        self.auto_check_update_on_startup()


    def clear_dropdown_selection(self, event):
        event.widget.selection_clear()

    def on_tab_change(self, event):
        self.master.focus_set()
        selected_tab = self.notebook.select()  # 返回选定标签的 widget ID
        if selected_tab == str(self.regenerate_tab):       # 比较 widget IDs
            self.character_names = self.load_character_names()
            self.character_dropdown['values'] = self.character_names
            self.character_var.set(self.character_names[0] if self.character_names else "")  # 设置默认值
        if selected_tab == str(self.snapshot_tab):
            self.populate_snapshot_buttons()
            


    def show_message_bubble(self, status, text, max_line_width=20):
        if threading.current_thread() != threading.main_thread():
            # 如果不在主线程，使用after方法将调用重定向到主线程
            self.master.after(0, lambda: self.show_message_bubble(status, text, max_line_width))
            return
        
        # Status check lists
        successlist = ["success", "Success", "成功", "True", "true", 0]
        errorlist = ["Error", "error", "fail", "failed", "Fail", "Failed", "错误", "False", "false", -1]
        
        # Determine status type
        for item in successlist:
            if isinstance(item, (int, float)):
                if status == item:
                    status = 'Success'
                    break
            else:
                if item in str(status):
                    status = 'Success'
                    break
                    
        for item in errorlist:
            if isinstance(item, (int, float)):
                if status == item:
                    status = 'Error'
                    break
            else:
                if item in str(status):
                    status = 'Error'
                    break

        # Define color scheme and icons based on status
        if status == "Success":
            fg_color = "#1E8449"  # Darker green
            bg_color = "#D4EFDF"  # Light green background
            border_color = "#A9DFBF"  # Medium green border
            text = "✓ " + text
            icon = "✓"
        elif status == "Error":
            fg_color = "#922B21"  # Darker red
            bg_color = "#F9EBEA"  # Light red background
            border_color = "#F5B7B1"  # Medium red border
            text = "✗ " + text
            icon = "✗"
        else:
            fg_color = "#5B2C6F"  # Darker purple
            bg_color = "#E8DAEF"  # Light purple background
            border_color = "#D2B4DE"  # Medium purple border
            text = "⏳ " + text
            icon = "⏳"

        # Create a Toplevel window for the bubble
        bubble = tk.Toplevel(self.master)
        bubble.withdraw()  # 隐藏窗口，防止闪烁
        bubble.overrideredirect(True)  # Remove window decorations
        bubble.config(bg=bg_color)  # Set the background color
        bubble.attributes("-alpha", 0.95)  # Slight transparency

        # --- Calculate Text Size and Wrap Text ---
        font = tkFont.Font(family="微软雅黑", size=10)  # Better font for display
        wrapped_text = self.wrap_text(text, font, max_line_width)
        text_width = max(font.measure(line) for line in wrapped_text.split('\n'))
        text_height = font.metrics("linespace") * (wrapped_text.count('\n') + 1)

        # --- Rounded Corners (Canvas-Based) with improved dimensions ---
        corner_radius = 15  # Increased radius for smoother corners
        padding_x = 20
        padding_y = 15
        canvas_width = text_width + padding_x * 2
        canvas_height = text_height + padding_y * 2
        
        canvas = tk.Canvas(bubble, bg=bg_color, height=canvas_height, width=canvas_width, 
                          bd=0, highlightthickness=0)
        canvas.pack()

        # Draw border first (slightly larger rounded rectangle)
        border_offset = 2
        self.draw_rounded_rectangle(canvas, border_offset, border_offset, 
                                   canvas_width-border_offset, canvas_height-border_offset, 
                                   corner_radius, fill=border_color, outline="")

        # Draw main background
        self.draw_rounded_rectangle(canvas, 2+border_offset, 2+border_offset, 
                                   canvas_width-2-border_offset, canvas_height-2-border_offset, 
                                   corner_radius-1, fill=bg_color, outline="")

        # Add icon in a circle on the left side
        icon_size = min(30, canvas_height - 20)
        icon_x = padding_x
        icon_y = canvas_height // 2
        
        # Draw small decorative dots at corners (subtle detail)
        dot_radius = 2
        dot_offset = corner_radius + 5
        dot_color = border_color
        
        # Top-left and bottom-right dots
        canvas.create_oval(dot_offset-dot_radius, dot_offset-dot_radius, 
                           dot_offset+dot_radius, dot_offset+dot_radius, 
                           fill=dot_color, outline="")
        canvas.create_oval(canvas_width-dot_offset-dot_radius, canvas_height-dot_offset-dot_radius, 
                           canvas_width-dot_offset+dot_radius, canvas_height-dot_offset+dot_radius, 
                           fill=dot_color, outline="")

        # Create text with proper spacing from the icon
        text_x = canvas_width / 2
        text_y = canvas_height / 2
        canvas.create_text(text_x, text_y, text=wrapped_text, font=("微软雅黑", 10), 
                          fill=fg_color, anchor="center", justify="center")

        bubble.update_idletasks()
        
        # Add subtle shadow
        bubble.configure(highlightbackground="#000022", highlightthickness=0)
        
        # Calculate the position of the bubble relative to the main window
        window_width = self.master.winfo_width()
        bubble_width = canvas_width

        # Position with a slight animation effect
        x = self.master.winfo_x() + window_width - bubble_width - 20
        y = self.master.winfo_y() + 50
        
        # Set initial position off-screen
        bubble.geometry(f"+{x+50}+{y}")
        bubble.deiconify()
        
        # Animate entrance
        def animate_in(step=0):
            if step <= 10:
                new_x = x + (10 - step) * 5
                bubble.geometry(f"+{new_x}+{y}")
                bubble.after(10, lambda: animate_in(step+1))
        
        animate_in()

        def destroy_bubble(status):
            if status == "Success":
                delay = 3.0
            elif status == "Error":
                delay = 4.0
            else:
                delay = 2.5
                
            time.sleep(delay)
            
            # Animate exit
            for i in range(11):
                if bubble.winfo_exists():  # Check if bubble still exists
                    new_x = x + i * 5
                    new_opacity = 0.95 - (i * 0.095)
                    bubble.geometry(f"+{new_x}+{y}")
                    bubble.attributes("-alpha", max(0.1, new_opacity))
                    time.sleep(0.01)
                    
            if bubble.winfo_exists():  # Final check before destroy
                bubble.destroy()

        threading.Thread(target=destroy_bubble, args=(status,)).start()

    def draw_rounded_rectangle(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        """Draw a rounded rectangle on a canvas"""
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def is_chinese(self, char):
        """判断一个字符是否为中文"""
        return '\u4e00' <= char <= '\u9fa5'

    def calculate_text_width(self, text, font, chinese_ratio=1.0):
        """计算文本的精确宽度，区分中英文字符"""
        width = 0
        for char in text:
            if self.is_chinese(char):
                width += font.measure("中") * chinese_ratio  # 中文字符宽度
            else:
                width += font.measure("a") * 0.75  # 英文字符宽度，调整系数
        return width

    def wrap_text(self, text, font, max_width, chinese_ratio=1.0):
        """优化的文本换行函数，支持中英文混合"""
        words = []
        current_word = ""
        
        # 将文本分解成更适合中英文混合的单元
        for char in text:
            if char == ' ':
                if current_word:
                    words.append(current_word)
                    current_word = ""
                words.append(' ')
            elif self.is_chinese(char):
                if current_word:
                    words.append(current_word)
                    current_word = ""
                words.append(char)
            else:
                current_word += char
        
        if current_word:
            words.append(current_word)
        
        lines = []
        current_line = []
        current_width = 0
        max_pixel_width = max_width * font.measure("中")
        
        for word in words:
            word_width = self.calculate_text_width(word, font, chinese_ratio)
            
            if word == ' ' and current_line:
                # 处理空格
                if current_width + word_width <= max_pixel_width:
                    current_line.append(word)
                    current_width += word_width
                continue
                
            if current_width + word_width <= max_pixel_width:
                current_line.append(word)
                current_width += word_width
            else:
                # 如果是单词太长，单独成行
                if not current_line:
                    lines.append(word)
                else:
                    lines.append(''.join(current_line))
                    current_line = [word]
                    current_width = word_width
        
        if current_line:
            lines.append(''.join(current_line))
            
        return '\n'.join(lines)


    def load_config(self):
        """Loads the configuration from the config.json file."""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print("Config file not found, creating a new one.")
            self.config = default_config
            self.save_config() # Save the default config
        except json.JSONDecodeError:
            print("Error decoding config.json.  Loading default config.")
            self.config = default_config
            self.save_config() # Save the default config

    def save_config(self):
        """Saves the configuration to the config.json file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"Error saving config.json: {e}")

    def create_home_tab_content(self):
        # Create a main container with padding
        main_frame = ttk.Frame(self.home_tab, padding="20 15 20 15")
        main_frame.pack(fill="both", expand=True)
        
        # Add a welcoming header section
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 15))
        
        welcome_label = ttk.Label(header_frame, text="欢迎使用AI Galgame生成器", font=("Arial", 18, "bold"))
        welcome_label.pack(anchor="w")
        

        
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=15)
        
        # === 游戏设置区域 ===
        settings_frame = ttk.LabelFrame(main_frame, text="游戏设置", padding=(15, 10))
        settings_frame.pack(fill="x", pady=(0, 15))
        
        # 创建两列布局
        settings_grid = ttk.Frame(settings_frame)
        settings_grid.pack(fill="x", padx=5, pady=10)
        settings_grid.columnconfigure(0, weight=1)  # 左列
        settings_grid.columnconfigure(1, weight=1)  # 右列
        
        # === 左侧设置组 ===
        left_settings = ttk.Frame(settings_grid)
        left_settings.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        # 大纲指导生成选项
        outline_frame = ttk.Frame(left_settings)
        outline_frame.pack(fill="x", pady=(0, 10))
        
        self.outline_switch_var = tk.BooleanVar()
        self.outline_switch_label = ttk.Label(outline_frame, text="大纲指导生成:")
        self.outline_switch_label.pack(side="left", padx=(5, 10))
        self.outline_switch = ttk.Checkbutton(
            outline_frame, 
            variable=self.outline_switch_var,
            command=self.save_outline_switch,
            bootstyle="round-toggle"
        )
        self.outline_switch.pack(side="left")
        
        # 语言选择框
        lang_frame = ttk.Frame(left_settings)
        lang_frame.pack(fill="x", pady=(0, 10))
        
        self.lang_var = tk.StringVar()
        self.lang_label = ttk.Label(lang_frame, text="游戏语言:")
        self.lang_label.pack(side="left", padx=(5, 10))
        self.lang = ttk.Combobox(
            lang_frame, 
            textvariable=self.lang_var, 
            values=["中文", "英文", "日文"],
            state="readonly",
            width=15
        )
        self.lang.pack(side="left", fill="x", expand=True)
        self.lang.bind("<<ComboboxSelected>>",
                       lambda event: [self.save_language(event),
                                      self.clear_dropdown_selection(event)])
        
        # === 右侧故事管理组 ===
        right_settings = ttk.Frame(settings_grid)
        right_settings.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        
        # 故事选择与管理
        story_selection_frame = ttk.Frame(right_settings)
        story_selection_frame.pack(fill="x", pady=(0, 10))
        
        self.story_title_var = tk.StringVar()
        self.story_names = [""]
        self.story_title_label = ttk.Label(story_selection_frame, text="选择故事:")
        self.story_title_label.pack(side="left", padx=(5, 10))
        self.story_title = ttk.Combobox(
            story_selection_frame, 
            textvariable=self.story_title_var,
            values=self.story_names, 
            state="readonly",
            width=25
        )
        self.story_title.pack(side="left", fill="x", expand=True)
        self.story_title.bind("<<ComboboxSelected>>",
                            lambda event: [self.save_story_title(event),
                                          self.clear_dropdown_selection(event)])
        
        # 故事管理按钮组
        story_mgmt_frame = ttk.Frame(right_settings)
        story_mgmt_frame.pack(fill="x", pady=(5, 0))
        
        # 使用更统一、更现代的按钮设计
        self.rename_button = ttk.Button(
            story_mgmt_frame, 
            text="🖋 故事改名", 
            command=self.rename_story,
            width=12
        )
        self.rename_button.pack(side="left", padx=(5, 5))
        
        self.delete_button = ttk.Button(
            story_mgmt_frame, 
            text="🗑 删除故事", 
            command=self.delete_story,
            width=12,
            bootstyle="danger"
        )
        self.delete_button.pack(side="left", padx=5)
        
        self.import_button = ttk.Button(
            story_mgmt_frame, 
            text="📤 本地导入", 
            command=self.import_story,
            width=12
        )
        self.import_button.pack(side="left", padx=5)
        
        # === 故事提示内容区域 ===
        content_frame = ttk.LabelFrame(main_frame, text="故事生成提示", padding=(15, 10))
        content_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # 文本区域容器
        text_container = ttk.Frame(content_frame)
        text_container.pack(fill="both", expand=True, padx=5, pady=10)
        
        # 创建带有滚动条的文本区域
        self.outline_content_entry = tk.Text(
            text_container, 
            width=50, 
            height=10,
            wrap="word",  # 自动换行
            font=("Arial", 11)
        )
        self.outline_content_entry.pack(side="left", fill="both", expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(text_container, command=self.outline_content_entry.yview)
        scrollbar.pack(side="right", fill="y")
        self.outline_content_entry.config(yscrollcommand=scrollbar.set)
        
        # 提示文本（可选）
        hint_text = "请在此处输入您的故事背景、角色设定和情节提示，AI将根据您的描述生成游戏内容..."
        hint_label = ttk.Label(content_frame, text=hint_text, foreground="gray")
        hint_label.pack(anchor="w", padx=10, pady=(0, 5))
        
        # === 底部操作区域 ===
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x", pady=(5, 0))
        
        # 左侧：开始按钮
        left_action = ttk.Frame(action_frame)
        left_action.pack(side="left")
        
        self.start_button = ttk.Button(
            left_action, 
            text="▶ 开始游戏",
            command=self.start,
            bootstyle="success",
            width=15,
            style="success.TButton"
        )
        # 使用custom_font = ("Arial", 12, "bold") 如果可用
        self.start_button.pack(side="left", padx=5, pady=5)
        
        # 右侧：高级选项按钮（可选）
        right_action = ttk.Frame(action_frame)
        right_action.pack(side="right")
        
        # 这个新按钮为高级选项，如果不需要可以删除
        advanced_button = ttk.Button(
            right_action,
            text="⚙️ 高级选项",
            command=lambda: self.show_advanced_options(),  # 需要实现此方法
            width=12
        )
        advanced_button.pack(side="right", padx=5, pady=5)
        
        # 加载保存的配置
        self.load_home_config()
        
    def show_advanced_options(self):
        # 实现显示高级选项的逻辑，可以是弹出窗口或展开隐藏内容
        # 这只是一个占位符函数，如果不需要可以删除此功能
        pass

    def rename_story(self):
        selected_story = self.story_title_var.get()
        if not selected_story:
            self.show_message_bubble("Error", "当前未选中故事")
            return

        new_name = simpledialog.askstring("Rename Story", "Enter new story name:",
                                          parent=self.master)
        if new_name:
            old_path = os.path.join(game_directory,"data", selected_story)
            new_path = os.path.join(game_directory,"data", new_name)

            try:
                os.rename(old_path, new_path)

                # Update config file
                #self.config.read(self.config_file, encoding="utf-8")
                self.config["剧情"]["story_title"] = new_name
                self.save_config()

                # Refresh story list
                self.story_names = [f for f in os.listdir(os.path.join(game_directory,"data")) if
                                    os.path.isdir(os.path.join(game_directory,"data", f))]
                self.story_names.sort()
                self.story_names.append("")
                self.story_title['values'] = self.story_names
                self.story_title_var.set(new_name)

                self.show_message_bubble("Success", "故事重命名成功!")

            except FileNotFoundError:
                self.show_message_bubble("Error", "故事目录不存在!")
            except FileExistsError:
                self.show_message_bubble("Error", "新故事名称已存在!")
            except Exception as e:
                messagebox.showerror("Error", f"重命名故事失败: {e}")

    def start(self):
        self.save_outline_content()
        if not self.story_title_var.get():
            threading.Thread(target=self.monitor_story_title).start()
        threading.Thread(target=self._start).start()
    def monitor_story_title(self):
        start_time = time.time()
        while time.time() - start_time < 180:
            time.sleep(10)
            try:
                #self.config.read(self.config_file, encoding="utf-8")
                self.load_config()
                new_story_title = self.config["剧情"].get("story_title", "")
                if new_story_title and new_story_title != self.story_title_var.get():
                    self.master.after(0, self.update_story_title, new_story_title)
                    break  # Exit the loop once the story title changes
            except Exception as e:
                print(f"Error monitoring story title: {e}")
                break
    def update_story_title(self, new_story_title):
        self.story_title_var.set(new_story_title)
        # Update available story list based on the 'data' directory
        try:
            self.story_names = [f for f in os.listdir(os.path.join(game_directory,"data")) if os.path.isdir(os.path.join(game_directory,"data", f))]
            self.story_names.sort()
            self.story_names.append("")  # Keep the blank entry
            self.story_title['values'] = self.story_names  # Update dropdown values
        except Exception as e:
            print(f"Error updating story list: {e}")
    def _start(self):
        try:
            status=gui_functions.start()
            if status!=1:
                self.show_message_bubble("Error",status)
        except NameError:
            self.show_message_bubble("Error","开始函数不可用")

    def save_story_title(self, event=None):
        try:
            #if "剧情" not in self.config:
            #    self.config["剧情"] = {}

            self.config["剧情"]["story_title"] = str(self.story_title_var.get())
            self.save_config()
            if str(self.story_title_var.get())!="":
                self.show_message_bubble("Success", f"成功切换故事到{str(self.story_title_var.get())}")
            else:
                self.show_message_bubble("Success", "已选择空项，开始游戏将会创建新故事")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving story title: {e}")
    def save_language(self, event=None):
        try:
            #if "剧情" not in self.config:
            #    self.config["剧情"] = {}

            self.config["剧情"]["language"] = str(self.lang_var.get())
            self.save_config()

            self.show_message_bubble("Success", f"成功切换到语言：{str(self.lang_var.get())}")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving language: {e}")
    def save_outline_switch(self):
        try:
            # Create section '剧情' if it does not exist
            #if "剧情" not in self.config:
            #    self.config["剧情"] = {}

            # Save the switch state
            self.config["剧情"]["if_on"] = self.outline_switch_var.get()
            self.save_config()
        except Exception as e:
            messagebox.showerror("Error", f"Error saving outline switch state: {e}")

    def save_outline_content(self):
        try:
            # Create section '剧情' if it does not exist
            #if "剧情" not in self.config:
            #    self.config["剧情"] = {}

            # Save the outline content
            self.config["剧情"]["outline_content_entry"] = self.outline_content_entry.get("1.0", tk.END).rstrip('\n\r')
            self.save_config()
        except Exception as e:
            messagebox.showerror("Error", f"Error saving outline content: {e}")

    def load_home_config(self):
        try:
            #self.config.read(self.config_file, encoding="utf-8")
            try:
                self.story_names = [f for f in os.listdir(os.path.join(game_directory,"data")) if os.path.isdir(os.path.join(game_directory,"data", f))]
                self.story_names.sort()
                self.story_names.extend([""])
                self.story_title['values'] = self.story_names
            except:
                pass

            # Load switch states
            self.outline_switch_var.set(self.config["剧情"].get("if_on", False))
            self.lang_var.set(self.config["剧情"].get("language", ""))
            self.story_title_var.set(self.config["剧情"].get("story_title", ""))
            self.outline_content_entry.insert(1.0, self.config["剧情"].get("outline_content_entry", ""))

        except FileNotFoundError:
            print("Config file not found, creating a new one.")
        except Exception as e:
            messagebox.showerror("Error", f"读取配置失败: {e}")

    def delete_story(self,message=1):
        selected_story = self.story_title_var.get()
        if not selected_story:
            self.show_message_bubble("Error", "当前选项无法删除")  # Or however you display messages
            return
        if selected_story == "":
            self.show_message_bubble("Error", "当前选项为空，无法删除")  # Or however you display messages
            return
        story_path = os.path.join(game_directory,"data", selected_story)
        if not os.path.exists(story_path) or not os.path.isdir(story_path):
            self.show_message_bubble("Error", f"目录不存在: {selected_story}")
            return
        try:
            shutil.rmtree(story_path)  # Use shutil.rmtree to delete the directory and its contents
            if message==1:
                self.show_message_bubble("Success", f"成功删除故事: {selected_story}")
            self.config["剧情"]["story_title"]=''
            self.save_config()

            # Update the story list
            self.story_names = [f for f in os.listdir(os.path.join(game_directory,"data")) if os.path.isdir(os.path.join(game_directory,"data", f))]
            self.story_names.sort()
            self.story_names.append("")  # Keep the blank entry
            self.story_title['values'] = self.story_names
            self.story_title_var.set("")  # Clear the selected story after deletion

        except Exception as e:
            messagebox.showerror("Error", f"删除故事失败: {e}")

    def load_local_story(self, path1, path2, path3, outline_status):
        title = self.story_title_var.get()
        data_dir = os.path.join(game_directory,"data",title)
        os.makedirs(os.path.join(game_directory,"data",title,"story"), exist_ok=True)
        character_data = None
        story_data = None
        outline_data = None

        character_status = "null"
        story_status = "null"
        outline_status_str = "null"

        # --- Character Intro ---
        if path1:
            try:
                with open(path1, 'r', encoding='utf-8') as f:
                    try:
                        character_data = json.load(f)
                        if isinstance(character_data, list) and all(isinstance(item, dict) and "name" in item for item in character_data):
                            character_status = "pass"
                        else:
                            character_status = "fail"
                            character_data = None
                    except json.JSONDecodeError:
                        # Try reading as text and converting to JSON
                        f.seek(0)
                        lines = [line.strip() for line in f.readlines() if line.strip()]
                        if all("：" in line for line in lines):
                            character_status = "pass"
                            character_data = []
                            for line in lines:
                                name, introduction = line.split("：", 1)
                                character_data.append({"name": name.strip(), "introduction": introduction.strip()})
                        else:
                            character_status = "fail"
                            with open(path1, 'r', encoding='utf-8') as f:
                                character_data = f.read()
            except Exception as e:
                print(f"人物介绍读取失败！{e}")
                character_data = None
                character_status = "null"
        else:
            character_status = "null"

        # --- Opening Text ---
        if path2:
            try:
                with open(path2, 'r', encoding='utf-8') as f:
                    try:
                        story_data = json.load(f)
                        if "conversations" in story_data:
                            story_data=story_data["conversations"]
                        if isinstance(story_data, list) and all(isinstance(item, dict) and all(key in item for key in ("place", "character", "text")) for item in story_data):
                            story_status = "pass"

                            # Remove existing ids if some items don't have them
                            if not all('id' in item for item in story_data):
                                for item in story_data:
                                    item.pop('id', None)

                            # Add ids if they aren't there
                            for i, item in enumerate(story_data):
                                item['id'] = i + 1
                                
                        else:
                            story_status = "fail"
                            story_data = None
                    except json.JSONDecodeError:
                        # Try reading as text and converting to JSON
                        f.seek(0)
                        lines = [line.strip() for line in f.readlines() if line.strip()]
                        valid = True
                        for line in lines:
                            # Remove anything enclosed in brackets
                            line_stripped = re.sub(r'\[.*?\]', '', line)
                            if "：" not in line_stripped:
                                valid = False
                                break
                            if not line.endswith("]") and line.count("[") > line.count("]"):
                                valid = False
                                break
                        if valid:
                            story_status = "pass"
                            story_data = []
                            for line in lines:
                                place = ""
                                text = line
                                match = re.search(r'\[(.*?)\]', line)
                                if match:
                                    place = match.group(1)
                                    text = line.replace(match.group(0), "")
                                character, text = text.split("：", 1)
                                character = character.strip()
                                text = text.strip()
                                match = re.search(r'\[(.*?)\]$', text)
                                if text.endswith("]"):
                                    text=text[:text.rfind("[")].strip()

                                if character == "旁白":
                                    character = ""  # Set character to "" for narration

                                story_data.append({"place": place, "character": character, "text": text.strip()})
                            for i, item in enumerate(story_data):
                                item['id'] = i + 1

                        else:
                            story_status = "fail"
                            with open(path2, 'r', encoding='utf-8') as f:
                                story_data = f.read()

            except Exception as e:
                print(f"开头文本读取失败！{e}")
                story_data = None
                story_status = "null"
        else:
            story_status = "null"

        # --- Outline ---
        if path3:
            try:
                with open(path3, 'r', encoding='utf-8') as f:
                    outline_data = f.read().strip()
                    if outline_data:
                        outline_status_str = "pass"
                    else:
                        outline_status_str = "fail"
                #if outline_data:
                #    outline_data = True
                #else:
                #    outline_data = False
            except Exception as e:
                print(f"大纲读取失败！{e}")
                outline_status_str = "null"
                outline_data = None

        else:
            outline_status_str = "null"

        if not character_data and not story_data and not outline_data and character_status == "null" and story_status == "null" and outline_status_str == "null":
            self.show_message_bubble("error", "所有项均获取失败，加载失败")
            self.delete_story(0)
            return "fail"

        # --- Save Data ---
        if character_data and character_status=="pass":
            with open(os.path.join(data_dir, "character.json"), 'w', encoding='utf-8') as f:
                json.dump(character_data, f, ensure_ascii=False, indent=4)
        if story_data and story_status=="pass":
            with open(os.path.join(data_dir,"story","0.json"), 'w', encoding='utf-8') as f:
                json.dump({"conversations": story_data}, f, ensure_ascii=False, indent=4)
        if outline_data and outline_status_str=="pass":
            with open(os.path.join(data_dir, "outline.json"), 'w', encoding='utf-8') as f:
                f.write(outline_data)

        # --- Update Config ---
        #self.config.read(self.config_file, encoding="utf-8")

        #self.config["剧情"]["local_story"] = ""
        local_story_config = {}

        local_story_config["character_content"] = str(character_data)
        local_story_config["story_content"] = str(story_data)
        local_story_config['outline_content']=str(outline_data)

        local_story_config["character_status"] = character_status
        local_story_config["stroy_status"] = story_status
        if outline_status:
            if outline_status_str == "null" or outline_status_str=="fail":
                outline_status_str="fail"
        else:
            outline_status_str="pass"
        local_story_config["outline_status"] = outline_status_str
        self.config["剧情"]["local_story"] = local_story_config
        self.save_config()
        if character_status=="pass" and outline_status_str=="pass" and outline_data:
            self.show_message_bubble("success", "导入成功，即将开始游戏")
            with open(os.path.join(data_dir, f"zw"), 'w') as f:
                pass
            self.start()
            return "success"
        if character_status=="pass" and story_status=="pass":
            self.show_message_bubble("success", "导入成功，即将开始游戏")
            with open(os.path.join(data_dir, f"zw"), 'w') as f:
                pass
            self.start()
            return "success"
        def process_json_string(input_string):
            try:
                start_index = input_string.find("{")
                end_index = input_string.rfind("}")
                if start_index == -1 or end_index == -1:
                    return "error"

                json_string = input_string[start_index:end_index + 1]

                data = json.loads(json_string)

                if not any(key in data for key in ["character", "outline", "conversations"]):
                    return "error"

                for key in ["character", "outline", "conversations"]:
                    if key in data:
                        if key == "conversations":
                            with open(os.path.join(data_dir,"story","0.json"), 'w', encoding='utf-8') as f:
                                json.dump({"conversations": data[key]}, f, ensure_ascii=False, indent=4)
                        else:
                            file_path = os.path.join(data_dir, f"{key}.json")
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(data[key], f, ensure_ascii=False, indent=4)  #indent for readability

                return "success"

            except json.JSONDecodeError:
                return "error"
            except Exception as e:
                print(f"An unexpected error occurred: {e}") # Add more logging
                return "error"
        prompt1,prompt2=handle_prompt.process_prompt('本地导入')
        id = random.randint(1, 100000)
        while True:
            try:
                gpt_response = GPT.gpt(prompt1, prompt2, '本地导入',id)
                if gpt_response=='over_times':
                    self.show_message_bubble("error", "gpt超出次数，导入失败")
                    self.delete_story(0)
                    return "fail"
                elif gpt_response and gpt_response != 'error':
                    result=process_json_string(gpt_response)
                    if result=="success":
                        self.show_message_bubble("success", "导入成功，即将开始游戏")
                        with open(os.path.join(data_dir, f"zw"), 'w') as f:
                            pass
                        self.start()
                        GPT.gpt_destroy(id)
                        return "success"
                    else:
                        continue
            except Exception as e:
                print(f"GPT call failed: {e}")
        #GPT.gpt()


    def import_story(self):
        
        import_window = tk.Toplevel(self.master)
        import_window.withdraw() # Create hidden
        import_window.title("本地导入故事")
        import_window.transient(self.master) # Keep on top of master
        import_window.grab_set() # Modal behavior
        import_window.resizable(False, False) # Prevent resizing

        # --- Window Centering ---
        window_width = 650  # Adjusted width for better fit
        window_height = 350 # Adjusted height for more padding
        screen_width = import_window.winfo_screenwidth()
        screen_height = import_window.winfo_screenheight()
        x = int((screen_width / 2) - (window_width / 2))
        y = int((screen_height / 2) - (window_height / 2))
        import_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        import_window.update_idletasks() # Ensure geometry is applied before showing

        # --- Style ---
        # Optional: You can configure ttk styles here if needed
        # style = ttk.Style(import_window)
        # style.configure('TButton', padding=5)
        # style.configure('TLabel', padding=2)

        # --- Variables ---
        character_intro_var = tk.BooleanVar()
        opening_text_var = tk.BooleanVar()
        outline_var = tk.BooleanVar()

        character_intro_path = tk.StringVar()
        opening_text_path = tk.StringVar()
        outline_path = tk.StringVar()

        # --- Main Frame ---
        # Increased padding for the main container
        main_frame = ttk.Frame(import_window, padding=(20, 10)) # (left/right, top/bottom)
        main_frame.pack(fill="both", expand=True)
        
        # Configure grid columns for main_frame (make column 1 expandable)
        main_frame.columnconfigure(1, weight=1)

        # --- Widgets ---

        # Row 0: Story Name
        story_name_label = ttk.Label(main_frame, text="故事名称:")
        story_name_label.grid(row=0, column=0, sticky="w", padx=5, pady=(0, 10)) # Add bottom padding
        story_name_entry = ttk.Entry(main_frame, width=40) # Use ttk.Entry
        story_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=(0, 10))

        # Row 1: Switches in a dedicated frame
        # Use a LabelFrame for better visual grouping (optional)
        switch_frame = ttk.LabelFrame(main_frame, text="包含内容", padding=(10, 5))
        # switch_frame = ttk.Frame(main_frame, padding=(10, 5)) # Alternative without title
        switch_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=10)

        # Use grid within switch_frame for alignment
        character_intro_check = ttk.Checkbutton(
            switch_frame, text="人物介绍", variable=character_intro_var
        )
        character_intro_check.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        opening_text_check = ttk.Checkbutton(
            switch_frame, text="开头文本", variable=opening_text_var
        )
        opening_text_check.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        outline_check = ttk.Checkbutton(
            switch_frame, text="故事大纲", variable=outline_var # Changed from "大纲" for clarity
        )
        outline_check.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        
        # Optional: Make checkboxes spread out if desired
        # switch_frame.columnconfigure(0, weight=1)
        # switch_frame.columnconfigure(1, weight=1)
        # switch_frame.columnconfigure(2, weight=1)

        # --- Path Frames and Widgets Creation Function ---
        def create_path_frame(parent, text, path_variable):
            # Use a standard Frame for grouping path elements
            frame = ttk.Frame(parent, padding=(0, 2)) # Add small vertical padding
            label = ttk.Label(frame, text=text, width=12, anchor="w") # Fixed width for alignment
            entry = ttk.Entry(frame, textvariable=path_variable, width=40) # Use ttk.Entry
            
            def browse_file():
                # Suggest file types if applicable
                filetypes = (("Text files", "*.txt;*.json"), ("All files", "*.*")) 
                filepath = filedialog.askopenfilename(title=f"选择 {text} 文件", filetypes=filetypes)
                if filepath:
                    path_variable.set(filepath)

            browse_button = ttk.Button(
                frame,
                text="浏览...", # Clearer text than icon
                # text="📁", # Keep icon if preferred
                width=6, # Give button a bit more space
                command=browse_file, 
            )

            # Use grid within the frame for better control
            label.grid(row=0, column=0, sticky="w", padx=(0, 5))
            entry.grid(row=0, column=1, sticky="ew", padx=5)
            browse_button.grid(row=0, column=2, sticky="e", padx=(5, 0))

            # Configure entry column to expand
            frame.columnconfigure(1, weight=1) 
            
            return frame

        # Create the path frames (they are initially hidden by grid_forget in update_visibility)
        character_intro_frame = create_path_frame(
            main_frame, "人物介绍:", character_intro_path # Use ":" for consistency
        )
        opening_text_frame = create_path_frame(
            main_frame, "开头文本:", opening_text_path
        )
        outline_frame = create_path_frame(main_frame, "故事大纲:", outline_path)

        # --- Dynamic Visibility Logic ---
        # Keep track of the next available row for path frames
        current_path_row = 2 

        def update_visibility(*args):
            nonlocal current_path_row # Allow modification of the row counter
            current_path_row = 2 # Reset row counter each time

            # Clear previous path frame placements first
            character_intro_frame.grid_forget()
            opening_text_frame.grid_forget()
            outline_frame.grid_forget()

            pady_val = (5, 2) # Standard padding for path rows

            if character_intro_var.get():
                character_intro_frame.grid(row=current_path_row, column=0, columnspan=2, sticky="ew", padx=5, pady=pady_val)
                current_path_row += 1 # Increment row for the next potential frame
            
            if opening_text_var.get():
                opening_text_frame.grid(row=current_path_row, column=0, columnspan=2, sticky="ew", padx=5, pady=pady_val)
                current_path_row += 1
            
            if outline_var.get():
                outline_frame.grid(row=current_path_row, column=0, columnspan=2, sticky="ew", padx=5, pady=pady_val)
                current_path_row += 1
            
            #Dynamically place the save button below the last path frame
            save_button.grid(row=current_path_row, column=0, columnspan=2, pady=(20, 10)) # Increased top padding

        # Trace variable changes to update layout
        character_intro_var.trace_add("write", update_visibility)
        opening_text_var.trace_add("write", update_visibility)
        outline_var.trace_add("write", update_visibility)

        # --- Save Button ---
        # Placed dynamically by update_visibility initially and on changes
        save_button = ttk.Button(main_frame, text="确认导入", command=lambda: start_loading(import_window, story_name_entry, character_intro_var, opening_text_var, outline_var, character_intro_path, opening_text_path, outline_path)) # Use ttk.Button
        # save_button.grid(row=5, column=0, columnspan=2, pady=(20, 10)) # Initial placement removed, handled by update_visibility
        
        # Define the loading function separately for clarity
        def start_loading(window, name_widget, c_var, o_var, otl_var, c_path, o_path, otl_path):
            title = name_widget.get().strip() # Use strip() to remove leading/trailing whitespace
            if not title:
                self.show_message_bubble("error", "故事名称不能为空")
                return

            path1 = c_path.get() if c_var.get() and c_path.get() else None
            path2 = o_path.get() if o_var.get() and o_path.get() else None
            path3 = otl_path.get() if otl_var.get() and otl_path.get() else None

            # Check if at least one *selected* option has a path
            # Or more simply: Check if at least one option is selected
            if not c_var.get() and not o_var.get() and not otl_var.get():
                 self.show_message_bubble("error", "请至少选择一项内容进行导入")
                 return
            # Check if selected items actually have paths (stricter check)
            no_paths_selected = True
            if c_var.get() and path1: no_paths_selected = False
            if o_var.get() and path2: no_paths_selected = False
            if otl_var.get() and path3: no_paths_selected = False

            if no_paths_selected and (c_var.get() or o_var.get() or otl_var.get()):
                 self.show_message_bubble("error", "请为选中的项目指定文件路径")
                 return

            # Proceed with import if checks pass
            try:
                 story_dir = os.path.join(game_directory, 'data', title) # Use os.path.join
                 os.makedirs(story_dir, exist_ok=True)
                 
                 self.update_story_title(title)
                 self.config["剧情"]["story_title"] = title
                 self.save_config()
                 
                 # Start loading in a background thread
                 threading.Thread(target=self.load_local_story, args=(path1, path2, path3, otl_var.get()), daemon=True).start() # Use daemon=True
                 
                 self.show_message_bubble("加载提示", f"开始导入故事 '{title}'...")
                 window.destroy() # Close the import window

            except OSError as e:
                 self.show_message_bubble("error", f"创建目录失败: {e}")
            except Exception as e:
                 self.show_message_bubble("error", f"导入时发生错误: {e}")

        # --- Final Setup ---
        update_visibility() # Call initially to set the layout based on default variable values
        import_window.deiconify() # Show the window now that it's configured 


    def create_llm_config_tab_content(self):
        # Create a main container with proper padding
        main_frame = ttk.Frame(self.llm_config_tab, padding="20 15 20 15")
        main_frame.pack(fill="both", expand=True)
        
        # Add a title section
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text="大语言模型配置", font=("等线", 16, "bold"))
        title_label.pack(anchor="w")
        
        
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=5)
        
        # === 配置选择区域 ===
        config_frame = ttk.LabelFrame(main_frame, text="配置管理", padding=(15, 10))
        config_frame.pack(fill="x", pady=(0, 15))
        
        # 上层：配置选择和操作按钮
        config_selection_frame = ttk.Frame(config_frame)
        config_selection_frame.pack(fill="x", padx=5, pady=10)
        
        # 配置下拉框和标签
        config_dropdown_frame = ttk.Frame(config_selection_frame)
        config_dropdown_frame.pack(side="left", fill="x", expand=True)
        
        ttk.Label(config_dropdown_frame, text="选择配置:").pack(side="left", padx=(5, 10))
        
        self.config_names = []
        self.config_selection_var = tk.StringVar()
        self.config_selection_dropdown = ttk.Combobox(
            config_dropdown_frame, 
            textvariable=self.config_selection_var, 
            values=self.config_names, 
            state="readonly",
            width=30
        )
        self.config_selection_dropdown.pack(side="left", fill="x", expand=True)
        self.config_selection_dropdown.bind("<<ComboboxSelected>>", self.on_config_select)
        
        # 配置操作按钮组
        config_buttons_frame = ttk.Frame(config_selection_frame)
        config_buttons_frame.pack(side="right")
        
        # 使用一致的按钮样式
        add_config_button = ttk.Button(
            config_buttons_frame, 
            text="➕ 新增", 
            command=self.add_llm_config,
            width=10
        )
        add_config_button.pack(side="left", padx=3)
        
        copy_config_button = ttk.Button(
            config_buttons_frame, 
            text="📋 复制", 
            command=self.copy_llm_config,
            width=10
        )
        copy_config_button.pack(side="left", padx=3)
        
        delete_config_button = ttk.Button(
            config_buttons_frame, 
            text="🗑 删除", 
            command=self.delete_llm_config, 
            bootstyle="danger",
            width=10
        )
        delete_config_button.pack(side="left", padx=3)
        
        # 分离特殊按钮，使其更明显
        integration_frame = ttk.Frame(config_frame)
        integration_frame.pack(fill="x", padx=5, pady=(0, 5))
        
        integration_config_button = ttk.Button(
            integration_frame, 
            text="⚙️ 接入模型配置", 
            command=self.open_integration_window,
            style="Accent.TButton",
            width=20
        )
        integration_config_button.pack(side="right")
        
        # === 内容区 - 使用Notebook分页 ===
        content_notebook = ttk.Notebook(main_frame)
        content_notebook.pack(fill="both", expand=True, pady=(0, 10))
        
        # === 基本信息配置页 ===
        basic_info_frame = ttk.Frame(content_notebook, padding=10)
        content_notebook.add(basic_info_frame, text="基本连接信息")
        
        # API连接信息表单
        form_frame = ttk.Frame(basic_info_frame)
        form_frame.pack(fill="both", expand=True)
        
        # URL输入区域
        url_frame = ttk.Frame(form_frame)
        url_frame.pack(fill="x", pady=(5, 10))
        
        ttk.Label(url_frame, text="模型 BaseURL:").pack(side="left", padx=(5, 10))
        
        self.model_baseurl_var = tk.StringVar()
        self.model_baseurl_entry = ttk.Entry(url_frame, textvariable=self.model_baseurl_var)
        self.model_baseurl_entry.pack(side="left", fill="x", expand=True)
        
        # API Key输入区域
        key_frame = ttk.Frame(form_frame)
        key_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(key_frame, text="API Key:").pack(side="left", padx=(5, 10))
        
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(key_frame, textvariable=self.api_key_var, show="*")  # 隐藏API密钥
        self.api_key_entry.pack(side="left", fill="x", expand=True)
        
        # 显示/隐藏API密钥切换按钮
        self.show_api_key = tk.BooleanVar(value=False)
        show_key_button = ttk.Checkbutton(
            key_frame,
            text="显示", 
            variable=self.show_api_key,
            command=lambda: self.api_key_entry.config(show="" if self.show_api_key.get() else "*"),
            width=5
        )
        show_key_button.pack(side="right", padx=5)
        
        # 保存按钮区域
        save_basic_frame = ttk.Frame(form_frame)
        save_basic_frame.pack(fill="x", pady=(10, 0))
        
        save_button = ttk.Button(
            save_basic_frame, 
            text="💾 保存基本配置", 
            command=self.save_llm_config,
            style="Accent.TButton",
            width=18
        )
        save_button.pack(side="right", padx=5, pady=5)
        
        # === 模型配置页 ===
        model_config_frame = ttk.Frame(content_notebook, padding=10)
        content_notebook.add(model_config_frame, text="模型参数设置")
        
        # 模型管理区域
        model_mgmt_frame = ttk.LabelFrame(model_config_frame, text="模型管理", padding=(10, 5))
        model_mgmt_frame.pack(fill="x", pady=(0, 15))
        
        # 模型选择区
        model_selection_frame = ttk.Frame(model_mgmt_frame)
        model_selection_frame.pack(fill="x", padx=5, pady=(10, 5))
        
        ttk.Label(model_selection_frame, text="选择模型:").pack(side="left", padx=(5, 10))
        
        self.model_names = []
        self.model_selection_var = tk.StringVar()
        self.model_selection_dropdown = ttk.Combobox(
            model_selection_frame, 
            textvariable=self.model_selection_var, 
            values=self.model_names, 
            state="readonly",
            width=30
        )
        self.model_selection_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.model_selection_dropdown.bind("<<ComboboxSelected>>", self.on_model_select)
        self.current_model_name_var = tk.StringVar()
        
        # 模型操作按钮区
        model_buttons_frame = ttk.Frame(model_mgmt_frame)
        model_buttons_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        model_buttons_left = ttk.Frame(model_buttons_frame)
        model_buttons_left.pack(side="left")
        
        model_buttons_right = ttk.Frame(model_buttons_frame)
        model_buttons_right.pack(side="right")
        
        # 模型管理按钮
        add_model_button = ttk.Button(
            model_buttons_left, 
            text="➕ 新增模型", 
            command=self.add_llm_model,
            width=12
        )
        add_model_button.pack(side="left", padx=(5, 3))
        
        delete_model_button = ttk.Button(
            model_buttons_left, 
            text="🗑 删除模型", 
            command=self.delete_llm_model, 
            bootstyle="danger",
            width=12
        )
        delete_model_button.pack(side="left", padx=3)
        
        # 模型操作按钮
        get_models_button = ttk.Button(
            model_buttons_right, 
            text="📥 从服务器获取模型", 
            command=self.get_models_from_server,
            width=18
        )
        get_models_button.pack(side="left", padx=3)
        
        test_model_button = ttk.Button(
            model_buttons_right, 
            text="✔ 测试模型", 
            command=self.test_llm_model,
            width=12
        )
        test_model_button.pack(side="left", padx=3)
        
        # === 模型参数配置区 ===
        model_params_frame = ttk.LabelFrame(model_config_frame, text="模型参数", padding=(10, 5))
        model_params_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 创建参数网格布局 - 修改为3列
        params_grid = ttk.Frame(model_params_frame)
        params_grid.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 配置3列等宽
        params_grid.columnconfigure(0, weight=1)  # 第1列
        params_grid.columnconfigure(1, weight=1)  # 第2列
        params_grid.columnconfigure(2, weight=1)  # 第3列
        
        # 参数标签和输入框宽度
        label_width = 12
        entry_width = 8
        
        # 创建统一的参数输入单元格函数
        def create_param_cell(parent, label_text, variable, validate_func=None, row=0, col=0, tooltip=None):
            frame = ttk.Frame(parent)
            frame.grid(row=row, column=col, sticky="ew", padx=5, pady=5)
            
            label = ttk.Label(frame, text=label_text + ":", width=label_width)
            label.pack(side="left")
            
            entry = ttk.Entry(frame, textvariable=variable, width=entry_width)
            entry.pack(side="left", fill="x", expand=True)
            
            if validate_func:
                entry.config(validate="key", validatecommand=(entry.register(validate_func), '%P'))
            
            return entry
        
        # 第一行参数
        self.model_retry_var = tk.StringVar(value="3")
        create_param_cell(
            params_grid, "最大尝试次数", self.model_retry_var, 
            self.llm_validate_range_retry, row=0, col=0
        )
        
        self.temperature_var = tk.StringVar()
        create_param_cell(
            params_grid, "Temperature", self.temperature_var, 
            self.llm_validate_range_temperature, row=0, col=1
        )
        
        self.top_p_var = tk.StringVar()
        create_param_cell(
            params_grid, "Top P", self.top_p_var, 
            None, row=0, col=2
        )
        
        # 第二行参数
        self.frequency_penalty_var = tk.StringVar()
        create_param_cell(
            params_grid, "Freq Penalty", self.frequency_penalty_var, 
            self.llm_validate_range_penalty, row=1, col=0
        )
        
        self.presence_penalty_var = tk.StringVar()
        create_param_cell(
            params_grid, "Pres Penalty", self.presence_penalty_var, 
            self.llm_validate_range_penalty, row=1, col=1
        )
        
        self.max_tokens_var = tk.StringVar()
        create_param_cell(
            params_grid, "Max Tokens", self.max_tokens_var, 
            self.llm_validate_range_retry, row=1, col=2
        )
            

        self.model_baseurl_entry.bind("<FocusIn>", lambda event: event.widget.selection_clear())
        # 保存模型配置按钮
        save_model_frame = ttk.Frame(model_config_frame)
        save_model_frame.pack(fill="x", pady=(0, 0))
        
        self.save_model_config_button = ttk.Button(
            save_model_frame, 
            text="💾 保存模型参数", 
            command=self.save_current_model_config,
            style="Accent.TButton",
            width=18
        )
        self.save_model_config_button.pack(side="right", padx=5)
        
        # 加载已保存的配置
        self.load_llm_config()


    def on_config_select(self, event=None):
        selected_config = self.config_selection_var.get()
        if selected_config:
            self.save_current_model_config() # Save current model config
            self.load_llm_config_values(selected_config)
        if event:
            event.widget.selection_clear()

    def add_llm_config(self):
        """Adds a new LLM configuration."""
        new_config_name = simpledialog.askstring("配置名称", "请输入新的配置名称:", parent=self.master)
        if new_config_name:
            if new_config_name in self.config["模型"]["configs"]:
                self.show_message_bubble("错误", "配置名称已存在")
                return

            self.config["模型"]["configs"][new_config_name] = {
                "model_baseurl": "",
                "api_key": "",
                "models": []
            }
            self.config_names.append(new_config_name)
            self.config_selection_dropdown['values'] = self.config_names  # Update dropdown list
            self.config_selection_var.set(new_config_name)  # Select the new configuration
            self.model_names = [] # Clear model names
            self.model_selection_dropdown['values'] = self.model_names
            self.clear_llm_config_values()
            self.clear_model_config_values()
            self.save_config()
            self.model_selection_var.set("")
            if len(self.config_names)==1:
                self.load_llm_config()
            #self.models=[]

    def copy_llm_config(self):
        """Copies the selected LLM configuration to a new configuration."""
        selected_config = self.config_selection_var.get()
        if not selected_config:
            self.show_message_bubble("错误", "请选择要复制的配置")
            return

        new_config_name = simpledialog.askstring("📄 复制配置", "请输入复制后的配置名称:", parent=self.master)
        if new_config_name:
            if new_config_name in self.config["模型"]["configs"]:
                self.show_message_bubble("错误", "配置名称已存在")
                return

            # Copy values from selected config
            self.load_llm_config_values(selected_config)

            self.config["模型"]["configs"][new_config_name] = {
                "model_baseurl": self.model_baseurl_var.get(),
                "api_key": self.api_key_var.get(),
                "models": self.models
            }

            self.config_names.append(new_config_name)
            self.config_selection_dropdown['values'] = self.config_names
            self.config_selection_var.set(new_config_name)
            self.save_config()


    def delete_llm_config(self):
        """Deletes the selected LLM configuration."""
        selected_config = self.config_selection_var.get()

        if not selected_config:
            self.show_message_bubble("错误", "请选择要删除的配置")
            return
        del self.config["模型"]["configs"][selected_config]

        self.config_names.remove(selected_config)
        self.config_selection_dropdown['values'] = self.config_names

        # Select the first configuration, if available
        if self.config_names:
            self.config_selection_var.set(self.config_names[0])
            self.load_llm_config_values(self.config_names[0])
        else:
            self.config_selection_var.set("")  # Clear selection
            self.clear_llm_config_values()
            self.clear_model_config_values()
        self.save_config()
        self.show_message_bubble("Success", "已删除")

    def load_llm_config(self):
        """Loads LLM configurations from config.json."""
        try:
            #self.config.read(self.config_file, encoding="utf-8")
            #if "模型" not in self.config:
            #    self.config["模型"] = {}

            # Load configuration names
            self.config_names = sorted(list(self.config["模型"]["configs"].keys()))
            self.config_selection_dropdown['values'] = self.config_names

            if self.config_names:
                self.config_selection_var.set(self.config_names[0])  # Select the first configuration
                self.load_llm_config_values(self.config_names[0])  # Load its values

        except FileNotFoundError:
            print("Config file not found, creating a new one.")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading LLM config: {e}")

    def save_llm_config(self):
        """Saves the LLM configuration to config.json."""
        try:
            selected_config = self.config_selection_var.get()

            # Save basic information
            if selected_config:
                self.config["模型"]["configs"][selected_config]["model_baseurl"] = self.model_baseurl_var.get()
                self.config["模型"]["configs"][selected_config]["api_key"] = self.api_key_var.get()
            self.save_config()
            self.show_message_bubble("Success", "成功保存配置信息！")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving LLM config: {e}")

    def load_llm_config_values(self, config_name):
        """Loads the values for a specific LLM configuration."""
        try:
            #self.config.read(self.config_file, encoding="utf-8")
            config_data = self.config["模型"]["configs"].get(config_name, {})

            # Load basic information
            self.model_baseurl_var.set(config_data.get("model_baseurl", ""))
            self.api_key_var.set(config_data.get("api_key", ""))

            # Load model names and select the first one
            self.models = config_data.get("models", [])
            self.model_names = [model["name"] for model in self.models]
            self.model_selection_dropdown['values'] = self.model_names

            if self.model_names:
                self.model_selection_var.set(self.model_names[0])
                self.load_model_config_values(self.model_names[0])
            else:
                self.model_selection_var.set("")
                self.clear_model_config_values()

        except Exception as e:
            messagebox.showerror("Error", f"Error loading LLM config values: {e}")

    def clear_llm_config_values(self):
        self.model_baseurl_var.set("")
        self.api_key_var.set("")

    def add_llm_model(self):
        """Adds a new LLM model to the selected configuration."""
        selected_config = self.config_selection_var.get()
        if not selected_config:
            self.show_message_bubble("错误", "请先选择一个配置")
            return

        new_model_name = simpledialog.askstring("模型名称", "请输入新的模型名称:", parent=self.master)
        if new_model_name:
            if new_model_name in self.model_names:
                self.show_message_bubble("错误", "模型名称已存在")
                return

            new_model = {"name": new_model_name, "max_retry": "3", "temperature": "", "top_p": "", "frequency_penalty": "","presence_penalty":"","max_tokens": ""} # Default max_retry = "3"
            self.models.append(new_model)
            self.model_names.append(new_model_name)
            self.model_selection_dropdown['values'] = self.model_names
            self.model_selection_var.set(new_model_name)  # Select the new model
            self.load_model_config_values(new_model_name)
        self.save_current_model_config()

    def delete_llm_model(self):
        """Deletes the selected LLM model from the selected configuration."""
        selected_config = self.config_selection_var.get()
        selected_model = self.model_selection_var.get()

        if not selected_config:
            self.show_message_bubble("错误", "请先选择一个配置")
            return

        if not selected_model:
            self.show_message_bubble("错误", "请选择要删除的模型")
            return

        for model in self.models:
            if model["name"] == selected_model:
                self.models.remove(model)
                break

        self.model_names.remove(selected_model)
        self.model_selection_dropdown['values'] = self.model_names

        if self.model_names:
            self.model_selection_var.set(self.model_names[0]) # Select the first model
            self.load_model_config_values(self.model_names[0])
        else:
            self.model_selection_var.set("")
            self.clear_model_config_values()

        self.save_current_model_config()

    def get_models_from_server(self):
        """Simulates fetching model names from a server and lets the user select which to import."""
        base_url = self.model_baseurl_var.get()
        api_key = self.api_key_var.get()

        if not base_url or not api_key:
            self.show_message_bubble("错误", "请先填写模型baseurl和api-key")
            return

        # Use threading to prevent UI freeze
        thread = threading.Thread(target=self.fetch_models_thread, args=(base_url, api_key))
        thread.start()

    def fetch_models_thread(self, base_url, api_key):
        self.show_message_bubble("","等待返回结果")
        """Thread function to fetch models and display selection dialog."""
        try:
            url=base_url+'/models'
            #print(url)
            #print(api_key)
            headers={'Authorization':api_key}
            response = requests.get(url, headers=headers)
            #print(json.loads(response.text)['data'])
            try:
                data = json.loads(response.text)['data']
                models_from_server = [item['id'] for item in data if 'id' in item]
                models_from_server.sort(key=lambda model_id: (any('\u4e00' <= char <= '\u9fa5' for char in model_id), model_id.lower()))
            except:
                models_from_server=[]

            self.master.after(0, self.show_model_selection_dialog, models_from_server)

        except Exception as e:
            self.master.after(0, lambda: messagebox.showerror("Error", f"Error fetching models: {e}"))

    def show_model_selection_dialog(self, models):
        """Displays a dialog allowing the user to select models to import/remove."""
        dialog = ModelSelectionDialog(self.master, models, self.model_names)  # Pass existing model names
        self.master.wait_window(dialog)

        selected_models = dialog.result

        if selected_models is not None: # Check if the dialog was not canceled
            # Add new models
            for model_name in selected_models["add"]:
                new_model = {"name": model_name, "max_retry": "3", "temperature": "", "top_p": "", "frequency_penalty": "","presence_penalty":"", "max_tokens": ""}
                self.models.append(new_model)
                self.model_names.append(model_name)

            # Remove models
            for model_name in selected_models["remove"]:
                for model in self.models:
                    if model["name"] == model_name:
                        self.models.remove(model)
                        break
                self.model_names.remove(model_name)

            self.model_selection_dropdown['values'] = self.model_names

            if self.model_names:
                self.model_selection_var.set(self.model_names[0])
                self.load_model_config_values(self.model_names[0])
            else:
                self.clear_model_config_values()

            self.save_current_model_config()

    def on_model_select(self, event=None):
        """Handles model selection from the dropdown."""
        selected_model = self.model_selection_var.get()
        if selected_model:
            self.save_current_model_config()  # Save the current model's config
            self.load_model_config_values(selected_model)
        if event:
            event.widget.selection_clear()

    def load_model_config_values(self, model_name):
        """Loads model-specific configuration values into the entry fields."""
        self.current_model_name_var.set(model_name)
        for model in self.models:
            if model["name"] == model_name:
                self.model_retry_var.set(model["max_retry"])
                self.temperature_var.set(model["temperature"])
                self.top_p_var.set(model["top_p"])
                self.frequency_penalty_var.set(model["frequency_penalty"])
                self.presence_penalty_var.set(model['presence_penalty'])
                self.max_tokens_var.set(model["max_tokens"])
                return

    def clear_model_config_values(self):
        """Clears the model-specific configuration values."""
        self.model_retry_var.set("3") # Default value
        self.temperature_var.set("")
        self.top_p_var.set("")
        self.frequency_penalty_var.set("")
        self.presence_penalty_var.set("")
        self.max_tokens_var.set("")

    def save_current_model_config(self):
        """Saves the current model's configuration to the models list."""
        selected_config = self.config_selection_var.get()
        model_name = self.current_model_name_var.get()

        if not selected_config or not model_name:
            return

        config_data = self.config["模型"]["configs"][selected_config]

        for model in config_data["models"]:
            if model["name"] == model_name:
                model["max_retry"] = self.model_retry_var.get()
                model["temperature"] = self.temperature_var.get()
                model["top_p"] = self.top_p_var.get()
                model["frequency_penalty"] = self.frequency_penalty_var.get()
                model["presence_penalty"]=self.presence_penalty_var.get()
                model["max_tokens"] = self.max_tokens_var.get()
                break
        #self.save_llm_config()
        self.save_config()

    def open_integration_window(self):
        """Opens a new window for integration configuration."""
        integration_window = tk.Toplevel(self.master)
        integration_window.withdraw()
        integration_window.title("接入模型配置区")

        # Calculate the center position
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        window_width = 1000  # Adjust as needed
        window_height = 800  # Adjust as needed
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        integration_window.resizable(False, False)
        integration_window.transient(self.master)
        integration_window.grab_set()

        # Make the window modal and stay on top
        integration_window.transient(self.master) # Make it a child of the main window
        integration_window.grab_set()            # Grab all events for this window

        # Create a notebook (tabbed interface)
        notebook = ttk.Notebook(integration_window)
        notebook.pack(fill="both", expand=True)

        # Create tabs
        tab_names = ["默认", "大纲", "正文", "选项", "人物", "背景", "音乐","对话","总结","本地导入","其他"]
        self.tabs = {}
        for tab_name in tab_names:
            tab = ModelSettingTab(notebook, self, tab_name)
            notebook.add(tab.frame, text=tab_name)
            self.tabs[tab_name] = tab

        # Create prompts tab
        self.prompt_tab = PromptConfigTab(notebook, self)
        notebook.add(self.prompt_tab.frame, text="提示词")

        integration_window.geometry(f"{window_width}x{window_height}+{x}+{y}") # <--- 设置位置和大小
        integration_window.update_idletasks() #Ensure updates

        integration_window.deiconify() # <-- 添加：设置完后显示

    def test_llm_model(self):
        """Tests the currently selected LLM model."""
        base_url = self.model_baseurl_var.get()
        api_key = self.api_key_var.get()
        model_name = self.current_model_name_var.get()

        if not base_url or not api_key or not model_name:
            self.show_message_bubble("错误", "请先填写模型baseurl、api-key和选择模型")
            return
        self.show_message_bubble("", f"开始测试{model_name}")
        # Create a thread to perform the test without blocking the UI
        thread = threading.Thread(target=self.run_model_test, args=(base_url, api_key, model_name))
        thread.start()

    def run_model_test(self, base_url, api_key, model_name):
        """Runs the model test and displays the result."""
        try:
            headers = {
                'Accept': 'application/json',
                'Authorization': api_key,
                'Content-Type': 'application/json'  # Important: Add Content-Type
            }
            a = {
                "model": model_name,
                "messages": [{"role": "user", "content": "你好"}]  # Correct messages format
            }
            data = json.dumps(a)

            response = requests.post(base_url+'/chat/completions', headers=headers, data=data)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            response_json = response.json()

            if 'choices' in response_json and len(response_json['choices']) > 0 and \
               'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message'] and \
               response_json['choices'][0]['message']['content']:
                self.master.after(0, lambda: self.show_message_bubble("Success", f"{model_name}测试通过"))
            else:
                self.master.after(0, lambda: self.show_message_bubble("Error", f"{model_name}测试失败"))

        except:
            self.master.after(0, lambda: self.show_message_bubble("Error", f"{model_name}测试不通过"))


    def llm_validate_range_retry(self, P):
        if P == "":
            return True  # Allow empty string

        try:
            value = int(P)
            return value>0
        except ValueError:
            return False
    def llm_validate_range_penalty(self, P):
        if P == "" or P == "-":
            return True  # Allow empty string

        try:
            value = float(P)
            return -2 <= value <= 2
        except ValueError:
            return False
    def llm_validate_range_temperature(self, P):
        if P == "":
            return True  # Allow empty string

        try:
            value = float(P)
            return 0 <= value <= 2
        except ValueError:
            return False

    def create_sovits_tab_content(self):
        # Create a main container with padding
        main_frame = ttk.Frame(self.sovits_tab, padding="20 15 20 15")
        main_frame.pack(fill="both", expand=True)
        
        # Add a title section
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text="语音合成配置", font=("等线", 16, "bold"))
        title_label.pack(anchor="w")
        
        subtitle_label = ttk.Label(title_frame, text="配置语音文件、文本内容和模型参数", font=("Arial", 10))
        subtitle_label.pack(anchor="w", pady=(5, 0))
        
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=15)
        
        # Create a scrollable frame for entries
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Create canvas with scrollbar for better handling of multiple entries
        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        
        # Scrollable frame inside canvas
        self.sovits_entries_frame = ttk.Frame(self.canvas)
        
        # Configure scrolling
        self.sovits_entries_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        canvas_id = self.canvas.create_window((0, 0), window=self.sovits_entries_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Create header row for columns
        header_frame = ttk.Frame(self.sovits_entries_frame)
        header_frame.pack(fill="x", padx=5, pady=(0, 10))
        
        # Column headers with fixed widths
        ttk.Label(header_frame, text="序号", width=5, font=("Arial", 10, "bold")).pack(side="left", padx=(5, 10))
        ttk.Label(header_frame, text="音频文件", width=60, font=("Arial", 10, "bold")).pack(side="left", padx=5)
        ttk.Label(header_frame, text="文本内容", width=50, font=("Arial", 10, "bold")).pack(side="left", padx=5)
        ttk.Label(header_frame, text="模型名称", width=15, font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        # Add separator after headers
        separator_frame = ttk.Frame(self.sovits_entries_frame, height=2)
        separator_frame.pack(fill="x", padx=5, pady=(0, 5))
        ttk.Separator(separator_frame, orient="horizontal").pack(fill="x")
        
        # Initialize entry containers
        self.file_path_entries = []
        self.text_content_entries = []
        self.model_name_entries = []
        
        # Create styled rows with alternating background for better visual separation
        for i in range(7):
            # Create row with a slight background tint for even rows (for visual separation)
            row_frame = ttk.Frame(self.sovits_entries_frame)
            row_frame.pack(fill="x", padx=5, pady=3)
            
            # Row number label
            index_label = ttk.Label(row_frame, text=f"{i+1}", width=5)
            index_label.pack(side="left", padx=(5, 10))
            
            # File path entry with button
            file_container = ttk.Frame(row_frame)
            file_container.pack(side="left", padx=5)
            
            file_path_entry = tk.Text(file_container, width=40, height=2, wrap="word")
            file_path_entry.pack(side="left")
            self.file_path_entries.append(file_path_entry)
            
            select_button = ttk.Button(
                file_container, 
                text="📁", 
                width=3,
                command=lambda idx=i: self.select_file(idx)
            )
            select_button.pack(side="left", padx=(5, 0))
            
            # Text content entry
            text_content_entry = tk.Text(row_frame, width=40, height=2, wrap="word")
            text_content_entry.pack(side="left", padx=5)
            self.text_content_entries.append(text_content_entry)
            
            # Model name entry
            model_name_entry = tk.Text(row_frame, width=25, height=2, wrap="word")
            model_name_entry.pack(side="left", padx=5)
            self.model_name_entries.append(model_name_entry)
        
        # Bottom control panel
        control_panel = ttk.LabelFrame(main_frame, text="批量操作", padding=(15, 10))
        control_panel.pack(fill="x", pady=(5, 10))
        
        # Create two rows for better organization
        top_controls = ttk.Frame(control_panel)
        top_controls.pack(fill="x", padx=5, pady=(5, 10))
        
        bottom_controls = ttk.Frame(control_panel)
        bottom_controls.pack(fill="x", padx=5, pady=(0, 5))
        
        # First row: Text fill button
        self.fill_text_button = ttk.Button(
            top_controls, 
            text="✍️ 一键填入文本内容", 
            command=self.fill_text_content,
            width=20
        )
        self.fill_text_button.pack(side="left", padx=(5, 20))
        
        # First row: Model fill section
        model_frame = ttk.Frame(top_controls)
        model_frame.pack(side="left", fill="x", expand=True)
        
        self.model_name_label = ttk.Label(model_frame, text="批量设置模型名称:")
        self.model_name_label.pack(side="left", padx=(0, 10))
        
        self.model_name_all_entry = ttk.Entry(model_frame, width=30)
        self.model_name_all_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.fill_model_button = ttk.Button(
            model_frame, 
            text="✍️ 应用到全部", 
            command=self.fill_model_names,
            width=15
        )
        self.fill_model_button.pack(side="left")
        
        # Second row: Extra operations and save button
        # You can add additional controls here if needed
        
        # Save button in bottom row, right aligned
        self.save_sovits_button = ttk.Button(
            bottom_controls, 
            text="💾 保存配置", 
            command=self.save_sovits_config,
            style="Accent.TButton",
            width=15
        )
        self.save_sovits_button.pack(side="right", padx=5)
        
        # Optional: Add a note or help text
        note_label = ttk.Label(
            bottom_controls, 
            text="提示: 选择音频文件后，可以一键批量设置模型名称",
            foreground="gray"
        )
        note_label.pack(side="left", padx=5)
        
        # Load existing configuration
        self.load_sovits_config()
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_sovits)  # Windows
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_sovits)  # Linux scroll up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_sovits)  # Linux scroll down

        self._bind_mousewheel_sovits(self.sovits_tab) # Bind to every element such as canvas, labels etc.

    def _bind_mousewheel_sovits(self, widget):
        """Recursively binds mousewheel events to a widget and its children."""
        widget.bind("<MouseWheel>", self._on_mousewheel_sovits)
        widget.bind("<Button-4>", self._on_mousewheel_sovits)  # Linux scroll up
        widget.bind("<Button-5>", self._on_mousewheel_sovits)  # Linux scroll down
        for child in widget.winfo_children():
            self._bind_mousewheel_sovits(child)

    def _on_mousewheel_sovits(self, event):
        """Handles MouseWheel events on the canvas"""
        try:
            widget = event.widget
            while widget:
                if widget.winfo_class() == 'Text':  # Or 'TkText' or however your text widget is.
                    return  # Found a Text widget, don't scroll the Canvas
                widget = widget.master

            if event.num == 4: # For Linux
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5: # For Linux
                self.canvas.yview_scroll(1, "units")
            else:  # For Windows
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except:
            pass
            

    def select_file(self, index):
        filename = filedialog.askopenfilename()
        if filename:
            self.file_path_entries[index].delete("1.0", tk.END)
            self.file_path_entries[index].insert("1.0", filename)

    def fill_text_content(self):
        for i, file_path_entry in enumerate(self.file_path_entries):
            file_path = file_path_entry.get("1.0", tk.END)
            if file_path:
                filename = os.path.basename(file_path)
                name_without_extension = os.path.splitext(filename)[0]
                self.text_content_entries[i].delete("1.0", tk.END)
                name_without_extension = re.sub(r'\【.*?\】', '', name_without_extension)
                name_without_extension = re.sub(r'\[.*?\]', '', name_without_extension)
                self.text_content_entries[i].insert("1.0", name_without_extension)

    def fill_model_names(self):
        model_name = self.model_name_all_entry.get()
        for model_name_entry in self.model_name_entries:
            model_name_entry.delete("1.0", tk.END)
            model_name_entry.insert("1.0", model_name)

    def load_sovits_config(self):
        try:
            # Load file paths, text content, and model names
            for i in range(7):
                path_key = f"path{i+1}"
                text_key = f"text{i+1}"
                model_key = f"model{i+1}"

                self.file_path_entries[i].delete("1.0", tk.END)
                self.file_path_entries[i].insert("1.0", self.config["SOVITS"].get(path_key, ""))
                self.text_content_entries[i].delete("1.0", tk.END)
                self.text_content_entries[i].insert("1.0", self.config["SOVITS"].get(text_key, ""))
                self.model_name_entries[i].delete("1.0", tk.END)
                self.model_name_entries[i].insert("1.0", self.config["SOVITS"].get(model_key, ""))

        except FileNotFoundError:
            print("Config file not found, creating a new one.")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading sovits config: {e}")

    def save_sovits_config(self):
        try:
            # Save file paths, text content, and model names
            for i in range(7):
                path_key = f"path{i+1}"
                text_key = f"text{i+1}"
                model_key = f"model{i+1}"

                self.config["SOVITS"][path_key] = self.file_path_entries[i].get("1.0", tk.END).strip().replace('\n', '')
                self.config["SOVITS"][text_key] = self.text_content_entries[i].get("1.0", tk.END).strip().replace('\n', '')
                self.config["SOVITS"][model_key] = self.model_name_entries[i].get("1.0", tk.END).strip().replace('\n', '')

            self.save_config()
            self.show_message_bubble("Success", "语音配置已保存")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving sovits config: {e}")




            

    def create_ai_draw_config_tab_content(self):
        # Create a main container with padding
        main_frame = ttk.Frame(self.ai_draw_config_tab, padding="20 15 20 15")
        main_frame.pack(fill="both", expand=True)
        
        # Add a title section
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text="AI 绘画配置", font=("Arial", 16, "bold"))
        title_label.pack(anchor="w")
        
        subtitle_label = ttk.Label(title_frame, text="配置和管理AI绘图服务接口", font=("Arial", 10))
        subtitle_label.pack(anchor="w", pady=(5, 0))
        
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=15)
        
        # === Configuration Selection Area ===
        config_selection_frame = ttk.LabelFrame(main_frame, text="配置管理", padding=(10, 5))
        config_selection_frame.pack(fill="x", pady=(0, 15))
        
        # Top row with main controls
        top_controls = ttk.Frame(config_selection_frame)
        top_controls.pack(fill="x", padx=5, pady=10)
        
        # Left side - AI Drawing switch and config selector
        left_controls = ttk.Frame(top_controls)
        left_controls.pack(side="left")
        
        # AI Drawing Switch with better label
        switch_frame = ttk.Frame(left_controls)
        switch_frame.pack(side="left", padx=(0, 15))
        
        self.cloud_on_var = tk.BooleanVar()
        ttk.Label(switch_frame, text="AI绘画功能:").pack(side="left", padx=(0, 10))
        self.cloud_on_switch = ttk.Checkbutton(
            switch_frame, 
            variable=self.cloud_on_var,
            command=self.save_ai_draw_switch,
            bootstyle="round-toggle"
        )
        self.cloud_on_switch.pack(side="left")
        
        # Config selection dropdown
        config_combo_frame = ttk.Frame(left_controls)
        config_combo_frame.pack(side="left", padx=(0, 15))
        
        ttk.Label(config_combo_frame, text="选择配置:").pack(side="left", padx=(0, 10))
        self.config_edit_combo = ttk.Combobox(config_combo_frame, state="readonly", width=25)
        self.config_edit_combo.pack(side="left")
        self.config_edit_combo.bind("<<ComboboxSelected>>", 
                                lambda event: [self.ai_draw_load_selected_config(event), 
                                            self.clear_dropdown_selection(event)])
        self.config_edit_combo.bind("<Button-1>", self.clear_dropdown_selection)
        
        # Right side - Config management buttons
        right_controls = ttk.Frame(top_controls)
        right_controls.pack(side="right")
        
        # Config management buttons with consistent styling
        button_frame = ttk.Frame(right_controls)
        button_frame.pack(side="right")
        
        # Create uniform buttons
        self.add_config_button = ttk.Button(
            button_frame, 
            text="➕ 新增", 
            command=self.ai_draw_add_config,
            width=10
        )
        self.add_config_button.pack(side="left", padx=(0, 5))
        
        self.copy_config_button = ttk.Button(
            button_frame, 
            text="📋 复制配置", 
            command=self.ai_draw_copy_config,
            width=10
        )
        self.copy_config_button.pack(side="left", padx=5)
        
        self.rename_config_button = ttk.Button(
            button_frame, 
            text="🖋 配置改名", 
            command=self.ai_draw_rename_config,
            bootstyle="secondary",
            width=10
        )
        self.rename_config_button.pack(side="left", padx=5)
        
        self.delete_config_button = ttk.Button(
            button_frame, 
            text="🗑 删除", 
            command=self.ai_draw_delete_config,
            bootstyle="danger",
            width=10
        )
        self.delete_config_button.pack(side="left", padx=5)
        
        # Advanced settings button (bottom row)
        advanced_frame = ttk.Frame(config_selection_frame)
        advanced_frame.pack(fill="x", padx=5, pady=(0, 5))
        
        self.person_background_config_button = ttk.Button(
            advanced_frame, 
            text="⚙️ 人物与背景绘画设置", 
            command=self.ai_draw_open_character_background_settings,
            style="Accent.TButton",
            width=25
        )
        self.person_background_config_button.pack(side="right")
        
        # === Configuration Content Area ===
        # Reduced height by setting a more compact notebook
        config_content = ttk.Notebook(main_frame)
        config_content.pack(fill="both", expand=True)
        
        # === General Settings Tab ===
        general_tab = ttk.Frame(config_content, padding=(10, 5))  # Reduced vertical padding
        config_content.add(general_tab, text="基本设置")
        
        # Shared parameters section - more compact
        shared_params_frame = ttk.LabelFrame(general_tab, text="共用参数", padding=(10, 3))  # Reduced vertical padding
        shared_params_frame.pack(fill="x", pady=(0, 5))  # Reduced bottom margin
        
        # Create a grid for parameters - more organized and compact layout
        params_grid = ttk.Frame(shared_params_frame)
        params_grid.pack(fill="x", padx=5, pady=5)  # Reduced vertical padding
        
        # Row 1: Max attempts and delay time
        ttk.Label(params_grid, text="最大尝试次数:").grid(row=0, column=0, sticky="w", padx=(5, 10), pady=3)  # Reduced padding
        self.max_attempts_entry = ttk.Entry(params_grid, width=8)
        self.max_attempts_entry.grid(row=0, column=1, sticky="w", padx=5, pady=3)  # Reduced padding
        self.max_attempts_entry.config(validate="key")
        vcmd_pos = (self.max_attempts_entry.register(self.ai_draw_validate_positive_int), '%P')
        self.max_attempts_entry.config(validatecommand=vcmd_pos)
        
        ttk.Label(params_grid, text="重试间隔 (秒):").grid(row=0, column=2, sticky="w", padx=(20, 10), pady=3)  # Reduced padding
        self.delay_time_entry = ttk.Entry(params_grid, width=8)
        self.delay_time_entry.grid(row=0, column=3, sticky="w", padx=5, pady=3)  # Reduced padding
        self.delay_time_entry.config(validate="key")
        vcmd_nat = (self.delay_time_entry.register(self.ai_draw_validate_natural_number), '%P')
        self.delay_time_entry.config(validatecommand=vcmd_nat)
        
        # Row 2: Max concurrency and background removal
        ttk.Label(params_grid, text="最大并发数:").grid(row=1, column=0, sticky="w", padx=(5, 10), pady=3)  # Reduced padding
        self.maxconcurrency_entry = ttk.Entry(params_grid, width=8)
        self.maxconcurrency_entry.grid(row=1, column=1, sticky="w", padx=5, pady=3)  # Reduced padding
        self.maxconcurrency_entry.config(validate="key", validatecommand=vcmd_pos)
        
        self.rembg_switch_var = tk.BooleanVar(value=False)
        self.rembg_switch = ttk.Checkbutton(
            params_grid, 
            text="使用本地rembg移除背景", 
            variable=self.rembg_switch_var, 
            bootstyle="round-toggle"
        )
        self.rembg_switch.grid(row=1, column=2, columnspan=2, sticky="w", padx=(20, 5), pady=3)  # Reduced padding
        
        # Request configuration section - more compact
        request_config_frame = ttk.LabelFrame(general_tab, text="请求配置", padding=(10, 3))  # Reduced vertical padding
        request_config_frame.pack(fill="x", pady=(0, 5))  # Reduced bottom margin
        
        # Request type selection
        req_type_frame = ttk.Frame(request_config_frame)
        req_type_frame.pack(fill="x", padx=5, pady=(5, 3))  # Reduced padding
        
        # Second request switch
        self.second_request_var = tk.BooleanVar(value=False)
        self.second_request_switch = ttk.Checkbutton(
            req_type_frame, 
            text="启用二次请求", 
            variable=self.second_request_var,
            command=self.ai_draw_toggle_second_request, 
            bootstyle="round-toggle"
        )
        self.second_request_switch.pack(side="left", padx=(5, 20))
        
        # Request selection (only visible when second request is enabled)
        self.request_selection_frame = ttk.Frame(req_type_frame)
        # Packing/Unpacking is handled by ai_draw_toggle_second_request
        ttk.Label(self.request_selection_frame, text="当前编辑:").pack(side="left", padx=(0, 5))
        self.request_type_var = tk.StringVar(value="一次请求")
        self.request_type_combo = ttk.Combobox(
            self.request_selection_frame, 
            textvariable=self.request_type_var,
            values=["一次请求", "二次请求"], 
            state="readonly", 
            width=10
        )
        self.request_type_combo.pack(side="left")
        self.request_type_combo.bind("<<ComboboxSelected>>", 
                                  lambda event: [self._ai_draw_switch_request_view(), 
                                              self.clear_dropdown_selection(event)])
        self.request_type_combo.bind("<Button-1>", self.clear_dropdown_selection)
        
        # URL and method frame
        url_frame = ttk.Frame(request_config_frame)
        url_frame.pack(fill="x", padx=5, pady=3)  # Reduced padding
        
        # URL with more space
        ttk.Label(url_frame, text="请求URL:").pack(side="left", padx=(5, 10))
        self.request_url_entry = ttk.Entry(url_frame)
        self.request_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        # Method and timeout together
        method_frame = ttk.Frame(url_frame)
        method_frame.pack(side="left")
        
        ttk.Label(method_frame, text="请求方法:").pack(side="left", padx=(0, 5))
        self.request_method_var = tk.StringVar(value="POST")
        self.request_method_combo = ttk.Combobox(
            method_frame, 
            textvariable=self.request_method_var,
            values=["POST", "GET"], 
            state="readonly", 
            width=8
        )
        self.request_method_combo.pack(side="left", padx=(0, 15))
        self.request_method_combo.bind("<<ComboboxSelected>>", 
                                    lambda event: [self.ai_draw_toggle_request_body(), 
                                                 self.clear_dropdown_selection(event)])
        self.request_method_combo.bind("<Button-1>", self.clear_dropdown_selection)
        
        ttk.Label(method_frame, text="超时时间 (秒):").pack(side="left")
        self.request_timeout_entry = ttk.Entry(method_frame, width=8)
        self.request_timeout_entry.pack(side="left", padx=5)
        self.request_timeout_entry.config(validate="key", validatecommand=vcmd_pos)
        
        # === Headers Tab ===
        headers_tab = ttk.Frame(config_content, padding=(10, 5))  # Reduced vertical padding
        config_content.add(headers_tab, text="请求头")
        
        # Headers control frame
        header_control_frame = ttk.Frame(headers_tab)
        header_control_frame.pack(fill="x", pady=(0, 5))  # Reduced padding
        
        # Header controls
        self.header_control_frame = ttk.Frame(header_control_frame)
        self.header_control_frame.pack(side="left")
        
        self.add_header_button = ttk.Button(
            self.header_control_frame, 
            text="➕ 新增请求头", 
            command=self.ai_draw_add_header,
            width=15
        )
        self.add_header_button.pack(side="left", padx=(0, 10))
        
        # Pagination placeholder
        self.header_page_combo = None
        self.header_page_var = None
        self.header_current_page = 1
        
        # Headers container - NO scrolling, using pagination instead
        self.headers_entries_frame = ttk.Frame(headers_tab)
        self.headers_entries_frame.pack(fill="x", expand=False)  # Only horizontal expansion
        
        self.headers_list = []  # List to store header entry tuples
        
        # === Request Body Tab ===
        body_tab = ttk.Frame(config_content, padding=(10, 15))  # Reduced vertical padding
        config_content.add(body_tab, text="请求体")
        
        # Request body frame (only shown for POST requests)
        self.request_body_placeholder_frame = ttk.Frame(body_tab)
        self.request_body_placeholder_frame.pack(fill="both",expand=True)
        
        self.request_body_frame = ttk.Frame(self.request_body_placeholder_frame)
        self.request_body_frame.pack(fill="both", expand=True)
        
        body_label_frame = ttk.Frame(self.request_body_frame)
        body_label_frame.pack(fill="x", pady=(0, 3))  # Reduced padding
        
        ttk.Label(body_label_frame, text="请求体 JSON:").pack(side="left")


        validate_json_button = ttk.Button(
            body_label_frame,
            text="检验JSON",
            command=self.validate_request_json,
            width=10
        )
        validate_json_button.pack(side="left", padx=10)
        
        # Add syntax highlighting hints
        body_help_label = ttk.Label(
            body_label_frame, 
            text="请按照JSON格式输入, {prompt}和{random}分别指代提示词和随机数", 
            foreground="gray"
        )
        body_help_label.pack(side="right")
        
        # Text widget with better styling - reduced height
        self.request_body_text = tk.Text(
            self.request_body_frame, 
            height=10,
            wrap="word",
            font=("Consolas", 10)  # Monospace font for better JSON editing
        )
        self.request_body_text.pack(fill="both", expand=True)
        

        
        # === Response Processing Tab ===
        response_tab = ttk.Frame(config_content, padding=(10, 5))  # Reduced vertical padding
        config_content.add(response_tab, text="响应处理")
        
        json_path_frame = ttk.Frame(response_tab)
        json_path_frame.pack(fill="x", pady=(0, 5))  # Reduced padding
        
        ttk.Label(json_path_frame, text="JSON路径:").pack(side="left", padx=(5, 10))
        self.json_path_entry = ttk.Entry(json_path_frame)
        self.json_path_entry.pack(side="left", fill="x", expand=True)
        
        ttk.Label(json_path_frame, text="解析响应:").pack(side="left", padx=(5, 10))
        self.parse_entry = ttk.Entry(json_path_frame)
        self.parse_entry.pack(side="left", fill="x", expand=True)
        
        # Conditions frame - more compact
        conditions_frame = ttk.LabelFrame(response_tab, text="响应条件", padding=(10, 3))  # Reduced vertical padding
        conditions_frame.pack(fill="x", pady=(0, 5))  # Reduced padding
        
        # Success condition
        success_frame = ttk.Frame(conditions_frame)
        success_frame.pack(fill="x", pady=3)  # Reduced padding
        
        ttk.Label(success_frame, text="成功条件:").pack(side="left", padx=(5, 10))
        self.success_condition_entry = ttk.Entry(success_frame)
        self.success_condition_entry.pack(side="left", fill="x", expand=True)
        
        # Failure condition
        fail_frame = ttk.Frame(conditions_frame)
        fail_frame.pack(fill="x", pady=3)  # Reduced padding
        
        ttk.Label(fail_frame, text="失败条件:").pack(side="left", padx=(5, 10))
        self.fail_condition_entry = ttk.Entry(fail_frame)
        self.fail_condition_entry.pack(side="left", fill="x", expand=True)

        # Forbid condition
        forbid_frame = ttk.Frame(conditions_frame)
        forbid_frame.pack(fill="x", pady=3)  # Reduced padding
        
        ttk.Label(forbid_frame, text="违禁条件:").pack(side="left", padx=(5, 10))
        self.forbid_condition_entry = ttk.Entry(forbid_frame)
        self.forbid_condition_entry.pack(side="left", fill="x", expand=True)

    
        # Save button at bottom
        save_frame = ttk.Frame(main_frame)
        save_frame.pack(fill="x", pady=(10, 0))  # Reduced top padding
        
        self.save_button = ttk.Button(
            save_frame, 
            text="💾 保存配置", 
            command=self.ai_draw_save_current_config,
            style="Accent.TButton",
            width=20
        )
        self.save_button.pack(side="right")


        self.max_attempts_entry.bind("<FocusIn>", lambda event: event.widget.selection_clear())
        self.json_path_entry.bind("<FocusIn>", lambda event: event.widget.selection_clear())
        
        # Initialization
        self.current_request_view_type = "一次请求"
        self.configs = self.ai_draw_load_config_names()
        self.ai_draw_load_all_configs()
        self._ai_draw_update_header_pagination()

    def _ai_draw_update_header_pagination(self):
        HEADERS_PER_PAGE=6
        """Updates header pagination controls and displays the correct items"""
        total_items = len(self.headers_list)
        total_pages = math.ceil(total_items / HEADERS_PER_PAGE)
        if total_pages == 0: total_pages = 1 # Ensure at least one page even if empty

        # Adjust current page if it's out of bounds (e.g., after deleting last item on a page)
        self.header_current_page = max(1, min(self.header_current_page, total_pages))

        page_values = list(range(1, total_pages + 1))

        # --- Manage Pagination Combobox ---
        if total_items > HEADERS_PER_PAGE: # Show combo only if more items than fit on one page
            if self.header_page_combo is None:
                # Create the combobox
                self.header_page_var = tk.IntVar(value=self.header_current_page)
                self.header_page_combo = ttk.Combobox(self.header_control_frame, # Parent is the control frame
                                                      textvariable=self.header_page_var,
                                                      values=page_values, state="readonly",
                                                      width=5, justify='center')
                self.header_page_combo.bind("<<ComboboxSelected>>", self._on_ai_draw_header_page_selected)
                self.header_page_combo.bind("<Button-1>", self.clear_dropdown_selection)
                # Pack it after the add button
                self.header_page_combo.pack(side=tk.LEFT, padx=5)
            else:
                # Update existing combobox
                # Note: Check if parent still exists before configuring, though unlikely needed here
                if self.header_page_combo.winfo_exists():
                    self.header_page_combo['values'] = page_values
                    self.header_page_var.set(self.header_current_page)
                    # Ensure it's packed if it was previously hidden
                    if not self.header_page_combo.winfo_manager():
                        self.header_page_combo.pack(side=tk.LEFT, padx=5)
        else:
            # Hide or destroy the combobox if it exists and is not needed
            if self.header_page_combo is not None and self.header_page_combo.winfo_exists():
                self.header_page_combo.pack_forget()
                # Optional: Destroy完全に if you prefer
                # self.header_page_combo.destroy()
                # self.header_page_combo = None
                # self.header_page_var = None

        # --- Display Headers for Current Page ---
        start_index = (self.header_current_page - 1) * HEADERS_PER_PAGE
        end_index = start_index + HEADERS_PER_PAGE

        # Hide all header frames first
        for _, _, frame in self.headers_list:
            if frame.winfo_exists(): # Check if frame exists before forgetting
                frame.pack_forget()

        # Show only those for the current page
        for i in range(start_index, min(end_index, total_items)):
             # Ensure the frame exists before trying to pack it
            if i < len(self.headers_list):
                _, _, frame = self.headers_list[i]
                if frame.winfo_exists():
                    frame.pack(fill=tk.X, pady=(0, 1)) # Pack with small vertical padding

    def _on_ai_draw_header_page_selected(self, event=None):
        """Handles header page selection change."""
        if self.header_page_combo and self.header_page_var:
            try:
                selected_page = self.header_page_var.get()
                if self.header_current_page != selected_page:
                    self.header_current_page = selected_page
                    self._ai_draw_update_header_pagination() # Update displayed items
            except tk.TclError:
                pass # Handle error during teardown
            except ValueError:
                print(f"Invalid header page number selected: {self.header_page_var.get()}")
        if event:
            self.clear_dropdown_selection(event)
            
    def validate_request_json(self):
        """检验JSON格式并替换测试变量"""
        try:
            # 获取当前请求体文本
            json_text = self.request_body_text.get("1.0", "end-1c")
            
            # 替换变量
            json_text = json_text.replace("{prompt}", "test").replace("{random}", "1")
            
            # 尝试解析JSON
            try:
                parsed_json = json.loads(json_text)
                self.show_message_bubble("Success", "检验通过")
            except json.JSONDecodeError as e:
                self.show_message_bubble("Error", f"JSON格式错误: {str(e)}")
                
        except Exception as e:
            self.show_message_bubble("Error", f"检验失败: {str(e)}")
    # --- Modifications to Existing Functions --

    def save_ai_draw_switch(self):
        self.config["AI_draw"]["cloud_on"] = self.cloud_on_var.get()
        self.save_config()

    def ai_draw_rename_config(self):
        current_config = self.config_edit_combo.get()
        if not current_config:
            messagebox.showerror("错误", "请选择要改名的配置！")
            return

        new_config_name = simpledialog.askstring("配置改名", "请输入新的配置名称:", initialvalue=current_config)
        if new_config_name:
            if new_config_name in self.config["AI_draw"]["configs"]:
                messagebox.showerror("错误", "配置名称已存在！")
                return

            # Rename in the list
            index = self.configs.index(current_config)
            self.configs[index] = new_config_name

            # Update comboboxes
            self.ai_draw_update_comboboxes()
            self.config_edit_combo.set(new_config_name)

            # Rename in config.json
            self.config["AI_draw"]["configs"][new_config_name] = self.config["AI_draw"]["configs"].pop(current_config)

            self.save_config()
            self.ai_draw_load_selected_config()
            self.show_message_bubble("Success", "配置已改名！")

    def ai_draw_copy_config(self):
        current_config = self.config_edit_combo.get()
        if not current_config:
            messagebox.showerror("错误", "请选择要复制的配置！")
            return

        new_config_name = simpledialog.askstring("复制配置", "请输入复制后的配置名称:")
        if new_config_name:
            if new_config_name in self.config["AI_draw"]["configs"]:
                messagebox.showerror("错误", "配置名称已存在！")
                return

            self.config["AI_draw"]["configs"][new_config_name] = self.config["AI_draw"]["configs"][current_config].copy()

            self.configs.append(new_config_name)
            self.ai_draw_update_comboboxes()
            self.config_edit_combo.set(new_config_name)
            self.save_config()
            self.ai_draw_load_selected_config()
            self.show_message_bubble("Success", "配置已复制！")

    def ai_draw_open_character_background_settings(self):
        self.character_background_window = tk.Toplevel(self.master)
        self.character_background_window.withdraw()
        self.character_background_window.title("人物与背景绘画设置")

        # Window settings
        window_width = 1000
        window_height = 800
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = int((screen_width / 2) - (window_width / 2))
        y = int((screen_height / 2) - (window_height / 2))
        self.character_background_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.character_background_window.resizable(False, False)


        self.character_background_window.resizable(False, False)
        self.character_background_window.transient(self.master)
        self.character_background_window.grab_set()



        # --- Notebook (Tabs) ---
        self.character_background_notebook = ttk.Notebook(self.character_background_window)
        self.character_tab = ttk.Frame(self.character_background_notebook)
        self.background_tab = ttk.Frame(self.character_background_notebook)
        self.judging_tab = ttk.Frame(self.character_background_notebook)
        self.processing_tab = ttk.Frame(self.character_background_notebook)
        self.character_background_notebook.add(self.character_tab, text="人物绘画配置区")
        self.character_background_notebook.add(self.background_tab, text="背景绘画配置区")
        self.character_background_notebook.add(self.judging_tab, text="判断生成质量")
        self.character_background_notebook.add(self.processing_tab, text="后处理")
        self.character_background_notebook.pack(expand=True, fill="both")

        self.ai_draw_create_character_tab_content(self.character_tab)
        self.ai_draw_create_background_tab_content(self.background_tab)
        self.ai_draw_create_judging_tab_content(self.judging_tab)
        self.ai_draw_create_processing_tab_content(self.processing_tab)

        self.character_background_window.geometry(f"{window_width}x{window_height}+{x}+{y}") # <--- 设置位置和大小
        self.character_background_window.update_idletasks() #Ensure updates

        self.character_background_window.deiconify()
        

        
    def ai_draw_create_judging_tab_content(self, parent):
        self.judging_queue = queue.Queue()
        self.current_test_filepath = None # To track the currently processing file
        """创建AI绘画图片质量判断标签页内容，采用更美观的布局"""
        # 创建主容器，使用内边距增加空间感
        main_container = ttk.Frame(parent, padding=(20, 15))
        main_container.pack(fill="both", expand=True)
        
        # ===== 标题区域 =====
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text="图片质量判断设置", font=("Microsoft YaHei", 16, "bold"))
        title_label.pack(side="left")
        
        subtitle_label = ttk.Label(title_frame, text="配置AI绘画结果的质量评估参数", font=("Microsoft YaHei", 10))
        subtitle_label.pack(side="left", padx=(15, 0), pady=(5, 0))
        
        ttk.Separator(main_container, orient="horizontal").pack(fill="x", pady=10)
        
        # ===== 质量判断方法选择区域 =====
        method_frame = ttk.LabelFrame(main_container, text="判断方法", padding=(15, 10))
        method_frame.pack(fill="x", pady=(0, 15))
        
        method_select_frame = ttk.Frame(method_frame)
        method_select_frame.pack(fill="x", pady=5)
        
        method_label = ttk.Label(method_select_frame, text="质量判断方法:", font=("Microsoft YaHei", 10, "bold"))
        method_label.pack(side="left", padx=(0, 10))
        
        # 添加质量判断方法下拉框
        self.quality_method_var = tk.StringVar(value="a")  # 默认选择方法a
        self.quality_method_combo = ttk.Combobox(
            method_select_frame,
            textvariable=self.quality_method_var,
            values=["a", "b", "c"],
            state="readonly",
            width=15
        )
        self.quality_method_combo.pack(side="left", padx=5)
        
        # 绑定方法切换事件
        # Ensure clear_dropdown_selection exists or remove binding
        # self.quality_method_combo.bind("<<ComboboxSelected>>", lambda e: [self.load_method_thresholds(), self.clear_dropdown_selection(e)])
        # self.quality_method_combo.bind("<Button-1>", self.clear_dropdown_selection)
        # Simplified binding if clear_dropdown_selection is not needed/defined:
        self.quality_method_combo.bind("<<ComboboxSelected>>", lambda e: self.load_method_thresholds())
        
        # 方法说明
        method_info_frame = ttk.Frame(method_frame)
        method_info_frame.pack(fill="x", pady=(5, 0))
        
        method_info_text = {
            "a": "方法A: 基于动态掩码和梯度幅值分位数的自适应锐度评估法",
            "b": "方法B: 基于人物特征识别和背景细节度评估",
            "c": "方法C: 基于综合美学分析和色彩协调度评估"
        }
        
        self.method_info_var = tk.StringVar(value=method_info_text["a"])
        method_info_label = ttk.Label(method_info_frame, textvariable=self.method_info_var, foreground="gray")
        method_info_label.pack(side="left")
        
        # 更新方法说明文本的函数
        def update_method_info(*args):
            selected_method = self.quality_method_var.get()
            self.method_info_var.set(method_info_text.get(selected_method, "未知方法"))
        
        self.quality_method_var.trace_add("write", update_method_info) # Use trace_add for modern Tkinter
        
        # ===== 启用/禁用开关区域 =====
        switch_frame = ttk.LabelFrame(main_container, text="质量判断开关", padding=(15, 10))
        switch_frame.pack(fill="x", pady=(0, 15))
        
        # 创建网格布局以保持对齐
        grid_frame = ttk.Frame(switch_frame)
        grid_frame.pack(fill="x", pady=5)
        
        # 人物绘画质量判断开关
        ttk.Label(grid_frame, text="人物绘画质量判断:", font=("Microsoft YaHei", 10)).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=8)
        
        self.character_quality_judgment_var = tk.BooleanVar()
        # Ensure bootstyle is available or use standard Checkbutton
        char_switch = ttk.Checkbutton(
            grid_frame, 
            variable=self.character_quality_judgment_var,
            # bootstyle="round-toggle" # May require ttkbootstrap
        )
        char_switch.grid(row=0, column=1, sticky="w", pady=8)
        
        # 背景绘画质量判断开关
        ttk.Label(grid_frame, text="背景绘画质量判断:", font=("Microsoft YaHei", 10)).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=8)
        
        self.background_quality_judgment_var = tk.BooleanVar()
        back_switch = ttk.Checkbutton(
            grid_frame, 
            variable=self.background_quality_judgment_var,
            # bootstyle="round-toggle" # May require ttkbootstrap
        )
        back_switch.grid(row=1, column=1, sticky="w", pady=8)
        
        # 开关说明
        switch_info = "启用质量判断后，系统将自动评估生成图像质量，低于阈值的图像将被丢弃并重新生成"
        ttk.Label(switch_frame, text=switch_info, foreground="gray", wraplength=500).pack(fill="x", pady=(5, 0))
        
        # ===== 阈值设置区域 =====
        threshold_frame = ttk.LabelFrame(main_container, text="质量阈值设置", padding=(15, 10))
        threshold_frame.pack(fill="x", pady=(0, 15))
        
        # 创建网格布局以保持对齐
        threshold_grid = ttk.Frame(threshold_frame)
        threshold_grid.pack(fill="x", pady=5)
        
        # 人物质量阈值
        ttk.Label(threshold_grid, text="人物质量阈值:", font=("Microsoft YaHei", 10)).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=8)
        
        self.character_quality_threshold_entry = ttk.Entry(threshold_grid, width=10)
        self.character_quality_threshold_entry.grid(row=0, column=1, sticky="w", padx=5, pady=8)
        
        ttk.Label(threshold_grid, text="(0-100)", foreground="gray").grid(row=0, column=2, sticky="w", padx=10, pady=8)
        
        # 背景质量阈值
        ttk.Label(threshold_grid, text="背景质量阈值:", font=("Microsoft YaHei", 10)).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=8)
        
        self.background_quality_threshold_entry = ttk.Entry(threshold_grid, width=10)
        self.background_quality_threshold_entry.grid(row=1, column=1, sticky="w", padx=5, pady=8)
        
        ttk.Label(threshold_grid, text="(0-100)", foreground="gray").grid(row=1, column=2, sticky="w", padx=10, pady=8)
        
        # 阈值说明
        threshold_info = "阈值范围为0-100，数值越高要求越严格。不同判断方法的推荐阈值可能有所不同。"
        ttk.Label(threshold_frame, text=threshold_info, foreground="gray", wraplength=1000).pack(fill="x", pady=(5, 0))
        
        # ===== 功能按钮区域 =====
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill="x", pady=(10, 0))
        
        # 测试按钮
        test_window_button = ttk.Button(
            button_frame, 
            text="🧪 测试质量判断", 
            command=self._open_judging_test_window, 
            width=20
        )
        test_window_button.pack(side="left", padx=(0, 10))
        
        # 保存按钮
        save_button = ttk.Button(
            button_frame, 
            text="💾 保存设置", 
            command=self.save_ai_draw_judging_config,
            # style="Accent.TButton", # May require ttkbootstrap
            width=15
        )
        save_button.pack(side="right")
        
        # ===== 状态栏 =====
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill="x", pady=(15, 0))
        
        self.judging_status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(status_frame, textvariable=self.judging_status_var)
        status_label.pack(side="left")
        
        # 初始化配置
        self.load_ai_draw_judging_config()
        
        # Modify save method locally within this setup if needed, 
        # or better, modify the actual self.save_ai_draw_judging_config method
        # to handle status updates. The original code already does this well.

    def _open_judging_test_window(self):
        """打开质量判断测试窗口"""
        # 保存当前设置 (确保这个方法本身不阻塞)
        self.save_ai_draw_judging_config()

        if hasattr(self, 'judging_status_var'):
            self.judging_status_var.set("正在打开测试窗口...")

        test_window = tk.Toplevel(self.master)
        test_window.withdraw()
        test_window.title("图片质量判断测试")
        test_window.geometry("650x750")
        test_window.transient(self.master)
        test_window.grab_set()
        test_window.resizable(False, False)

        # Need to store widgets or the window itself for later access by queue checker
        test_window.widgets = {} # Dictionary to hold key widgets

        # --- Make window closing graceful ---
        def on_close():
            # Optional: Add cleanup if needed (e.g., stop threads if applicable)
            test_window.grab_release()
            test_window.destroy()
        test_window.protocol("WM_DELETE_WINDOW", on_close)
        
        main_frame = ttk.Frame(test_window, padding=(20, 15))
        main_frame.pack(fill="both", expand=True)
        
        title_label = ttk.Label(main_frame, text="图片质量判断测试", font=("Microsoft YaHei", 16, "bold"))
        title_label.pack(pady=(0, 15))
        
        settings_frame = ttk.LabelFrame(main_frame, text="当前设置", padding=(15, 10))
        settings_frame.pack(fill="x", pady=(0, 15))
        
        settings_grid = ttk.Frame(settings_frame)
        settings_grid.pack(fill="x")
        
        ttk.Label(settings_grid, text="判断方法:", font=("Microsoft YaHei", 10, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 5), pady=3)
        ttk.Label(settings_grid, text=f"{self.quality_method_var.get()}").grid(row=0, column=1, sticky="w", padx=5, pady=3)
        ttk.Label(settings_grid, text="人物质量阈值:", font=("Microsoft YaHei", 10, "bold")).grid(row=1, column=0, sticky="w", padx=(0, 5), pady=3)
        ttk.Label(settings_grid, text=f"{self.character_quality_threshold_entry.get()}").grid(row=1, column=1, sticky="w", padx=5, pady=3)
        ttk.Label(settings_grid, text="背景质量阈值:", font=("Microsoft YaHei", 10, "bold")).grid(row=2, column=0, sticky="w", padx=(0, 5), pady=3)
        ttk.Label(settings_grid, text=f"{self.background_quality_threshold_entry.get()}").grid(row=2, column=1, sticky="w", padx=5, pady=3)
        
        test_area_frame = ttk.LabelFrame(main_frame, text="测试区域", padding=(15, 10))
        test_area_frame.pack(fill="both", expand=True, pady=(0, 15))
        test_window.widgets['test_area_frame'] = test_area_frame # Store reference

        init_prompt = ttk.Label(
            test_area_frame,
            text="请点击下方按钮选择一张图片进行质量评估测试",
            font=("Microsoft YaHei", 11),
            foreground="gray"
        )
        init_prompt.pack(pady=50)
        test_window.widgets['init_prompt'] = init_prompt # Store reference

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(0, 10))
        
        select_button = ttk.Button(
            button_frame,
            text="选择图片",
            # Pass the test_window context to the command
            command=lambda: self._select_test_image(test_window),
            width=15
        )
        select_button.pack(side="left", padx=(0, 10))
        test_window.widgets['select_button'] = select_button # Store reference
        
        close_button = ttk.Button(
            button_frame,
            text="关闭",
            command=on_close, # Use the safe closing function
            width=15
        )
        close_button.pack(side="right")
        
        test_window.update_idletasks()
        width = test_window.winfo_width()
        height = test_window.winfo_height()
        x = (test_window.winfo_screenwidth() // 2) - (width // 2)
        y = (test_window.winfo_screenheight() // 2) - (height // 2)
        test_window.geometry(f'{width}x{height}+{x}+{y}')
        test_window.deiconify()
        
        if hasattr(self, 'judging_status_var'):
            self.judging_status_var.set("测试窗口已打开")
            self.notebook.after(2000, lambda: self.judging_status_var.set("准备就绪"))

    def _select_test_image(self, test_window): # Pass test_window context
        """选择图片进行质量评估测试"""
        filepath = filedialog.askopenfilename(
            title="选择要测试的图片",
            filetypes=[("图像文件", "*.jpg;*.jpeg;*.png;*.bmp"), ("所有文件", "*.*")],
            parent=test_window # Make dialog modal to test window
        )

        if filepath:
            # Start processing in the background
            self._start_test_image_processing(filepath, test_window)

    def _start_test_image_processing(self, filepath, test_window):
        """Initiates image processing in a separate thread."""
        
        test_area_frame = test_window.widgets.get('test_area_frame')
        select_button = test_window.widgets.get('select_button')
        if not test_area_frame or not select_button:
             print("Error: Test window widgets not found.")
             return

        # --- 1. Update UI immediately (Clear previous, show processing) ---
        for widget in test_area_frame.winfo_children():
            widget.destroy() # Clear previous results/image

        # Disable button
        select_button.config(state=tk.DISABLED)
        
        # Show loading/processing indicator
        loading_label = ttk.Label(test_area_frame, text="正在加载和判断图片...", font=("Microsoft YaHei", 11), foreground="blue")
        loading_label.pack(pady=50)
        test_window.widgets['loading_label'] = loading_label

        # Store the filepath being processed
        self.current_test_filepath = filepath 

        # --- 2. Start the background thread ---
        thread = threading.Thread(
            target=self._run_judging_task,
            args=(filepath, self.judging_queue),
            daemon=True # AllowsQUADS program to exit even if thread is running
        )
        thread.start()

        # --- 3. Start polling the queue for results ---
        # Pass test_window context to the checker
        self.master.after(100, lambda: self._check_judging_queue(test_window))

    def _run_judging_task(self, filepath, q):
        """Worker function to run in a separate thread."""
        try:
            # --- Perform image loading and type detection (can stay here) ---
            # This part is usually fast unless images are enormous
            orig_img = Image.open(filepath)
            width, height = orig_img.size

            character_diff = abs(width - 1024) + abs(height - 1024)
            background_diff = abs(width - 1920) + abs(height - 1080)

            if character_diff <= background_diff:
                image_type = "character"
            else:
                image_type = "background"

            # --- Perform the potentially long-running task ---
            quality_score = self._judge_image_quality(filepath, width, height)

            # --- Put successful result into the queue ---
            # Include all necessary data for UI update
            q.put({
                "status": "success",
                "filepath": filepath,
                "score": quality_score,
                "image_type": image_type,
                "width": width,
                "height": height,
                "original_image": orig_img # Send the Pillow image object too
            })

        except Exception as e:
            # --- Put error into the queue ---
            print(f"Error in judging thread for {filepath}: {e}") # Log error
            q.put({
                "status": "error",
                "filepath": filepath,
                "error": str(e)
            })
        # Note: Don't access `self` directly for UI elements here. Pass data via queue.

    def _check_judging_queue(self, test_window):
        """Check the queue for results and update UI if available."""
        try:
            # Non-blocking check of the queue
            result = self.judging_queue.get_nowait()

            # --- Process the result (runs in the main thread) ---
            # Check if the window still exists and the result is for the current file
            if test_window.winfo_exists() and result.get("filepath") == self.current_test_filepath:
                 self._update_test_ui_with_result(result, test_window)
            else:
                # Result is old or window closed, discard
                print(f"Discarding stale result for {result.get('filepath')}")
                # Optionally, re-schedule check if needed for other tasks
                # self.master.after(100, lambda: self._check_judging_queue(test_window))

        except queue.Empty:
            # Queue is empty, check again later if the window still exists
             if test_window.winfo_exists():
                 self.master.after(100, lambda: self._check_judging_queue(test_window))

        except Exception as e:
             print(f"Error processing judging queue: {e}")
             select_button = test_window.widgets.get('select_button')
             if select_button and test_window.winfo_exists():
                 select_button.config(state=tk.NORMAL) # Re-enable button on error
             # Continue checking if window exists
             if test_window.winfo_exists():
                 self.master.after(100, lambda: self._check_judging_queue(test_window))

    def _update_test_ui_with_result(self, result, test_window):
        """Updates the test window UI with the judging result (runs in main thread)."""

        test_area_frame = test_window.widgets.get('test_area_frame')
        select_button = test_window.widgets.get('select_button')
        loading_label = test_window.widgets.get('loading_label')

        # --- Clear loading message ---
        if loading_label and loading_label.winfo_exists():
            loading_label.destroy()
            if 'loading_label' in test_window.widgets:
                 del test_window.widgets['loading_label']

        if not test_area_frame or not select_button:
            print("Error: Cannot update UI, test window widgets missing.")
            if select_button and select_button.winfo_exists():
                 select_button.config(state=tk.NORMAL) # Ensure button re-enabled
            return
        
        # --- Re-enable the select button ---
        select_button.config(state=tk.NORMAL)

        # --- Create the results display area ---
        result_frame = ttk.Frame(test_area_frame)
        result_frame.pack(fill="both", expand=True, padx=10, pady=0)
        test_window.widgets['result_frame'] = result_frame # Store if needed later

        if result["status"] == "error":
            # --- Display Error ---
            error_message = f"处理图像时发生错误：\n{result['error']}"
            error_label = ttk.Label(result_frame, text=error_message, foreground="red", wraplength=550, justify=tk.LEFT)
            error_label.pack(pady=20)
            
        elif result["status"] == "success":
             # --- Display Success Results ---
            try:
                filepath = result["filepath"]
                quality_score = result["score"]
                image_type = result["image_type"]
                width = result["width"]
                height = result["height"]
                orig_img = result["original_image"] # Get the image object

                type_label_text = "人物图片" if image_type == "character" else "背景图片"
                target_size = "1024×1024" if image_type == "character" else "1920×1080"
                
                # --- Display Image Preview ---
                max_width = 600
                max_height = 220
                img_copy = orig_img.copy() # Work with a copy

                if width > max_width or height > max_height:
                    scale = min(max_width / width, max_height / height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    # Use ANTIALIAS or BICUBIC for better quality downscaling if Pillow version supports it
                    # Use LANCZOS if available (newer Pillow) otherwise default RESAMPLE
                    resample_method = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS
                    img_resized = img_copy.resize((new_width, new_height), resample_method)

                else:
                    img_resized = img_copy

                tk_img = ImageTk.PhotoImage(img_resized)

                img_label = ttk.Label(result_frame, image=tk_img)
                img_label.image = tk_img # Keep reference! Crucial!
                img_label.pack(pady=0)

                # --- Display Scores and Results ---
                score_frame = ttk.Frame(result_frame)
                score_frame.pack(fill="x", pady=5)

                info_frame = ttk.Frame(score_frame)
                info_frame.pack(fill="x", pady=(0, 0))

                resolution_label = ttk.Label(info_frame, text=f"分辨率: {width} × {height}", font=("Microsoft YaHei", 10))
                resolution_label.pack(side="left", padx=(0, 20))

                type_label = ttk.Label(
                    info_frame,
                    text=f"图片类型: {type_label_text} (目标: {target_size})",
                    font=("Microsoft YaHei", 10, "bold"),
                    foreground="blue"
                )
                type_label.pack(side="left")

                quality_label = ttk.Label(score_frame, text=f"质量得分: {quality_score:.1f}", font=("Microsoft YaHei", 11, "bold"))
                quality_label.pack(anchor="w", pady=(0, 10))

                result_table = ttk.Frame(score_frame)
                result_table.pack(fill="x")

                if image_type == "character":
                    threshold_str = self.character_quality_threshold_entry.get()
                    threshold_name = "人物质量阈值"
                else:
                    threshold_str = self.background_quality_threshold_entry.get()
                    threshold_name = "背景质量阈值"
                
                try:
                    # Safely convert threshold to float
                    threshold_value = float(threshold_str) if threshold_str and threshold_str.replace(".", "", 1).isdigit() else 0.0
                except ValueError:
                    threshold_value = 0.0 # Default if conversion fails

                ttk.Label(result_table, text="阈值名称", font=("Microsoft YaHei", 10, "bold"), width=15).grid(row=0, column=0, padx=5, pady=2, sticky="w")
                ttk.Label(result_table, text="阈值", font=("Microsoft YaHei", 10, "bold"), width=8).grid(row=0, column=1, padx=5, pady=2, sticky="w")
                ttk.Label(result_table, text="结果", font=("Microsoft YaHei", 10, "bold"), width=8).grid(row=0, column=2, padx=5, pady=2, sticky="w")

                ttk.Label(result_table, text=threshold_name, width=15).grid(row=1, column=0, padx=5, pady=5, sticky="w")
                ttk.Label(result_table, text=f"{threshold_value:.1f}", width=8).grid(row=1, column=1, padx=5, pady=5, sticky="w")

                result_text = "通过" if quality_score >= threshold_value else "不通过"
                result_color = "green" if result_text == "通过" else "red"

                result_label = ttk.Label(
                    result_table,
                    text=result_text,
                    foreground=result_color,
                    width=8
                )
                result_label.grid(row=1, column=2, padx=5, pady=0, sticky="w")

            except Exception as e:
                # --- Error during UI update itself ---
                print(f"Error updating UI with success result: {e}")
                # Clear the frame and show an error message
                for widget in result_frame.winfo_children():
                    widget.destroy()
                error_message = f"显示结果时发生错误：\n{e}"
                error_label = ttk.Label(result_frame, text=error_message, foreground="red", wraplength=550, justify=tk.LEFT)
                error_label.pack(pady=20)
        
        # Reset current filepath tracker after processing is done for this file
        self.current_test_filepath = None

    def _judge_image_quality(self, image_path,width,height):
        """
        Judges image quality using an external executable.
        This function now runs in a separate thread via _run_judging_task.
        NOTE: Ensure game_directory is accessible. You might need to pass it
              or make it globally available/an instance variable accessible by the thread.
        """
        # Make sure game_directory is defined and accessible
        global game_directory # Or pass it as an argument if needed
        if 'game_directory' not in globals() and not hasattr(self, 'game_directory'):
             raise ValueError("game_directory is not defined")
        
        exec_dir = getattr(self, 'game_directory', game_directory) # Prefer instance variable if exists

        try:
            # Retrieve method from the UI var (Assuming it's up-to-date when thread starts)
            # It's generally safer to pass required config values to the thread function
            # instead of relying on UI vars directly from the thread.
            # However, for this specific blocking call, reading it just before might be okay.
            method = self.quality_method_var.get() # Read from UI Var - Potential race condition if user changes method DURING processing
            
            command = [
                os.path.join(exec_dir,"resize.exe"),
                f"method_{method}",
                image_path,
                str(width),
                str(height),
                method
            ]
            # Using CREATE_NO_WINDOW hides the console window for the subprocess
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            
            # Use subprocess.run (still blocks this *thread*, but not the main UI thread)
            result = subprocess.run(
                command,
                capture_output=True, # Capture stdout/stderr if needed for debugging
                text=True,          # Decode output as text
                check=False,         # Don't raise exception for non-zero exit code
                creationflags=creationflags,
                timeout=60 # Add a timeout (e.g., 60 seconds) to prevent indefinite hangs
            )

            # Check stderr for errors reported by resize.exe
            if result.stderr:
                print(f"resize.exe reported error for {image_path}: {result.stderr.strip()}")
            
            # Assuming the score is returned as the exit code
            score = float(result.returncode) # Convert exit code to float
            print(f"Judged {image_path} (Method {method}): Score {score}") # Logging
            return score

        except FileNotFoundError:
             print(f"Error: resize.exe not found at {os.path.join(exec_dir, 'resize.exe')}")
             raise # Re-raise to be caught by the calling thread function
        except subprocess.TimeoutExpired:
             print(f"Error: Timeout expired waiting for resize.exe on {image_path}")
             raise # Re-raise
        except Exception as e:
            print(f"Error during _judge_image_quality for {image_path}: {e}")
            raise # Re-raise the exception to be caught in _run_judging_task

    def load_method_thresholds(self):
        """根据选中的判断方法加载对应的阈值"""
        # Check if UI elements exist before accessing them
        if not hasattr(self, 'quality_method_var') or not hasattr(self, 'character_quality_threshold_entry'):
            # UI not fully initialized yet
            return

        selected_method = self.quality_method_var.get()
        
        # Ensure correct config structure
        judging_config = self.config.setdefault("AI_draw", {}).setdefault("judging_config", {})
        methods_config = judging_config.setdefault("methods", {})
        method_config = methods_config.get(selected_method, {}) # Use get for default empty dict
        
        # Clear existing input
        self.character_quality_threshold_entry.delete(0, tk.END)
        self.background_quality_threshold_entry.delete(0, tk.END)
        
        # Insert the method's thresholds, default to "" if not found
        character_threshold = method_config.get("character_quality_threshold", "")
        background_threshold = method_config.get("background_quality_threshold", "")
        
        self.character_quality_threshold_entry.insert(0, str(character_threshold))
        self.background_quality_threshold_entry.insert(0, str(background_threshold))
        
        if hasattr(self, 'judging_status_var'):
            self.judging_status_var.set(f"已加载方法 {selected_method} 的阈值设置")
            # Use self.master.after or the appropriate widget's after method
            self.master.after(2000, lambda: self.judging_status_var.set("准备就绪") if hasattr(self, 'judging_status_var') else None)

    def load_ai_draw_judging_config(self):
        """加载质量判断配置"""
        if not hasattr(self, 'config'):
            self.load_config() # Ensure config is loaded

        # Use setdefault for safer dictionary access and creation
        ai_draw_config = self.config.setdefault("AI_draw", {})
        judging_config = ai_draw_config.setdefault("judging_config", {})
        
        # Ensure default methods exist if 'methods' key is missing or empty
        default_methods = {
            "a": {"character_quality_threshold": "10", "background_quality_threshold": "15"},
            "b": {"character_quality_threshold": "65", "background_quality_threshold": "60"},
            "c": {"character_quality_threshold": "70", "background_quality_threshold": "65"}
        }
        if "methods" not in judging_config or not judging_config["methods"]:
             judging_config["methods"] = default_methods
        else:
             # Ensure all default methods are present if some exist
             for key, value in default_methods.items():
                 judging_config["methods"].setdefault(key, value)

        # Check if UI elements exist before setting them
        if hasattr(self, 'character_quality_judgment_var'):
             self.character_quality_judgment_var.set(judging_config.get("character_quality_judgment", False))
        if hasattr(self, 'background_quality_judgment_var'):
             self.background_quality_judgment_var.set(judging_config.get("background_quality_judgment", False))
        
        selected_method = judging_config.get("selected_method", "a")
        if hasattr(self, 'quality_method_var'):
            self.quality_method_var.set(selected_method)
        
            # Load thresholds for the selected method
            self.load_method_thresholds() # This will handle UI updates
        
        if hasattr(self, 'judging_status_var'):
            self.judging_status_var.set("配置已加载")
            self.master.after(2000, lambda: self.judging_status_var.set("准备就绪") if hasattr(self, 'judging_status_var') else None)

    def save_ai_draw_judging_config(self):
        """保存质量判断配置"""
        # Ensure UI elements exist before getting values
        if not hasattr(self, 'quality_method_var'):
             print("Warning: Cannot save judging config, UI not ready.")
             return

        ai_draw_config = self.config.setdefault("AI_draw", {})
        judging_config = ai_draw_config.setdefault("judging_config", {})
        methods_config = judging_config.setdefault("methods", {})
        
        selected_method = self.quality_method_var.get()
        
        # Ensure the dictionary for the selected method exists
        method_settings = methods_config.setdefault(selected_method, {})
        
        # Save current method's thresholds from UI input fields
        method_settings["character_quality_threshold"] = self.character_quality_threshold_entry.get().strip()
        method_settings["background_quality_threshold"] = self.background_quality_threshold_entry.get().strip()
        
        # Save switch states and selected method
        judging_config["character_quality_judgment"] = self.character_quality_judgment_var.get()
        judging_config["background_quality_judgment"] = self.background_quality_judgment_var.get()
        judging_config["selected_method"] = selected_method
        
        # Save the main config file
        self.save_config() 
        
        # Update status and show message bubble (if methods exist)
        if hasattr(self, 'judging_status_var'):
             self.judging_status_var.set("设置已保存")
             self.master.after(2000, lambda: self.judging_status_var.set("准备就绪") if hasattr(self, 'judging_status_var') else None)
        if hasattr(self, 'show_message_bubble'):
            self.show_message_bubble("Success", "质量判断设置已保存！")



        
    def ai_draw_create_processing_tab_content(self, parent):
        """创建AI绘画后处理标签页内容"""
        
        # 创建主容器，使用内边距增加空间感
        main_container = ttk.Frame(parent, padding=(20, 15))
        main_container.pack(fill="both", expand=True)
        
        # ===== 添加标题区域 =====
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text="AI绘画后处理设置", font=("Microsoft YaHei", 16, "bold"))
        title_label.pack(anchor="w")
        
        subtitle_label = ttk.Label(title_frame, text="配置图像处理选项和自动调整参数", font=("Microsoft YaHei", 10))
        subtitle_label.pack(anchor="w", pady=(5, 0))
        
        ttk.Separator(main_container, orient="horizontal").pack(fill="x", pady=15)
        
        # ===== rembg配置区域 =====
        rembg_frame = ttk.LabelFrame(main_container, text="背景去除设置 (rembg)", padding=(15, 10))
        rembg_frame.pack(fill="x", pady=(0, 15))
        
        # rembg位置设置
        rembg_location_frame = ttk.Frame(rembg_frame)
        rembg_location_frame.pack(fill="x", pady=5)
        
        self.rembg_location_label = ttk.Label(rembg_location_frame, text="rembg地址:", width=15)
        self.rembg_location_label.pack(side="left")
        
        self.rembg_location_entry = ttk.Entry(rembg_location_frame)
        self.rembg_location_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # rembg模型设置
        rembg_model_frame = ttk.Frame(rembg_frame)
        rembg_model_frame.pack(fill="x", pady=5)
        
        self.rembg_model_label = ttk.Label(rembg_model_frame, text="rembg模型:", width=15)
        self.rembg_model_label.pack(side="left")
        
        self.rembg_model_entry = ttk.Entry(rembg_model_frame)
        self.rembg_model_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        

        
        # 保存rembg设置按钮
        button_frame = ttk.Frame(rembg_frame)
        button_frame.pack(fill="x", pady=(5, 0))
        
        self.save_rembg_button = ttk.Button(
            button_frame, 
            text="💾 保存Rembg设置", 
            command=self.save_processing_config,
            style="Accent.TButton",
            width=20
        )
        self.save_rembg_button.pack(side="right")
        
        # ===== 分辨率调整设置区域 =====
        resolution_frame = ttk.LabelFrame(main_container, text="分辨率调整设置", padding=(15, 10))
        resolution_frame.pack(fill="x", pady=(0, 15))
        
        # === 人物分辨率调整 ===
        character_section = ttk.Frame(resolution_frame)
        character_section.pack(fill="x", pady=(0, 10))
        
        # 人物分辨率调整开关
        self.character_res_outer_frame = ttk.Frame(character_section)
        self.character_res_outer_frame.pack(fill="x", pady=5)
        
        self.character_resolution_var = tk.BooleanVar()
        self.character_resolution_switch = ttk.Checkbutton(
            self.character_res_outer_frame, 
            text="启用人物绘画分辨率调整",
            variable=self.character_resolution_var,
            bootstyle="round-toggle",
            command=lambda: self.toggle_character_resolution_settings(triggered_by_user=True)
        )
        self.character_resolution_switch.pack(side="left", padx=(0, 15))
        
        # 人物分辨率设置框架
        self.character_res_settings_frame = ttk.Frame(character_section)
        # 不立即pack，由toggle函数控制显示
        
        # 创建网格布局以保持对齐
        grid_frame = ttk.Frame(self.character_res_settings_frame)
        grid_frame.pack(fill="x")
        
        # 第一行：宽度和高度比例
        ttk.Label(grid_frame, text="宽度比例:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="e")
        self.character_width_combo = ttk.Combobox(
            grid_frame, 
            values=list(range(1, 17)), 
            state="readonly", 
            width=6
        )
        self.character_width_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(grid_frame, text="高度比例:").grid(row=0, column=2, padx=(15, 5), pady=5, sticky="e")
        self.character_height_combo = ttk.Combobox(
            grid_frame, 
            values=list(range(1, 17)), 
            state="readonly", 
            width=6
        )
        self.character_height_combo.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        # 第二行：调整方案
        ttk.Label(grid_frame, text="非指定比例方案:").grid(row=1, column=0, columnspan=2, padx=(0, 5), pady=5, sticky="e")
        self.character_resize_combo = ttk.Combobox(
            grid_frame, 
            values=["裁剪", "填充", "拉伸"], 
            state="readonly", 
            width=10
        )
        self.character_resize_combo.grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky="w")
        
        # 调整提示
        character_tip_frame = ttk.Frame(self.character_res_settings_frame)
        character_tip_frame.pack(fill="x", pady=(5, 0))
        
        character_tip = ttk.Label(
            character_tip_frame, 
            text="提示: 设置人物图像的宽高比例，非指定比例时的处理方式",
            foreground="gray",
            font=("Microsoft YaHei", 9)
        )
        character_tip.pack(side="left")
        
        # === 背景分辨率调整 ===
        background_section = ttk.Frame(resolution_frame)
        background_section.pack(fill="x", pady=(10, 0))
        
        # 背景分辨率调整开关
        self.background_res_outer_frame = ttk.Frame(background_section)
        self.background_res_outer_frame.pack(fill="x", pady=5)
        
        self.background_resolution_var = tk.BooleanVar()
        self.background_resolution_switch = ttk.Checkbutton(
            self.background_res_outer_frame, 
            text="启用背景绘画分辨率调整",
            variable=self.background_resolution_var,
            bootstyle="round-toggle",
            command=lambda: self.toggle_background_resolution_settings(triggered_by_user=True)
        )
        self.background_resolution_switch.pack(side="left", padx=(0, 15))
        
        # 背景分辨率设置框架
        self.background_res_settings_frame = ttk.Frame(background_section)
        # 不立即pack，由toggle函数控制显示
        
        bg_grid_frame = ttk.Frame(self.background_res_settings_frame)
        bg_grid_frame.pack(fill="x")
        
        ttk.Label(bg_grid_frame, text="非16:9比例方案:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="e")
        self.background_resize_combo = ttk.Combobox(
            bg_grid_frame, 
            values=["裁剪", "填充", "拉伸"], 
            state="readonly", 
            width=10
        )
        self.background_resize_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # 背景调整提示
        background_tip_frame = ttk.Frame(self.background_res_settings_frame)
        background_tip_frame.pack(fill="x", pady=(5, 0))
        
        background_tip = ttk.Label(
            background_tip_frame, 
            text="提示: 背景图像将自动调整为16:9比例，此选项控制调整方法",
            foreground="gray",
            font=("Microsoft YaHei", 9)
        )
        background_tip.pack(side="left")
        

        
        # 添加状态显示区域
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill="x", pady=(15, 0))
        
        self.processing_status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(status_frame, textvariable=self.processing_status_var)
        status_label.pack(side="left")
        


        # 绑定保存
        self.character_width_combo.bind("<<ComboboxSelected>>", self.save_processing_config)
        self.character_height_combo.bind("<<ComboboxSelected>>", self.save_processing_config)
        self.character_resize_combo.bind("<<ComboboxSelected>>", self.save_processing_config)
        self.background_resize_combo.bind("<<ComboboxSelected>>", self.save_processing_config)
        
        # ===== 绑定事件 =====
        # 绑定选择清除
        self.rembg_location_entry.bind("<FocusIn>", lambda event: event.widget.selection_clear())
        self.rembg_model_entry.bind("<FocusIn>", lambda event: event.widget.selection_clear())
        # ===== 加载配置并设置初始状态 =====
        self.load_processing_tab_config()  # 加载此标签页的特定设置
        self.toggle_character_resolution_settings(triggered_by_user=False)  # 设置初始可见性
        self.toggle_background_resolution_settings(triggered_by_user=False)  # 设置初始可见性

        # ===== 取消焦点 =====
        parent.focus_set()  # 初始将焦点设置到父框架
        
        # 更新原有save_processing_config函数以更新状态消息
        original_save = self.save_processing_config
        def save_with_status(*args, **kwargs):
            result = original_save(*args, **kwargs)
            self.processing_status_var.set("设置已保存")
            # 2秒后恢复状态消息
            parent.after(2000, lambda: self.processing_status_var.set("准备就绪"))
            return result
        self.save_processing_config = save_with_status

    def toggle_character_resolution_settings(self, triggered_by_user=False):
        """Shows or hides character resolution settings and sets defaults if triggered."""
        defaults_applied = False
        if self.character_resolution_var.get():
            self.character_res_settings_frame.pack(anchor=tk.W, pady=(2,0)) # Pack below switch
            if triggered_by_user:
                # Ensure config structure exists before accessing
                if not hasattr(self, 'config') or "AI_draw" not in self.config or "processing_config" not in self.config["AI_draw"]:
                    self.load_config() # Load or initialize config if missing

                processing_config = self.config["AI_draw"].get("processing_config", {})
                # Check and set defaults only if triggered by user and config is missing/empty
                if processing_config.get("character_width") is None or str(processing_config.get("character_width", "")).strip() == "":
                    self.character_width_combo.set("1")
                    defaults_applied = True
                if processing_config.get("character_height") is None or str(processing_config.get("character_height", "")).strip() == "":
                    self.character_height_combo.set("1")
                    defaults_applied = True
                if processing_config.get("character_resize") is None or str(processing_config.get("character_resize", "")).strip() == "":
                    self.character_resize_combo.set("裁剪")
                    defaults_applied = True
        else:
            self.character_res_settings_frame.pack_forget()

        # Save only if the toggle was triggered by the user action
        if triggered_by_user:
            self.save_processing_config(event=True) # Pass event=True to indicate user action for feedback

    def toggle_background_resolution_settings(self, triggered_by_user=False):
        """Shows or hides background resolution settings and sets defaults if triggered."""
        defaults_applied = False
        if self.background_resolution_var.get():
            self.background_res_settings_frame.pack(anchor=tk.W, pady=(2,0)) # Pack below switch
            if triggered_by_user:
                # Ensure config structure exists before accessing
                if not hasattr(self, 'config') or "AI_draw" not in self.config or "processing_config" not in self.config["AI_draw"]:
                    self.load_config() # Load or initialize config if missing

                processing_config = self.config["AI_draw"].get("processing_config", {})
                 # Check and set defaults only if triggered by user and config is missing/empty
                if processing_config.get("background_resize") is None or str(processing_config.get("background_resize", "")).strip() == "":
                    self.background_resize_combo.set("裁剪")
                    defaults_applied = True
        else:
            self.background_res_settings_frame.pack_forget()

        # Save only if the toggle was triggered by the user action
        if triggered_by_user:
            self.save_processing_config(event=True) # Pass event=True to indicate user action for feedback

    def load_processing_tab_config(self):
        """Loads the specific configurations for the processing tab."""
        # Ensure config is loaded and structure exists before accessing
        if not hasattr(self, 'config') or "AI_draw" not in self.config or "processing_config" not in self.config["AI_draw"]:
            self.load_config() # Make sure config is loaded

        processing_config = self.config["AI_draw"].get("processing_config", {})

        # Load rembg settings (with defaults if empty or missing)
        rembg_location = processing_config.get("rembg_location") if processing_config.get("rembg_location") else "http://localhost:7000/api/remove"
        rembg_model = processing_config.get("rembg_model") if processing_config.get("rembg_model") else "isnet-anime"

        self.rembg_location_entry.delete(0, tk.END)
        self.rembg_location_entry.insert(0, rembg_location)
        self.rembg_model_entry.delete(0, tk.END)
        self.rembg_model_entry.insert(0, rembg_model)

        # Load switch states
        self.character_resolution_var.set(processing_config.get("character_resolution", False))
        self.background_resolution_var.set(processing_config.get("background_resolution", False))

        # Load combobox values *if they exist* in the config, otherwise leave them empty initially
        # Default values are now handled by the toggle functions when triggered by user
        char_w = processing_config.get("character_width")
        self.character_width_combo.set(str(char_w) if char_w is not None else "")

        char_h = processing_config.get("character_height")
        self.character_height_combo.set(str(char_h) if char_h is not None else "")

        char_r = processing_config.get("character_resize")
        self.character_resize_combo.set(char_r if char_r else "")

        back_r = processing_config.get("background_resize")
        self.background_resize_combo.set(back_r if back_r else "")

        # Note: Initial visibility is set by calls to toggle functions after this load

    def save_processing_config(self, event=None):
        """Saves the current state of the processing tab configuration."""
         # Ensure config structure exists
        if "AI_draw" not in self.config:
            self.config["AI_draw"] = {}
        if "processing_config" not in self.config["AI_draw"]:
            self.config["AI_draw"]["processing_config"] = {}

        # Get values from Comboboxes
        char_width_val = self.character_width_combo.get()
        char_height_val = self.character_height_combo.get()
        char_resize_val = self.character_resize_combo.get()
        back_resize_val = self.background_resize_combo.get()

        processing_config = {
            "rembg_location": self.rembg_location_entry.get() or "http://localhost:7000/api/remove",
            "rembg_model": self.rembg_model_entry.get() or "isnet-anime",
            "character_resolution": self.character_resolution_var.get(),
            "background_resolution": self.background_resolution_var.get(),
             # Save only if the switch is ON and value is not empty, otherwise save None
            "character_width": int(char_width_val) if self.character_resolution_var.get() and char_width_val else None,
            "character_height": int(char_height_val) if self.character_resolution_var.get() and char_height_val else None,
            "character_resize": char_resize_val if self.character_resolution_var.get() and char_resize_val else None,
            "background_resize": back_resize_val if self.background_resolution_var.get() and back_resize_val else None,
        }

        # Clean up None values before assigning to self.config to keep config.json cleaner
        self.config["AI_draw"]["processing_config"] = {k: v for k, v in processing_config.items() if v is not None}

        self.save_config()
        # Optional: Provide feedback only if triggered by an event
        # The 'event=True' check handles calls from the toggle switches
        if event is not None:
            self.show_message_bubble("Success", "后处理配置已自动保存！")
        try:
            event.widget.selection_clear()
        except:
            pass





    def ai_draw_create_character_tab_content(self, parent):
        """创建人物绘画模型配置标签页内容，采用更美观的布局。"""
        # --- 初始化内部状态变量 ---
        self.character_config_entries = []
        self.character_current_page = 1
        self.character_page_combo = None
        self.character_entries_container = None
        
        # 创建主容器，使用内边距增加空间感
        main_container = ttk.Frame(parent, padding=(20, 15))
        main_container.pack(fill="both", expand=True)
        
        # ===== 标题区域 =====
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text="人物绘画模型配置", font=("Microsoft YaHei", 16, "bold"))
        title_label.pack(side="left")
        
        subtitle_label = ttk.Label(title_frame, text="配置AI绘画人物图片生成模型", font=("Microsoft YaHei", 10))
        subtitle_label.pack(side="left", padx=(15, 0), pady=(5, 0))
        
        ttk.Separator(main_container, orient="horizontal").pack(fill="x", pady=10)
        
        # ===== 设置区域 =====
        settings_frame = ttk.LabelFrame(main_container, text="基本设置", padding=(15, 10))
        settings_frame.pack(fill="x", pady=(0, 15))
        
        # 绘制非主要人物开关
        switch_frame = ttk.Frame(settings_frame)
        switch_frame.pack(fill="x", pady=10, padx=5)
        
        switch_label = ttk.Label(switch_frame, text="绘制非主要人物:", font=("Microsoft YaHei", 10, "bold"))
        switch_label.pack(side="left", padx=(0, 10))
        
        self.draw_non_main_character_var = tk.BooleanVar(value=False)
        self.draw_non_main_character_switch = ttk.Checkbutton(
            switch_frame, 
            text="启用", 
            variable=self.draw_non_main_character_var,
            bootstyle="round-toggle", 
            command=self.save_ai_draw_character_switch
        )
        self.draw_non_main_character_switch.pack(side="left")
        
        # 开关下方的说明文本
        help_text = "启用此功能后，系统将为故事中的非主要人物也生成AI绘画。注意：这会增加LLM模型和AI绘图的使用量。"
        help_label = ttk.Label(switch_frame, text=help_text, foreground="gray", wraplength=400)
        help_label.pack(side="left", padx=(20, 0))
        
        # ===== 模型配置列表区域 =====
        models_frame = ttk.LabelFrame(main_container, text="模型配置列表", padding=(15, 10))
        models_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 工具栏区域
        toolbar_frame = ttk.Frame(models_frame)
        toolbar_frame.pack(fill="x", pady=(0, 0))
        
        # 左侧按钮组
        left_buttons = ttk.Frame(toolbar_frame)
        left_buttons.pack(side="left")
        
        # 新增按钮
        self.add_character_config_button = ttk.Button(
            left_buttons, 
            text="➕ 新增模型", 
            command=lambda: self.ai_draw_add_config_entry(self.character_tab, self.character_config_entries, self.character_entries_container, 'character'),
            width=12
        )
        self.add_character_config_button.pack(side="left", padx=(0, 5))
        
        # 保存按钮
        self.save_character_config_button = ttk.Button(
            left_buttons, 
            text="💾 保存配置", 
            command=self.ai_draw_save_character_config,
            style="Accent.TButton",
            width=12
        )
        self.save_character_config_button.pack(side="left", padx=5)
        
        # 右侧帮助按钮
        right_buttons = ttk.Frame(toolbar_frame)
        right_buttons.pack(side="right")
        
        # 存储按钮框架引用以便分页控件使用
        self.character_button_frame = left_buttons
        
        # 帮助提示按钮
        tip_text = "开启绘制非主要人物则会尝试为配角生成AI绘画提示词并生成图片。这会增加LLM模型和AI绘图消耗量。程序优先选择优先级最高的图像生成模型，并在同等优先级的模型中，根据预设的权重分配生成任务，权重高的模型承担更多任务。当高优先级模型达到并发上限或生成失败时，程序会动态调整任务分配，或自动切换到较低优先级的模型继续生成。"
        self.character_hover_button = HoverButton(right_buttons, tooltip_text=tip_text)
        self.character_hover_button.pack(side="right")
        
        help_label = ttk.Label(right_buttons, text="说明", font=("Microsoft YaHei", 9))
        help_label.pack(side="right", padx=(0, 5))
        
        # 添加分隔线
        ttk.Separator(models_frame, orient="horizontal").pack(fill="x", pady=5)
        
        # 列表标题行
        header_frame = ttk.Frame(models_frame)
        header_frame.pack(fill="x", pady=(5, 8))
        
        # 使用网格布局确保对齐
        header_frame.columnconfigure(0, weight=55)  # 模型列
        header_frame.columnconfigure(1, weight=15)  # 权重列
        header_frame.columnconfigure(2, weight=15)  # 优先级列
        header_frame.columnconfigure(3, weight=15)  # 操作列
        
        model_label = ttk.Label(header_frame, text="模型", font=("Microsoft YaHei", 9, "bold"))
        model_label.grid(row=0, column=0, sticky="w", padx=5)
        
        weight_label = ttk.Label(header_frame, text="权重", font=("Microsoft YaHei", 9, "bold"))
        weight_label.grid(row=0, column=1, sticky="w", padx=5)
        
        priority_label = ttk.Label(header_frame, text="优先级", font=("Microsoft YaHei", 9, "bold"))
        priority_label.grid(row=0, column=2, sticky="w", padx=5)
        
        action_label = ttk.Label(header_frame, text="操作", font=("Microsoft YaHei", 9, "bold"))
        action_label.grid(row=0, column=3, sticky="w", padx=5)
        
        # 条目容器框架 - 使用Canvas和滚动条代替分页
        container_frame = ttk.Frame(models_frame)
        container_frame.pack(fill="both", expand=True)
        
        # 创建Canvas和滚动条
        canvas = tk.Canvas(container_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container_frame, orient="vertical", command=canvas.yview)
        
        canvas.pack(side="left", fill="both", expand=True)
        #scrollbar.pack(side="right", fill="y")



        def _character_scrollbar_set(first, last):
            # 当内容完全可见时隐藏滚动条
            if float(first) <= 0.0 and float(last) >= 1.0:
                scrollbar.pack_forget()
            else:
                # 内容不完全可见，需要显示滚动条
                if not scrollbar.winfo_ismapped():
                    scrollbar.pack(side="right", fill="y")
            scrollbar.set(first, last)

        canvas.configure(yscrollcommand=_character_scrollbar_set)

        

        
        # 创建内部框架用于存放配置条目
        self.character_entries_container = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=self.character_entries_container, anchor="nw", tags="self.character_entries_container")
        
        # 配置Canvas自适应大小
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
            update_character_scrollbar_visibility()
        
        def update_character_scrollbar_visibility():
            self.character_entries_container.update_idletasks()  # 确保测量正确
            content_height = self.character_entries_container.winfo_reqheight()
            canvas_height = canvas.winfo_height()
            
            if content_height <= canvas_height:
                scrollbar.pack_forget()  # 内容完全可见，隐藏滚动条
            else:
                if not scrollbar.winfo_ismapped():
                    scrollbar.pack(side="right", fill="y")  # 内容超出范围，显示滚动条
        
        canvas.bind("<Configure>", on_canvas_configure)
        self.character_entries_container.bind("<Configure>", 
            lambda e: (canvas.configure(scrollregion=canvas.bbox("all")), update_character_scrollbar_visibility()))
        


        self.character_canvas = canvas
        self.character_scrollbar = scrollbar
        self.update_character_scrollbar_visibility = update_character_scrollbar_visibility
        
        # 添加状态栏
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill="x", pady=(0, 0))
        
        self.character_status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(status_frame, textvariable=self.character_status_var)
        status_label.pack(side="left")
        
        priority_tip = ttk.Label(status_frame, text="提示: 优先级数值越高越优先使用，同级则按权重比例分配", foreground="gray")
        priority_tip.pack(side="right")
        
        # 加载配置
        self.ai_draw_load_character_config(self.character_tab, self.character_config_entries, self.character_entries_container)
        
        # 修改原有save函数，添加状态更新
        original_save = self.ai_draw_save_character_config
        def save_with_status(*args, **kwargs):
            result = original_save(*args, **kwargs)
            self.character_status_var.set("配置已保存")
            # 2秒后恢复状态消息
            parent.after(2000, lambda: self.character_status_var.set("准备就绪"))
            return result
        
        self.ai_draw_save_character_config = save_with_status
        
        self.character_canvas.bind_all("<MouseWheel>", self._on_character_mousewheel)  # Windows 滚轮
        self.character_canvas.bind_all("<Button-4>", self._on_character_mousewheel)  # Linux
        self.character_canvas.bind_all("<Button-5>", self._on_character_mousewheel)  # Linux

        self._bind_character_mousewheel(parent)
        

    def save_ai_draw_character_switch(self):
        self.config["AI_draw"]["draw_non_main_character"] = self.draw_non_main_character_var.get()
        self.save_config()

    def ai_draw_create_background_tab_content(self, parent):
        """创建背景绘画模型配置标签页内容，采用更美观的布局"""
        # --- 初始化内部状态变量 ---
        self.background_config_entries = []
        self.background_current_page = 1
        self.background_page_combo = None
        self.background_entries_container = None
        
        # 创建主容器，使用内边距增加空间感
        main_container = ttk.Frame(parent, padding=(20, 15))
        main_container.pack(fill="both", expand=True)
        
        # ===== 标题区域 =====
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text="背景绘画模型配置", font=("Microsoft YaHei", 16, "bold"))
        title_label.pack(side="left")
        
        subtitle_label = ttk.Label(title_frame, text="配置AI绘画背景图片生成模型", font=("Microsoft YaHei", 10))
        subtitle_label.pack(side="left", padx=(15, 0), pady=(5, 0))
        
        ttk.Separator(main_container, orient="horizontal").pack(fill="x", pady=10)
        
        # ===== 上下文设置区域 =====
        context_frame = ttk.LabelFrame(main_container, text="上下文设置", padding=(15, 10))
        context_frame.pack(fill="x", pady=(0, 15))
        
        # 上下文选项区域
        context_options_frame = ttk.Frame(context_frame)
        context_options_frame.pack(fill="x", pady=10)
        
        # 左侧 - 传入上下文选项
        left_options = ttk.Frame(context_options_frame)
        left_options.pack(side="left")
        
        self.convey_context_label = ttk.Label(left_options, text="传入上下文:", font=("Microsoft YaHei", 10, "bold"))
        self.convey_context_label.pack(side="left", padx=(0, 10))
        
        self.convey_context_var = tk.StringVar(value="不传入")
        self.convey_context_combo = ttk.Combobox(
            left_options, 
            textvariable=self.convey_context_var,
            values=["不传入", "部分传入", "全部传入"], 
            state="readonly", 
            width=15
        )
        self.convey_context_combo.pack(side="left", padx=5)
        self.convey_context_combo.bind("<<ComboboxSelected>>", 
                                     lambda event: [self.ai_draw_toggle_context_entry(event), 
                                                   self.clear_dropdown_selection(event), 
                                                   self.ai_draw_save_background_config()])
        self.convey_context_combo.bind("<Button-1>", self.clear_dropdown_selection)
        
        # 条数输入区域（初始隐藏）
        self.context_entry_label = ttk.Label(left_options, text="传入条数:", font=("Microsoft YaHei", 10))
        self.context_entry = ttk.Entry(left_options, width=8)
        self.context_entry.config(validate="key", 
                                validatecommand=(self.context_entry.register(self.ai_draw_validate_natural_number), '%P'))
        self.context_entry.bind("<FocusOut>", lambda event: self.ai_draw_save_background_config())
        
        # 右侧 - 上下文说明
        right_info = ttk.Frame(context_options_frame)
        right_info.pack(side="right", padx=(20, 0))
        
        context_info_text = "传入上下文选项决定AI绘画生成背景图时参考的对话数量，有助于使背景图更贴近故事情境。"
        context_info = ttk.Label(right_info, text=context_info_text, foreground="gray", wraplength=300)
        context_info.pack(side="right")
        
        # 初始化上下文条目显示状态
        self.ai_draw_toggle_context_entry()
        
        # ===== 模型配置列表区域 =====
        models_frame = ttk.LabelFrame(main_container, text="模型配置列表", padding=(15, 10))
        models_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 工具栏区域
        toolbar_frame = ttk.Frame(models_frame)
        toolbar_frame.pack(fill="x", pady=(0, 0))
        
        # 左侧按钮组
        left_buttons = ttk.Frame(toolbar_frame)
        left_buttons.pack(side="left")
        
        # 新增按钮
        self.add_background_config_button = ttk.Button(
            left_buttons, 
            text="➕ 新增模型", 
            command=lambda: self.ai_draw_add_config_entry(self.background_tab, self.background_config_entries, self.background_entries_container, 'background'),
            width=12
        )
        self.add_background_config_button.pack(side="left", padx=(0, 5))
        
        # 保存按钮
        self.save_background_config_button = ttk.Button(
            left_buttons, 
            text="💾 保存配置", 
            command=self.ai_draw_save_background_config,
            style="Accent.TButton",
            width=12
        )
        self.save_background_config_button.pack(side="left", padx=5)
        
        # 右侧帮助按钮
        right_buttons = ttk.Frame(toolbar_frame)
        right_buttons.pack(side="right")
        
        # 存储按钮框架引用以便分页控件使用
        self.background_button_frame = left_buttons
        
        # 帮助提示按钮
        tip_text = "传入上下文选项是指，LLM模型会传入最近对话的多少条来生成背景绘画提示词，这是为了使生成的背景图更贴近故事。程序优先选择优先级最高的图像生成模型，并在同等优先级的模型中，根据预设的权重分配生成任务，权重高的模型承担更多任务。当高优先级模型达到并发上限或生成失败时，程序会动态调整任务分配，或自动切换到较低优先级的模型继续生成。"
        self.background_hover_button = HoverButton(right_buttons, tooltip_text=tip_text)
        self.background_hover_button.pack(side="right")
        
        help_label = ttk.Label(right_buttons, text="说明", font=("Microsoft YaHei", 9))
        help_label.pack(side="right", padx=(0, 5))
        
        # 添加分隔线
        ttk.Separator(models_frame, orient="horizontal").pack(fill="x", pady=5)
        
        # 列表标题行
        header_frame = ttk.Frame(models_frame)
        header_frame.pack(fill="x", pady=(5, 8))
        
        # 使用网格布局确保对齐
        header_frame.columnconfigure(0, weight=55)  # 模型列
        header_frame.columnconfigure(1, weight=15)  # 权重列
        header_frame.columnconfigure(2, weight=15)  # 优先级列
        header_frame.columnconfigure(3, weight=15)  # 操作列
        
        model_label = ttk.Label(header_frame, text="模型", font=("Microsoft YaHei", 9, "bold"))
        model_label.grid(row=0, column=0, sticky="w", padx=5)
        
        weight_label = ttk.Label(header_frame, text="权重", font=("Microsoft YaHei", 9, "bold"))
        weight_label.grid(row=0, column=1, sticky="w", padx=5)
        
        priority_label = ttk.Label(header_frame, text="优先级", font=("Microsoft YaHei", 9, "bold"))
        priority_label.grid(row=0, column=2, sticky="w", padx=5)
        
        action_label = ttk.Label(header_frame, text="操作", font=("Microsoft YaHei", 9, "bold"))
        action_label.grid(row=0, column=3, sticky="w", padx=5)
        
        # 条目容器框架 - 使用Canvas和滚动条代替分页
        container_frame = ttk.Frame(models_frame)
        container_frame.pack(fill="both", expand=True)
        
        # 创建Canvas和滚动条
        canvas = tk.Canvas(container_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container_frame, orient="vertical", command=canvas.yview)
        
        canvas.pack(side="left", fill="both", expand=True)
        # 不立即pack滚动条，等待检查是否需要
        
        # 修改：使用自定义的scrollbar_set函数来控制滚动条显示/隐藏
        def _background_scrollbar_set(first, last):
            # 当内容完全可见时隐藏滚动条
            if float(first) <= 0.0 and float(last) >= 1.0:
                scrollbar.pack_forget()
            else:
                # 内容不完全可见，需要显示滚动条
                if not scrollbar.winfo_ismapped():
                    scrollbar.pack(side="right", fill="y")
            scrollbar.set(first, last)
        
        # 绑定Canvas和自定义的scrollbar_set函数
        canvas.configure(yscrollcommand=_background_scrollbar_set)
        
        # 创建内部框架用于存放配置条目
        self.background_entries_container = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=self.background_entries_container, anchor="nw", tags="self.background_entries_container")
        
        # 配置Canvas自适应大小
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
            # 检查内容高度，决定是否需要滚动条
            update_background_scrollbar_visibility()
        
        # 检查是否需要显示滚动条
        def update_background_scrollbar_visibility():
            self.background_entries_container.update_idletasks()  # 确保测量正确
            content_height = self.background_entries_container.winfo_reqheight()
            canvas_height = canvas.winfo_height()
            
            if content_height <= canvas_height:
                scrollbar.pack_forget()  # 内容完全可见，隐藏滚动条
            else:
                if not scrollbar.winfo_ismapped():
                    scrollbar.pack(side="right", fill="y")  # 内容超出范围，显示滚动条
        
        canvas.bind("<Configure>", on_canvas_configure)
        self.background_entries_container.bind("<Configure>", 
            lambda e: (canvas.configure(scrollregion=canvas.bbox("all")), update_background_scrollbar_visibility()))
        
        
        # 存储对scrollbar和canvas的引用，用于其他方法中更新滚动条状态
        self.background_canvas = canvas
        self.background_scrollbar = scrollbar
        self.update_background_scrollbar_visibility = update_background_scrollbar_visibility
        
        # 添加状态栏
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill="x", pady=(0, 0))
        
        self.background_status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(status_frame, textvariable=self.background_status_var)
        status_label.pack(side="left")
        
        priority_tip = ttk.Label(status_frame, text="提示: 优先级数值越高越优先使用，同级则按权重比例分配", foreground="gray")
        priority_tip.pack(side="right")
        
        # 加载配置
        self.ai_draw_load_background_config(self.background_tab, self.background_config_entries, self.background_entries_container)
        
        # 修改原有保存函数，添加状态更新功能
        original_save = self.ai_draw_save_background_config
        
        def save_with_status(*args, **kwargs):
            result = original_save(*args, **kwargs)
            # 仅当作为直接保存操作时显示状态消息
            if args and isinstance(args[0], tk.Event) and args[0].widget == self.save_background_config_button:
                self.background_status_var.set("配置已保存")
                # 2秒后恢复状态消息
                parent.after(2000, lambda: self.background_status_var.set("准备就绪"))
            elif not args:  # 无参数调用也视为直接保存
                self.background_status_var.set("配置已保存")
                # 2秒后恢复状态消息
                parent.after(2000, lambda: self.background_status_var.set("准备就绪"))
            return result
        
        self.ai_draw_save_background_config = save_with_status

        self.background_canvas.bind_all("<MouseWheel>", self._on_background_mousewheel) #windows
        self.background_canvas.bind_all("<Button-4>", self._on_background_mousewheel)  # Linux scroll up
        self.background_canvas.bind_all("<Button-5>", self._on_background_mousewheel)  # Linux scroll down
        self._bind_background_mousewheel(parent)
        self.convey_context_combo.bind("<MouseWheel>", lambda event: "break")
        #print("binding combos")

    def ai_draw_add_config_entry(self, parent, config_entries, entries_container, tab_type):
        """添加新的配置条目行到UI和内部列表，改进布局。"""
        if not entries_container:
            print(f"错误：{tab_type} 的条目容器未初始化。")
            return
        
        # 创建条目框架，使用ttk.Frame以获得更好的样式
        entry_frame = ttk.Frame(entries_container)
        # 设置交替背景色以提高可读性
        if len(config_entries) % 2 == 0:
            entry_frame.configure(style="EvenRow.TFrame")
        else:
            entry_frame.configure(style="OddRow.TFrame")
        
        # 使用网格布局代替流式布局
        entry_frame.columnconfigure(0, weight=55)  # 模型列
        entry_frame.columnconfigure(1, weight=15)  # 权重列
        entry_frame.columnconfigure(2, weight=15)  # 优先级列
        entry_frame.columnconfigure(3, weight=15)  # 操作列
        
        # 模型下拉菜单
        model_var = tk.StringVar()
        # 使用self.configs保存可用的AI绘画配置名称
        available_models = getattr(self, 'configs', [])
        model_combo = ttk.Combobox(
            entry_frame, 
            textvariable=model_var, 
            values=available_models, 
            state="readonly", 
            width=30
        )
        model_combo.grid(row=0, column=0, padx=5, pady=3, sticky="w")
        model_combo.bind("<<ComboboxSelected>>", self.clear_dropdown_selection)
        model_combo.bind("<Button-1>", self.clear_dropdown_selection)
        
        # 权重输入框（仅允许正整数）
        weight_var = tk.StringVar(value="1")  # 默认权重为1
        weight_entry = ttk.Entry(entry_frame, textvariable=weight_var, width=8)
        weight_entry.grid(row=0, column=1, padx=5, pady=3, sticky="w")
        weight_entry.config(validate="key")
        vcmd_positive_int = (weight_entry.register(self.ai_draw_validate_positive_int), '%P')
        weight_entry.config(validatecommand=vcmd_positive_int)
        
        # 优先级输入框（仅允许非负整数）
        priority_var = tk.StringVar(value="0")  # 默认优先级为0
        priority_entry = ttk.Entry(entry_frame, textvariable=priority_var, width=8)
        priority_entry.grid(row=0, column=2, padx=5, pady=3, sticky="w")
        priority_entry.config(validate="key")
        vcmd_natural_num = (priority_entry.register(self.ai_draw_validate_natural_number), '%P')
        priority_entry.config(validatecommand=vcmd_natural_num)
        
        # 操作按钮组
        action_frame = ttk.Frame(entry_frame)
        action_frame.grid(row=0, column=3, padx=5, pady=3, sticky="w")
        
        # 删除按钮
        delete_button = ttk.Button(
            action_frame, 
            text="🗑", 
            width=3,
            command=lambda ef=entry_frame, ce=config_entries, tt=tab_type: self._ai_draw_delete_config_entry_wrapper(ef, ce, tt),
            bootstyle="danger"
        )
        delete_button.pack(side="left", padx=(0, 5))
        
        # 测试按钮
        test_button = ttk.Button(
            action_frame, 
            text="🔍", 
            width=3,
            command=lambda mv=model_var, p=parent: self.ai_draw_test_config(mv.get(), p)
        )
        test_button.pack(side="left")
        
        # 将数据保存到条目数据中
        entry_data = {
            "frame": entry_frame,
            "model_var": model_var,
            "model_combo": model_combo,
            "weight_var": weight_var,
            "weight_entry": weight_entry,
            "priority_var": priority_var,
            "priority_entry": priority_entry
        }
        config_entries.append(entry_data)
        # 直接在容器中显示新条目
        entry_frame.pack(fill="x", pady=1)
        
        # 更新滚动条可见性
        if tab_type == 'character' and hasattr(self, 'update_character_scrollbar_visibility'):
            self.update_character_scrollbar_visibility()
        elif tab_type == 'background' and hasattr(self, 'update_background_scrollbar_visibility'):
            self.update_background_scrollbar_visibility()
        
        # 显示状态消息
        if tab_type == 'character':
            self.character_status_var.set("已添加新模型配置")
            parent.after(2000, lambda: self.character_status_var.set("准备就绪"))
        elif tab_type == 'background':
            if hasattr(self, 'background_status_var'):
                self.background_status_var.set("已添加新模型配置")
                parent.after(2000, lambda: self.background_status_var.set("准备就绪"))

    def _bind_character_mousewheel(self, widget):
        """Recursively binds mousewheel events to a widget and its children. (Character)"""
        widget.bind("<MouseWheel>", self._on_character_mousewheel) # Bind to the widget
        widget.bind("<Button-4>", self._on_character_mousewheel)  # Linux scroll up
        widget.bind("<Button-5>", self._on_character_mousewheel)  # Linux scroll down

        for child in widget.winfo_children():
            self._bind_character_mousewheel(child) # And to its children!

    def _bind_background_mousewheel(self, widget):
        """Recursively binds mousewheel events to a widget and its children. (Background)"""
        widget.bind("<MouseWheel>", self._on_background_mousewheel) # Bind to the widget
        widget.bind("<Button-4>", self._on_background_mousewheel)  # Linux scroll up
        widget.bind("<Button-5>", self._on_background_mousewheel)  # Linux scroll down

        for child in widget.winfo_children():
            self._bind_background_mousewheel(child) # And to its children!

    def _on_character_mousewheel(self, event):
        """Character Model Config Canvas Scroll"""
        try:
            widget = event.widget

            while widget:
                if widget.winfo_class() == 'Combobox':
                    return  # If in Combobox don't do anything
                widget = widget.master

            if event.num == 4: # For Linux
                self.character_canvas.yview_scroll(-1, "units")
            elif event.num == 5: # For Linux
                self.character_canvas.yview_scroll(1, "units")
            else:  # For Windows
                self.character_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except:
            pass

    def _on_background_mousewheel(self, event):
        try:
            """Background Model config Canvas Scroll"""
            widget = event.widget
            while widget:
                if widget.winfo_class() == 'TCombobox':
                    return  # If in Combobox don't do anything
                widget = widget.master

            if event.num == 4: # For Linux
                self.background_canvas.yview_scroll(-1, "units")
            elif event.num == 5: # For Linux
                self.background_canvas.yview_scroll(1, "units")
            else:  # For Windows
                self.background_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except:
            pass
            
    def _on_ai_draw_character_background_page_selected(self, event, tab_type):
        """Handles selection change in the pagination combobox."""
        if tab_type == 'character':
            page_combo = self.character_page_combo
            if not page_combo: return
            try:
                selected_page = int(page_combo.get())
                self.character_current_page = selected_page
            except ValueError:
                return # Ignore if value isn't an int somehow
        elif tab_type == 'background':
            page_combo = self.background_page_combo
            if not page_combo: return
            try:
                selected_page = int(page_combo.get())
                self.background_current_page = selected_page
            except ValueError:
                return
        else:
            return

        self.clear_dropdown_selection(event) # Clear focus highlight

    def ai_draw_test_config(self,model,name):
        if str(name).endswith("frame"):
            kind='character'
        else:
            kind='background'
        threading.Thread(target=self._ai_draw_test_config, args=(str(model),str(kind),)).start()
        self.show_message_bubble("","开始测试，详细信息请看日志")

    def _ai_draw_test_config(self,model,kind):
        try:
            result=gui_functions.test_ai_draw(model,kind)
            if result=="success":
                self.show_message_bubble("Success",f"{model}模型测试通过")
            else:
                self.show_message_bubble("Error","模型测试未通过")
        except AttributeError:
            self.show_message_bubble("Error","模型测试未通过")
        except Exception as e:

            messagebox.showerror("Error", f"Error calling test_ai_draw: {e}")

    def ai_draw_delete_config_entry(self, entry_frame, config_entries):
        for entry in config_entries:
            if entry["frame"] == entry_frame:
                entry["frame"].destroy()
                config_entries.remove(entry)
                break
    def _ai_draw_delete_config_entry_wrapper(self, entry_frame, config_entries, tab_type):
        """调用删除并更新UI的包装器"""
        self.ai_draw_delete_config_entry(entry_frame, config_entries)
        
        # 更新配置项的交替背景色
        for i, entry in enumerate(config_entries):
            if i % 2 == 0:
                entry["frame"].configure(style="EvenRow.TFrame")
            else:
                entry["frame"].configure(style="OddRow.TFrame")
        
        # 更新滚动条可见性
        if tab_type == 'character' and hasattr(self, 'update_character_scrollbar_visibility'):
            self.update_character_scrollbar_visibility()
        elif tab_type == 'background' and hasattr(self, 'update_background_scrollbar_visibility'):
            self.update_background_scrollbar_visibility()
        
        # 更新状态消息
        if tab_type == 'background' and hasattr(self, 'background_status_var'):
            self.background_status_var.set("已删除一项配置")
            # 2秒后恢复状态消息
            self.background_tab.after(2000, lambda: self.background_status_var.set("准备就绪"))
        elif tab_type == 'character' and hasattr(self, 'character_status_var'):
            self.character_status_var.set("已删除一项配置")
            # 2秒后恢复状态消息
            self.character_tab.after(2000, lambda: self.character_status_var.set("准备就绪"))

    def ai_draw_validate_positive_int(self, new_value):
        if new_value == "":
            return True
        try:
            value = int(new_value)
            return value > 0
        except ValueError:
            return False

    def ai_draw_validate_natural_number(self, new_value):
        if new_value == "":
            return True
        try:
            value = int(new_value)
            return value >= 0
        except ValueError:
            return False

    def ai_draw_load_character_config(self, parent, config_entries, entries_container):
        """加载人物配置，在条目容器中创建UI元素，采用新的布局。"""
        # 清除现有条目列表和UI容器
        config_entries.clear()
        for widget in entries_container.winfo_children():
            widget.destroy()
        
        config_data = self.config["AI_draw"].get('character_config', [])
        try:
            # 确保数据是列表
            if not isinstance(config_data, list):
                print("警告：人物配置数据不是列表。正在重置。")
                config_data = []
                self.config["AI_draw"]['character_config'] = []  # 在配置中修复
            
            # 根据优先级（降序）和权重（降序）对配置数据进行排序
            config_data.sort(key=lambda x: (-int(x.get('priority', 0)), -int(x.get('weigh', 1))))
            
            for i, item in enumerate(config_data):
                # 创建条目UI
                entry_frame = ttk.Frame(entries_container)
                # 设置交替背景色以提高可读性
                if i % 2 == 0:
                    entry_frame.configure(style="EvenRow.TFrame")
                else:
                    entry_frame.configure(style="OddRow.TFrame")
                
                # 使用网格布局代替流式布局
                entry_frame.columnconfigure(0, weight=55)  # 模型列
                entry_frame.columnconfigure(1, weight=15)  # 权重列
                entry_frame.columnconfigure(2, weight=15)  # 优先级列
                entry_frame.columnconfigure(3, weight=15)  # 操作列
                
                model_var = tk.StringVar(value=item.get("config", ""))
                available_models = getattr(self, 'configs', [])
                model_combo = ttk.Combobox(
                    entry_frame, 
                    textvariable=model_var, 
                    values=available_models, 
                    state="readonly", 
                    width=30
                )
                model_combo.grid(row=0, column=0, padx=5, pady=3, sticky="w")
                model_combo.bind("<<ComboboxSelected>>", self.clear_dropdown_selection)
                model_combo.bind("<Button-1>", self.clear_dropdown_selection)
                
                weight_var = tk.StringVar(value=str(item.get("weigh", 1)))
                weight_entry = ttk.Entry(entry_frame, textvariable=weight_var, width=8)
                weight_entry.grid(row=0, column=1, padx=5, pady=3, sticky="w")
                weight_entry.config(validate="key")
                vcmd_positive_int = (weight_entry.register(self.ai_draw_validate_positive_int), '%P')
                weight_entry.config(validatecommand=vcmd_positive_int)
                
                priority_var = tk.StringVar(value=str(item.get("priority", 0)))
                priority_entry = ttk.Entry(entry_frame, textvariable=priority_var, width=8)
                priority_entry.grid(row=0, column=2, padx=5, pady=3, sticky="w")
                priority_entry.config(validate="key")
                vcmd_natural_num = (priority_entry.register(self.ai_draw_validate_natural_number), '%P')
                priority_entry.config(validatecommand=vcmd_natural_num)
                
                # 操作按钮组
                action_frame = ttk.Frame(entry_frame)
                action_frame.grid(row=0, column=3, padx=5, pady=3, sticky="w")
                
                # 删除按钮
                delete_button = ttk.Button(
                    action_frame, 
                    text="🗑", 
                    width=3,
                    command=lambda ef=entry_frame, ce=config_entries, tt='character': self._ai_draw_delete_config_entry_wrapper(ef, ce, tt),
                    bootstyle="danger"
                )
                delete_button.pack(side="left", padx=(0, 5))
                
                # 测试按钮
                test_button = ttk.Button(
                    action_frame, 
                    text="🔍", 
                    width=3,
                    command=lambda mv=model_var, p=parent: self.ai_draw_test_config(mv.get(), p)
                )
                test_button.pack(side="left")
                
                # 将创建的元素和数据添加到内部列表
                config_entries.append({
                    "frame": entry_frame,
                    "model_var": model_var, "model_combo": model_combo,
                    "weight_var": weight_var, "weight_entry": weight_entry,
                    "priority_var": priority_var, "priority_entry": priority_entry
                })
                entry_frame.pack(fill="x", pady=1)

        except Exception as e: # 捕获更广泛的异常
            print(f"加载/处理人物配置时出错: {e}")
            messagebox.showerror("配置加载错误", f"加载人物配置时出错: {e}\n\n配置可能已损坏，请检查或重置。")

        # 加载"绘制非主要人物"开关状态
        self.draw_non_main_character_var.set(self.config["AI_draw"].get("draw_non_main_character", False))
        
        # 加载完成后检查滚动条可见性
        if hasattr(self, 'update_character_scrollbar_visibility'):
            # 延迟一下以确保布局更新完成
            parent.after(100, self.update_character_scrollbar_visibility)
        
        # 更新状态
        if hasattr(self, 'character_status_var'):
            self.character_status_var.set("配置已加载")
            # 2秒后恢复状态消息
            parent.after(2000, lambda: self.character_status_var.set("准备就绪"))

    def ai_draw_save_character_config(self):
        """Saves character config based on the *entire* internal list."""
        config_data = []
        # Iterate through the full list, not just the visible ones
        for entry in self.character_config_entries:
            try:
                weight = int(entry["weight_var"].get())
                priority = int(entry["priority_var"].get())
                model = entry["model_var"].get()
                if not model: # Skip empty model selections
                    print("Skipping character entry with no model selected.")
                    continue
                config_data.append({
                    "config": model,
                    "weigh": weight,
                    "priority": priority
                })
            except ValueError:
                messagebox.showerror("错误", "权重和优先级必须是有效的整数！")
                return # Stop saving if invalid data found
            except KeyError:
                messagebox.showerror("内部错误", "无法访问配置条目数据。")
                return

        self.config["AI_draw"]["character_config"] = config_data

        # Save the "绘制非主要人物" switch state
        self.config["AI_draw"]["draw_non_main_character"] = self.draw_non_main_character_var.get()
        self.save_config()
        self.show_message_bubble("Success", "人物配置已保存！")

    def ai_draw_load_background_config(self, parent, config_entries, entries_container):
        """加载背景配置，在条目容器中创建UI元素，采用新的布局。"""
        # 清除现有条目列表和UI容器
        config_entries.clear()
        for widget in entries_container.winfo_children():
            widget.destroy()
        
        config_data = self.config["AI_draw"].get('background_config', [])
        try:
            # 确保数据是列表
            if not isinstance(config_data, list):
                print("警告：背景配置数据不是列表。正在重置。")
                config_data = []
                self.config["AI_draw"]['background_config'] = []  # 在配置中修复
            
            # 根据优先级（降序）和权重（降序）对配置数据进行排序
            config_data.sort(key=lambda x: (-int(x.get('priority', 0)), -int(x.get('weigh', 1))))
            
            for i, item in enumerate(config_data):
                # 创建条目UI
                entry_frame = ttk.Frame(entries_container)
                # 设置交替背景色以提高可读性
                if i % 2 == 0:
                    entry_frame.configure(style="EvenRow.TFrame")
                else:
                    entry_frame.configure(style="OddRow.TFrame")
                
                # 使用网格布局代替流式布局
                entry_frame.columnconfigure(0, weight=55)  # 模型列
                entry_frame.columnconfigure(1, weight=15)  # 权重列
                entry_frame.columnconfigure(2, weight=15)  # 优先级列
                entry_frame.columnconfigure(3, weight=15)  # 操作列
                
                model_var = tk.StringVar(value=item.get("config", ""))
                available_models = getattr(self, 'configs', [])
                model_combo = ttk.Combobox(
                    entry_frame, 
                    textvariable=model_var, 
                    values=available_models, 
                    state="readonly", 
                    width=30
                )
                model_combo.grid(row=0, column=0, padx=5, pady=3, sticky="w")
                model_combo.bind("<<ComboboxSelected>>", self.clear_dropdown_selection)
                model_combo.bind("<Button-1>", self.clear_dropdown_selection)
                
                weight_var = tk.StringVar(value=str(item.get("weigh", 1)))
                weight_entry = ttk.Entry(entry_frame, textvariable=weight_var, width=8)
                weight_entry.grid(row=0, column=1, padx=5, pady=3, sticky="w")
                weight_entry.config(validate="key")
                vcmd_positive_int = (weight_entry.register(self.ai_draw_validate_positive_int), '%P')
                weight_entry.config(validatecommand=vcmd_positive_int)
                
                priority_var = tk.StringVar(value=str(item.get("priority", 0)))
                priority_entry = ttk.Entry(entry_frame, textvariable=priority_var, width=8)
                priority_entry.grid(row=0, column=2, padx=5, pady=3, sticky="w")
                priority_entry.config(validate="key")
                vcmd_natural_num = (priority_entry.register(self.ai_draw_validate_natural_number), '%P')
                priority_entry.config(validatecommand=vcmd_natural_num)
                
                # 操作按钮组
                action_frame = ttk.Frame(entry_frame)
                action_frame.grid(row=0, column=3, padx=5, pady=3, sticky="w")
                
                # 删除按钮
                delete_button = ttk.Button(
                    action_frame, 
                    text="🗑", 
                    width=3,
                    command=lambda ef=entry_frame, ce=config_entries, tt='background': self._ai_draw_delete_config_entry_wrapper(ef, ce, tt),
                    bootstyle="danger"
                )
                delete_button.pack(side="left", padx=(0, 5))
                
                # 测试按钮
                test_button = ttk.Button(
                    action_frame, 
                    text="🔍", 
                    width=3,
                    command=lambda mv=model_var, p=parent: self.ai_draw_test_config(mv.get(), p)
                )
                test_button.pack(side="left")
                
                # 将创建的元素和数据添加到内部列表
                config_entries.append({
                    "frame": entry_frame,
                    "model_var": model_var, "model_combo": model_combo,
                    "weight_var": weight_var, "weight_entry": weight_entry,
                    "priority_var": priority_var, "priority_entry": priority_entry
                })
                entry_frame.pack(fill="x", pady=1)

        except Exception as e:
            print(f"加载/处理背景配置时出错: {e}")
            messagebox.showerror("配置加载错误", f"加载背景配置时出错: {e}\n\n配置可能已损坏，请检查或重置。")
        
        # 加载"传入上下文"选项
        self.convey_context_var.set(self.config["AI_draw"].get("convey_context", "不传入"))
        self.context_entry.delete(0, tk.END)
        self.context_entry.insert(0, self.config["AI_draw"].get("context_entry", ""))
        self.ai_draw_toggle_context_entry()
        
        if hasattr(self, 'update_background_scrollbar_visibility'):
            # 延迟一下以确保布局更新完成
            parent.after(100, self.update_background_scrollbar_visibility)
        
        # 更新状态
        if hasattr(self, 'background_status_var'):
            self.background_status_var.set("配置已加载")
            # 2秒后恢复状态消息
            parent.after(2000, lambda: self.background_status_var.set("准备就绪"))

    def ai_draw_save_background_config(self, event=None): # Added event=None for potential binding calls
        """Saves background config based on the *entire* internal list."""
        config_data = []
         # Iterate through the full list, not just the visible ones
        for entry in self.background_config_entries:
            try:
                weight = int(entry["weight_var"].get())
                priority = int(entry["priority_var"].get())
                model = entry["model_var"].get()
                if not model: # Skip empty model selections
                    print("Skipping background entry with no model selected.")
                    continue
                config_data.append({
                    "config": model,
                    "weigh": weight,
                    "priority": priority
                })
            except ValueError:
                messagebox.showerror("错误", "权重和优先级必须是有效的整数！")
                return # Stop saving if invalid data found
            except KeyError:
                messagebox.showerror("内部错误", "无法访问配置条目数据。")
                return

        self.config["AI_draw"]["background_config"] = config_data

        # Save the "传入上下文" options
        self.config["AI_draw"]["convey_context"] = self.convey_context_var.get()
        context_num = self.context_entry.get()
        # Save context number only if "部分传入" is selected and value is valid
        if self.convey_context_var.get() == "部分传入":
            if context_num.isdigit() and int(context_num) >= 0:
                self.config["AI_draw"]["context_entry"] = int(context_num)
            else:
                self.context_entry.delete(0, tk.END)
                self.context_entry.insert(0,50)
                self.config["AI_draw"]["context_entry"] = 50 # Or keep old value
        else:
            self.config["AI_draw"]["context_entry"] = "" # Clear if not '部分传入'

        self.save_config()
        # Avoid showing bubble if called implicitly (e.g., from context change) unless specifically desired
        if event is None or isinstance(event, tk.Event) and event.widget == self.save_background_config_button:
            self.show_message_bubble("Success", "背景配置已保存！")

    def ai_draw_toggle_context_entry(self, event=None):
        """根据上下文选择来显示或隐藏条数输入框"""
        if self.convey_context_var.get() == "部分传入":
            self.context_entry_label.pack(side=tk.LEFT, padx=(15, 5))
            self.context_entry.pack(side=tk.LEFT, padx=(0, 5))
        else:
            self.context_entry_label.pack_forget()
            self.context_entry.pack_forget()
        
        # 更新状态消息
        if hasattr(self, 'background_status_var'):
            if event:  # 只有当由用户触发时才更新状态
                self.background_status_var.set(f"已更改上下文设置: {self.convey_context_var.get()}")
                # 2秒后恢复状态消息
                self.background_tab.after(2000, lambda: self.background_status_var.set("准备就绪"))



    def ai_draw_toggle_second_request(self):
        """Handles toggling ONLY the request selection's visibility"""
        if self.configs:
            if self.second_request_var.get():
                #Ensure visibility of this config based on saved state
                self.request_selection_frame.pack(side=tk.LEFT, padx=5)
                if self.current_request_view_type!=self.request_type_var.get():
                    self._ai_draw_switch_request_view()
            else:
                self.request_selection_frame.pack_forget()

        selected_config = self.config_edit_combo.get()
        if selected_config: # Only execute this if any config is selected
            config_data = self.config["AI_draw"]["configs"][selected_config] # Make sure u save state to base config for easy retrieval
            config_data['second_request']=self.second_request_var.get()
            self.save_config()

    def _ai_draw_switch_request_view(self):
        """Saves the currently displayed configuration and loads the newly selected one."""
        new_request_type = self.request_type_var.get()
        old_request_type = self.current_request_view_type

        if new_request_type == old_request_type:
            return # No change needed

        # Save the data from the outgoing view
        self._ai_draw_save_view_to_config(old_request_type)

        # Load the data for the incoming view
        self._ai_draw_load_view_from_config(new_request_type)

        # Update the tracker
        self.current_request_view_type = new_request_type

    def _ai_draw_save_view_to_config(self, request_type_to_save):
        """Saves the current UI elements' state (request-specific parts) into the config dictionary."""
        selected_config = self.config_edit_combo.get()
        if not selected_config or selected_config not in self.config["AI_draw"]["configs"]:
            return

        config_data = self.config["AI_draw"]["configs"][selected_config]
        prefix = "" if request_type_to_save == "一次请求" else "second_"

        # --- Save ONLY Request-Specific Fields ---
        config_data[prefix + "request_timeout"] = self.request_timeout_entry.get() # Timeout is specific
        config_data[prefix + "request_url"] = self.request_url_entry.get()
        config_data[prefix + "request_method"] = self.request_method_var.get()
        config_data[prefix + "request_body"] = self.request_body_text.get('1.0', tk.END).strip() if self.request_method_var.get() == "POST" else ""
        config_data[prefix + "json_path"] = self.json_path_entry.get()
        config_data[prefix + "userdefine"] = self.parse_entry.get()
        config_data[prefix + "success_condition"] = self.success_condition_entry.get()
        config_data[prefix + "fail_condition"] = self.fail_condition_entry.get()
        config_data[prefix + "forbid_condition"] = self.forbid_condition_entry.get()
        # REMOVED: Shared fields (attempts, delay, concurrency, rembg) are saved elsewhere

        # Save headers (still specific to the request type)
        headers_data = []
        for key_entry, value_entry, _ in self.headers_list:
            key = key_entry.get().strip()
            value = value_entry.get().strip()
            if key:
                headers_data.append((key, value))
        config_data[prefix + "headers"] = headers_data

        # Save the secondary switch state itself (only needed when saving the primary view's state)
        if prefix == "":
            config_data["second_request"] = self.second_request_var.get()

    def _ai_draw_load_view_from_config(self, request_type_to_load):
        """Loads data (request-specific parts) into the UI elements from the config dictionary."""
        selected_config = self.config_edit_combo.get()
        if not selected_config or selected_config not in self.config["AI_draw"]["configs"]:
            self.ai_draw_clear_request_specific_fields() # Clear request specific fields
            return

        config_data = self.config["AI_draw"]["configs"][selected_config]
        prefix = "" if request_type_to_load == "一次请求" else "second_"

        # Clear previous request-specific state first (includes clearing headers)
        self.ai_draw_clear_request_specific_fields() # This now calls update pagination internally

        if not selected_config or selected_config not in self.config["AI_draw"]["configs"]:

            return

        config_data = self.config["AI_draw"]["configs"][selected_config]

        self.request_timeout_entry.insert(0, config_data.get(prefix + "request_timeout", "30")) # Timeout is specific
        self.request_url_entry.insert(0, config_data.get(prefix + "request_url", ""))
        self.request_method_var.set(config_data.get(prefix + "request_method", "POST"))
        self.request_body_text.insert('1.0', config_data.get(prefix + "request_body", ""))
        self.json_path_entry.insert(0, config_data.get(prefix + "json_path", ""))
        self.parse_entry.insert(0, config_data.get(prefix + "userdefine", ""))
        self.success_condition_entry.insert(0, config_data.get(prefix + "success_condition", ""))
        self.fail_condition_entry.insert(0, config_data.get(prefix + "fail_condition", ""))
        self.forbid_condition_entry.insert(0, config_data.get(prefix + "forbid_condition", ""))
        # Load headers (specific to the request type)
        headers_data_str = config_data.get(prefix + "headers", '[]')
        try:
            headers_data = eval(str(headers_data_str))
            if isinstance(headers_data, list):
                for key, value in headers_data:
                    # Call add_header WITHOUT updating pagination inside the loop
                    # Add the UI elements and append to list
                    header_frame = tk.Frame(self.headers_entries_frame)

                    delete_button = ttk.Button(header_frame, text="🗑", width=3,
                                            command=lambda frame=header_frame: self.ai_draw_delete_header(frame),
                                            bootstyle="danger-outline")
                    delete_button.pack(side=tk.LEFT, padx=(5, 2))

                    key_entry = ttk.Entry(header_frame, width=30)
                    key_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
                    value_entry = ttk.Entry(header_frame, width=40)
                    value_entry.pack(side=tk.LEFT, padx=(2, 5), fill=tk.X, expand=True)
                    # Add data
                    key_entry.insert(0, key)
                    value_entry.insert(0, value)

                    self.headers_list.append((key_entry, value_entry, header_frame))
                    # DO NOT pack frame here
                    # DO NOT call _ai_draw_update_header_pagination here yet
            else:
                print(f"Warning: Invalid format for request headers in config '{selected_config}'. Expected list.")
        except Exception as e:
            print(f"Error creating header UI for config '{selected_config}': {e}")

        # --- After loading ALL headers ---
        self.header_current_page = 1 # Reset to page 1 after loading
        self._ai_draw_update_header_pagination() # Update display and controls ONCE

        # Toggle body visibility based on loaded method
        self.ai_draw_toggle_request_body()

        # Load the secondary switch state (only relevant when loading the primary view)
        if prefix == "":
            self.second_request_var.set(config_data.get("second_request", False))
            # Ensure dropdown visibility matches the loaded switch state
            if self.second_request_var.get():
                self.request_selection_frame.pack(side=tk.LEFT, padx=5)
            else:
                self.request_selection_frame.pack_forget()

    def ai_draw_clear_request_specific_fields(self):
        """Clears only the fields specific to a single request view (URL, Method, Body, Headers, Conditions, Timeout)."""
        self.request_url_entry.delete(0, tk.END)
        self.request_timeout_entry.delete(0, tk.END) # Timeout is specific
        self.request_method_var.set("POST") # Reset method
        self.request_body_text.delete('1.0', tk.END)
        self.json_path_entry.delete(0, tk.END)
        self.parse_entry.delete(0, tk.END)
        self.success_condition_entry.delete(0, tk.END)
        self.fail_condition_entry.delete(0, tk.END)
        self.forbid_condition_entry.delete(0, tk.END)

        # Clear headers list and destroy UI frames
        for _, _, frame in self.headers_list:
            if frame.winfo_exists():
                frame.destroy()
        self.headers_list.clear()
        self.header_current_page = 1 # Reset page number
        self._ai_draw_update_header_pagination() # Update display (will hide combo if needed)

    def ai_draw_clear_shared_config_fields(self):
        """Clears only the fields that are shared between first and second request views."""
        self.max_attempts_entry.delete(0, tk.END)
        self.delay_time_entry.delete(0, tk.END)
        self.maxconcurrency_entry.delete(0, tk.END)
        self.request_timeout_entry.delete(0, tk.END)
        self.request_url_entry.delete(0, tk.END)
        self.request_method_var.set("POST") # Reset method
        self.request_body_text.delete('1.0', tk.END)
        self.json_path_entry.delete(0, tk.END)
        self.parse_entry.delete(0, tk.END)
        self.success_condition_entry.delete(0, tk.END)
        self.fail_condition_entry.delete(0, tk.END)
        self.forbid_condition_entry.delete(0, tk.END)
        self.rembg_switch_var.set(False) # Reset rembg switch

        # Clear headers list and UI
        for _, _, frame in self.headers_list:
            frame.destroy()
        self.headers_list.clear()

        # Ensure body is hidden initially after clear (will be shown if method is POST after load)
        self.ai_draw_toggle_request_body()


    def ai_draw_add_header(self):
        """Adds a header entry row and updates pagination."""
        header_frame = tk.Frame(self.headers_entries_frame)
        # Don't pack here, pagination function handles it

        delete_button = ttk.Button(header_frame, text="🗑", width=3,
                                   command=lambda frame=header_frame: self.ai_draw_delete_header(frame),
                                   bootstyle="danger-outline")
        delete_button.pack(side=tk.LEFT, padx=(5, 2))

        key_entry = ttk.Entry(header_frame, width=30)
        key_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        value_entry = ttk.Entry(header_frame, width=40)
        value_entry.pack(side=tk.LEFT, padx=(2, 5), fill=tk.X, expand=True)

        self.headers_list.append((key_entry, value_entry, header_frame))
        self._ai_draw_update_header_pagination() # Update pagination display

    def ai_draw_delete_header(self, header_frame):
        """Deletes a header entry row and updates pagination."""
        for i, (_, _, frame) in enumerate(self.headers_list):
            if frame == header_frame:
                # Ensure frame exists before destroying
                if frame.winfo_exists():
                    frame.destroy()
                del self.headers_list[i]
                break
        self._ai_draw_update_header_pagination() # Update pagination display

    def ai_draw_toggle_request_body(self, event=None):
        """Toggles the visibility of the shared request body frame based on the shared request method."""
        if self.request_method_var.get() == "POST":
            # Ensure placeholder is packed correctly before conditions_frame
            self.request_body_placeholder_frame.pack(fill=tk.X)
            # Pack the actual body frame inside the placeholder
            self.request_body_frame.pack(in_=self.request_body_placeholder_frame, fill=tk.X)
        else:
            # Forget both the body frame and its placeholder
            self.request_body_frame.pack_forget()
            self.request_body_placeholder_frame.pack_forget()


    def ai_draw_set_default_config_fields(self):
        self.max_attempts_entry.insert(0, "1")
        self.delay_time_entry.insert(0, "5")
        self.maxconcurrency_entry.insert(0, "1")
        self.request_timeout_entry.insert(0, "30")
        #self.second_request_timeout_entry.insert(0, "30")

    def ai_draw_add_config(self):
        config_name = simpledialog.askstring("➕ 新增配置", "请输入配置名称:")
        if config_name:
            if config_name in self.config["AI_draw"]["configs"]:
                messagebox.showerror("错误", "配置名称已存在！")
                return
            self.configs.append(config_name)
            self.ai_draw_update_comboboxes()
            self.config_edit_combo.set(config_name)
            self.ai_draw_clear_config_fields()
            self.ai_draw_set_default_config_fields()
            self.ai_draw_create_new_config(config_name)  # Create the config entries in config.json

    def ai_draw_create_new_config(self, config_name):
        """Initializes a new config entry with defaults for shared and specific parts."""
        self.config["AI_draw"]["configs"][config_name] = {
            # Shared defaults
            "max_attempts": "1",
            "delay_time": "3",
            "maxconcurrency": "1",
            "use_rembg": False,

            # First request defaults
            "request_timeout": "30", # Specific
            "request_method": "POST",
            "request_url": "",
            "request_body": "",
            "json_path": "",
            "success_condition": "",
            "fail_condition": "",
            "headers": [],

            # Second request switch state
            "second_request": False,

            # Second request defaults
            "second_request_timeout": "30", # Specific
            "second_request_method": "POST",
            "second_request_url": "",
            "second_request_body": "",
            "second_json_path": "",
            "second_success_condition": "",
            "second_fail_condition": "",
            "second_headers": [],
            # Note: 'second_use_rembg' could exist if rembg becomes request-specific, but currently it's shared.
        }
        self.save_config()

    def ai_draw_delete_config(self):
        selected_config = self.config_edit_combo.get()
        if selected_config:
            result = messagebox.askyesno("确认", f"确定要删除配置 '{selected_config}' 吗？")
            if result:
                del self.config["AI_draw"]["configs"][selected_config]
                self.configs.remove(selected_config)
                self.ai_draw_update_comboboxes()
                if self.configs:
                    self.config_edit_combo.set(self.configs[0])
                    self.ai_draw_load_selected_config()
                else:
                    self.config_edit_combo.set("")
                    self.ai_draw_clear_config_fields()
                self.save_config()

    def ai_draw_update_comboboxes(self):
        self.config_edit_combo['values'] = self.configs

    def ai_draw_clear_config_fields(self):
        """Clears ALL fields, including shared parameters and the second request switch."""
        # Clear request-specific fields first
        self.ai_draw_clear_request_specific_fields()

        # Clear shared parameter fields
        self.max_attempts_entry.delete(0, tk.END)
        self.delay_time_entry.delete(0, tk.END)
        self.maxconcurrency_entry.delete(0, tk.END)
        self.rembg_switch_var.set(False)

        # Clear second request switch state
        self.second_request_var.set(False)
        self.request_selection_frame.pack_forget() # Hide dropdown
        self.current_request_view_type = "一次请求" # Reset view tracker

    def ai_draw_load_config_names(self):
        return sorted(self.config["AI_draw"]["configs"].keys())

    def ai_draw_load_selected_config(self, event=None):
        """Loads shared params and the first request view for the selected config."""
        selected_config = self.config_edit_combo.get()
        if not selected_config:
            self.ai_draw_clear_config_fields()
            return

        if selected_config not in self.config["AI_draw"]["configs"]:
            print(f"Error: Config '{selected_config}' not found in data.")
            self.ai_draw_clear_config_fields()
            return

        config_data = self.config["AI_draw"]["configs"][selected_config]

        # --- Load Shared Parameters FIRST ---
        self.max_attempts_entry.delete(0, tk.END)
        self.max_attempts_entry.insert(0, config_data.get("max_attempts", "1"))
        self.delay_time_entry.delete(0, tk.END)
        self.delay_time_entry.insert(0, config_data.get("delay_time", "3"))
        self.maxconcurrency_entry.delete(0, tk.END)
        self.maxconcurrency_entry.insert(0, config_data.get("maxconcurrency", "1"))
        self.rembg_switch_var.set(config_data.get("use_rembg", False))
        self.second_request_var.set(config_data.get("second_request", False))
        self.ai_draw_toggle_second_request()
        # --- Load the '一次请求' view ---
        # This handles loading request-specific fields (URL, Timeout, Method, Body, Conditions, Headers)
        # AND loads the 'second_request' switch state, adjusting dropdown visibility.
        self._ai_draw_load_view_from_config("一次请求")
        self.current_request_view_type = "一次请求" # Reset tracker

        # Ensure dropdown shows "一次请求" after loading
        self.request_type_var.set("一次请求")

    def ai_draw_save_current_config(self):
        """Saves shared params and the currently viewed configuration part."""
        selected_config = self.config_edit_combo.get()
        if not selected_config:
            messagebox.showerror("错误", "请选择要保存的配置！")
            return

        if selected_config not in self.config["AI_draw"]["configs"]:
            messagebox.showerror("错误", f"配置 '{selected_config}' 数据丢失，无法保存！")
            return

        config_data = self.config["AI_draw"]["configs"][selected_config]

        # --- Save Shared Parameters ---
        config_data["max_attempts"] = self.max_attempts_entry.get()
        config_data["delay_time"] = self.delay_time_entry.get()
        config_data["maxconcurrency"] = self.maxconcurrency_entry.get()
        config_data["use_rembg"] = self.rembg_switch_var.get()

        # --- Save the currently displayed view's specific data ---
        self._ai_draw_save_view_to_config(self.current_request_view_type)

        # --- Save the entire config dictionary to the file ---
        self.save_config()
        self.show_message_bubble("Success", f"配置 '{selected_config}' 已保存！")

    def ai_draw_load_all_configs(self):
        self.ai_draw_update_comboboxes()
        self.cloud_on_var.set(self.config["AI_draw"].get("cloud_on", False))
        if self.configs:
            self.config_edit_combo.set(self.configs[0]) # Select first by default
            self.ai_draw_load_selected_config()

    def create_ai_music_config_tab_content(self):
        # Create a main container frame with padding
        main_frame = ttk.Frame(self.ai_music_config_tab, padding="20 15 20 15")
        main_frame.pack(fill="both", expand=True)
        
        # Title section
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text="AI 音乐配置", font=("Arial", 16, "bold"))
        title_label.pack(anchor="w")
        
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=(0, 20))
        
        # Toggle switches section with better grouping
        toggle_frame = ttk.LabelFrame(main_frame, text="音乐生成选项", padding="10")
        toggle_frame.pack(fill="x", pady=(0, 20))
        
        # Create a grid layout for toggles
        toggle_grid = ttk.Frame(toggle_frame)
        toggle_grid.pack(fill="x", padx=5, pady=10)
        
        # AI Music switches in a nicer grid layout
        self.ai_music_switch_var = tk.BooleanVar()
        self.ai_opening_music_switch_var = tk.BooleanVar()
        self.ai_ending_music_switch_var = tk.BooleanVar()
        
        # Row 1: Background music
        ttk.Label(toggle_grid, text="生成背景音乐:").grid(row=0, column=0, sticky="w", padx=(5, 15), pady=8)
        ttk.Checkbutton(toggle_grid, variable=self.ai_music_switch_var, 
                        bootstyle="round-toggle", command=self.save_ai_music_switch).grid(
                        row=0, column=1, sticky="w", padx=5, pady=8)
        
        # Row 2: Opening music
        ttk.Label(toggle_grid, text="生成片头曲:").grid(row=1, column=0, sticky="w", padx=(5, 15), pady=8)
        ttk.Checkbutton(toggle_grid, variable=self.ai_opening_music_switch_var,
                       bootstyle="round-toggle", command=self.save_ai_music_switch).grid(
                       row=1, column=1, sticky="w", padx=5, pady=8)
        
        # Row 3: Ending music
        ttk.Label(toggle_grid, text="生成片尾曲:").grid(row=2, column=0, sticky="w", padx=(5, 15), pady=8)
        ttk.Checkbutton(toggle_grid, variable=self.ai_ending_music_switch_var,
                       bootstyle="round-toggle", command=self.save_ai_music_switch).grid(
                       row=2, column=1, sticky="w", padx=5, pady=8)
        
        # API Configuration section
        api_frame = ttk.LabelFrame(main_frame, text="API 配置", padding="10")
        api_frame.pack(fill="x", pady=(0, 20))
        
        # URL field
        url_frame = ttk.Frame(api_frame)
        url_frame.pack(fill="x", padx=5, pady=(10, 5))
        
        ttk.Label(url_frame, text="音乐 URL:", width=10).pack(side="left", padx=(5, 10))
        self.music_url_entry = ttk.Entry(url_frame)
        self.music_url_entry.pack(side="left", fill="x", expand=True, pady=5)
        
        # Token field
        token_frame = ttk.Frame(api_frame)
        token_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        ttk.Label(token_frame, text="音乐 Token:", width=10).pack(side="left", padx=(5, 10))
        self.music_token_entry = ttk.Entry(token_frame)
        self.music_token_entry.pack(side="left", fill="x", expand=True, pady=5)
        
        # Button section with styling
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        # Create a styled save button
        self.save_ai_music_button = ttk.Button(
            button_frame, 
            text="💾 保存配置", 
            command=self.save_ai_music_config,
            style="Accent.TButton",  # Using ttkbootstrap's accent style
            width=20
        )
        self.save_ai_music_button.pack(side="right", padx=5, pady=5)
        
        # Load existing configuration
        self.load_ai_music_config()

    def save_ai_music_switch(self):
        self.config["AI音乐"]["if_on"] = self.ai_music_switch_var.get()
        self.config["AI音乐"]["opening_if_on"]=self.ai_opening_music_switch_var.get()
        self.config["AI音乐"]["ending_if_on"]=self.ai_ending_music_switch_var.get()

        self.save_config()

    def save_ai_music_config(self):

        self.config["AI音乐"]["base_url"] = self.music_url_entry.get()
        self.config["AI音乐"]["api_key"] = self.music_token_entry.get()
        self.save_config()
        self.show_message_bubble("Success", "AI音乐配置保存成功!")

    def load_ai_music_config(self):
        try:
            # Load switch states
            self.ai_music_switch_var.set(self.config["AI音乐"].get("if_on", False))
            self.ai_opening_music_switch_var.set(self.config["AI音乐"].get("opening_if_on",False))
            self.ai_ending_music_switch_var.set(self.config["AI音乐"].get("ending_if_on",False))

            # Load entry values
            self.music_url_entry.insert(0, self.config["AI音乐"].get("base_url", ""))
            self.music_token_entry.insert(0, self.config["AI音乐"].get("api_key", ""))

        except FileNotFoundError:
            print("Config file not found, creating a new one.")
        except Exception as e:
            messagebox.showerror("Error", f"读取AI音乐配置失败: {e}")

    def create_snapshot_tab_content(self):
        # Create a main container with padding
        main_frame = ttk.Frame(self.snapshot_tab, padding="20 15 20 15")
        main_frame.pack(fill="both", expand=True)
        
        # Add a title section
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text="游戏快照管理", font=("Arial", 16, "bold"))
        title_label.pack(anchor="w")
        
        subtitle_label = ttk.Label(title_frame, text="保存和恢复游戏状态快照", font=("Arial", 10))
        subtitle_label.pack(anchor="w", pady=(5, 0))
        
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=15)
        
        # Action buttons section
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(fill="x", pady=(0, 15))
        
        # Generate snapshot button with improved styling
        self.generate_snapshot_button = ttk.Button(
            actions_frame, 
            text="✨ 生成游戏快照", 
            command=self.savesnap,
            style="Accent.TButton",
            width=20
        )
        self.generate_snapshot_button.pack(side="left", padx=(0, 10))
        
        # Add refresh button
        refresh_button = ttk.Button(
            actions_frame, 
            text="🔄 刷新列表", 
            command=self.populate_snapshot_buttons,
            width=15
        )
        refresh_button.pack(side="left")
        
        # Snapshot count indicator (right-aligned)
        self.snapshot_count_var = tk.StringVar(value="快照数量: 0")
        snapshot_count_label = ttk.Label(actions_frame, textvariable=self.snapshot_count_var)
        snapshot_count_label.pack(side="right")
        
        # Snapshot list section with header
        snapshots_frame = ttk.LabelFrame(main_frame, text="可用快照", padding=(10, 5))
        snapshots_frame.pack(fill="both", expand=True)
        
        # Create header for the list columns
        header_frame = ttk.Frame(snapshots_frame)
        header_frame.pack(fill="x", pady=(5, 0))
        
        # Column headers with consistent widths
        ttk.Label(header_frame, text="日期时间", width=20, font=("Arial", 10, "bold")).pack(side="left", padx=(5, 10))
        ttk.Label(header_frame, text="快照名称", width=30, font=("Arial", 10, "bold")).pack(side="left", padx=10)
        ttk.Label(header_frame, text="操作", width=15, font=("Arial", 10, "bold")).pack(side="left")
        
        # Separator after header
        ttk.Separator(snapshots_frame, orient="horizontal").pack(fill="x", pady=(5, 0))
        
        # Create a Frame with Canvas and Scrollbar for the snapshot list
        list_container = ttk.Frame(snapshots_frame)
        list_container.pack(fill="both", expand=True, pady=(5, 0))
        
        # Canvas for scrolling
        self.snapshot_canvas = tk.Canvas(list_container, highlightthickness=0)
        self.snapshot_scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.snapshot_canvas.yview)
        
        # Configure canvas and scrollbar
        self.snapshot_canvas.configure(yscrollcommand=self.snapshot_scrollbar.set)
        self.snapshot_canvas.pack(side="left", fill="both", expand=True)
        self.snapshot_scrollbar.pack(side="right", fill="y")
        
        # Frame inside canvas to hold snapshot items
        self.snapshot_buttons_frame = ttk.Frame(self.snapshot_canvas)
        self.snapshot_canvas_window = self.snapshot_canvas.create_window(
            (0, 0), 
            window=self.snapshot_buttons_frame, 
            anchor="nw",
            tags="self.snapshot_buttons_frame"
        )
        
        # Configure canvas to adjust with window size
        def on_canvas_configure(event):
            self.snapshot_canvas.itemconfig(
                self.snapshot_canvas_window,
                width=event.width
            )
        self.snapshot_canvas.bind("<Configure>", on_canvas_configure)
        
        # Bind events for scrolling and frame configuration
        self.snapshot_buttons_frame.bind("<Configure>", self.snapshot_on_frame_configure)
        self.snapshot_canvas.bind("<MouseWheel>", self.snapshot_on_mousewheel)
        self.snapshot_canvas.bind("<Button-4>", lambda e: self.snapshot_canvas.yview_scroll(-1, "units"))
        self.snapshot_canvas.bind("<Button-5>", lambda e: self.snapshot_canvas.yview_scroll(1, "units"))
        
        # Status bar at the bottom
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(10, 0))
        
        # Status message (left-aligned)
        self.snapshot_status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(status_frame, textvariable=self.snapshot_status_var)
        status_label.pack(side="left")
        
        # Help text (right-aligned)
        help_label = ttk.Label(
            status_frame, 
            text="提示: 点击快照名称可以恢复该快照", 
            foreground="gray"
        )
        help_label.pack(side="right")
        
        # Populate with available snapshots
        self.populate_snapshot_buttons()

    def populate_snapshot_buttons(self):
        """Populate the snapshot tab with buttons for each zip file in the snap directory."""
        # Clear existing buttons
        for widget in self.snapshot_buttons_frame.winfo_children():
            widget.destroy()

        # Update status
        self.snapshot_status_var.set("正在加载快照列表...")

        # Create buttons for each zip file
        snap_dir = os.path.join(game_directory,"snap")  # Directory containing zip files

        try:
            # Get a list of all zip files in the snap directory with their modification times
            files_with_time = []
            for filename in os.listdir(snap_dir):
                if filename.endswith(".zip"):
                    filepath = os.path.join(snap_dir, filename)
                    modification_time = os.path.getmtime(filepath)
                    files_with_time.append((filename, modification_time))

            # Sort the files by modification time in descending order (newest first)
            files_with_time.sort(key=lambda x: x[1], reverse=True)

            # Extract the name from the filename
            names = []
            for filename, modification_time in files_with_time:
                match = re.match(r"^(.*?)_\{.*\}\.zip$", filename)
                if match:
                    name = match.group(1)  # Get the first group (the name part)
                else:
                    name = filename[:-4]  # If the pattern doesn't match, use the filename without the .zip extension
                names.append(name)

            # Count name occurrences and generate labels with numbering
            name_counts = {}
            for name in names:
                name_counts[name] = name_counts.get(name, 0) + 1

            # Renumber the names based on reverse modification time order
            numbered_names = {}
            labels = []
            for name in reversed(names):
                if name_counts[name] > 1:
                    if name in numbered_names:
                        numbered_names[name] += 1
                    else:
                        numbered_names[name] = 1
                    labels.append(f"{name}({numbered_names[name]})")
                else:
                    labels.append(name)

            labels.reverse()  # 反转 labels，使其与原始文件列表顺序一致

            # Create styled rows for each snapshot with alternating background for better readability
            for row_num, ((filename, modification_time), label) in enumerate(zip(files_with_time, labels)):
                # Calculate background color for alternating rows
                bg_color = "#f5f5f5" if row_num % 2 == 0 else "#ffffff"
                
                # Create a row frame for this snapshot
                row_frame = ttk.Frame(self.snapshot_buttons_frame)
                row_frame.pack(fill="x", pady=2)
                
                # Format the modification time
                datetime_object = datetime.datetime.fromtimestamp(modification_time)
                formatted_time = datetime_object.strftime("%Y-%m-%d %H:%M:%S")
                
                # Time label
                time_label = ttk.Label(row_frame, text=formatted_time, width=20, background=bg_color)
                time_label.pack(side="left", padx=(5, 10))
                
                # Name button - clicking this will restore the snapshot
                name_button = ttk.Button(
                    row_frame, 
                    text=label, 
                    command=lambda f=filename, foldername=name: self.extract_zip(f, foldername),
                    width=30,
                    style="TButton"
                )
                name_button.pack(side="left", padx=10)
                
                # Action buttons container
                action_frame = ttk.Frame(row_frame)
                action_frame.pack(side="left")
                
                # Delete button
                delete_button = ttk.Button(
                    action_frame, 
                    text="🗑 删除", 
                    command=lambda f=filename: self.delete_snapshot(f),
                    width=10,
                    bootstyle="danger"
                )
                delete_button.pack(side="left", padx=5)
                
                # Optional: Add info button to show snapshot details
                info_button = ttk.Button(
                    action_frame, 
                    text="ℹ️", 
                    command=lambda f=filename: self.show_snapshot_info(f),
                    width=3
                )
                info_button.pack(side="left", padx=5)

            # Update snapshot count
            count = len(files_with_time)
            self.snapshot_count_var.set(f"快照数量: {count}")
            
            # Update status
            self.snapshot_status_var.set("快照列表已更新")
            
        except FileNotFoundError:
            print("Snap directory not found.")
            os.makedirs(snap_dir)  # Create the directory if it doesn't exist
            self.snapshot_status_var.set("已创建快照目录")
            self.snapshot_count_var.set("快照数量: 0")
        except Exception as e:
            error_msg = f"读取快照文件错误: {e}"
            messagebox.showerror("Error", error_msg)
            self.snapshot_status_var.set(error_msg)
            
        # Update canvas scrollregion
        self.snapshot_on_frame_configure(None)

    def savesnap(self):
        if not self.story_title_var.get():
            self.show_message_bubble("Error", "当前没有选择生成快照的故事")
            self.snapshot_status_var.set("错误: 未选择故事")
            return
        self.snapshot_status_var.set("正在生成快照...")
        threading.Thread(target=self._savesnap).start()

    def _savesnap(self):
        try:
            self.show_message_bubble("", "正在生成快照")
            gui_functions.savesnap()
            self.master.after(0, lambda: self.snapshot_status_var.set("快照生成成功"))
        except NameError:
            self.show_message_bubble("Error", "快照生成失败")
            self.master.after(0, lambda: self.snapshot_status_var.set("快照生成失败"))
        self.master.after(500, self.populate_snapshot_buttons)  # Refresh the buttons

    def extract_zip(self, filename, foldername):
        self.snapshot_status_var.set(f"正在恢复快照: {filename}...")
        threading.Thread(target=self._extract_zip, args=(filename, foldername)).start()

    def _extract_zip(self, filename, foldername):
        try:
            gui_functions.extract_zip(filename, foldername)
            self.show_message_bubble("Success", "成功恢复快照")
            self.load_config()
            new_story_title = self.config["剧情"].get("story_title", "")
            self.master.after(0, self.update_story_title, new_story_title)
            self.master.after(0, lambda: self.snapshot_status_var.set(f"已恢复快照: {filename}"))
        except NameError:
            self.show_message_bubble("Error", "快照恢复失败")
            self.master.after(0, lambda: self.snapshot_status_var.set("快照恢复失败"))

    def delete_snapshot(self, filename):
        snap_dir = os.path.join(game_directory,"snap")
        filepath = os.path.join(snap_dir, filename)
        try:
            if messagebox.askyesno("确认删除", f"确定要删除快照 {filename} 吗？"):
                self.snapshot_status_var.set(f"正在删除快照: {filename}...")
                os.remove(filepath)
                self.populate_snapshot_buttons()  # Refresh the button list
                self.show_message_bubble("Success", "删除成功")
        except Exception as e:
            error_msg = f"删除 {filename} 出错: {e}"
            messagebox.showerror("Error", error_msg)
            self.snapshot_status_var.set(error_msg)
        self.snapshot_canvas.yview_moveto(0)

    def show_snapshot_info(self, filename):
        """Display detailed information about a snapshot."""
        snap_dir = os.path.join(game_directory,"snap")
        filepath = os.path.join(snap_dir, filename)
        
        try:
            # Get file details
            file_stats = os.stat(filepath)
            size_mb = file_stats.st_size / (1024 * 1024)  # Convert to MB
            created_time = datetime.datetime.fromtimestamp(file_stats.st_ctime)
            modified_time = datetime.datetime.fromtimestamp(file_stats.st_mtime)
            
            # Format the information message
            info_message = (
                f"文件名: {filename}\n\n"
                f"创建时间: {created_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"修改时间: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"文件大小: {size_mb:.2f} MB\n"
            )
            
            # Show in a messagebox
            self.show_message_bubble("成功", info_message,80)
            
        except Exception as e:
            self.show_message_bubble("Error", f"获取快照信息出错: {e}",80)

    def snapshot_on_frame_configure(self, event):
        """Update the scrollregion of the canvas to encompass all items."""
        self.snapshot_canvas.configure(scrollregion=self.snapshot_canvas.bbox("all"))
        self.snapshot_hide_scrollbar()

    def snapshot_on_mousewheel(self, event):
        """Handle mousewheel scrolling."""
        self.snapshot_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def snapshot_hide_scrollbar(self):
        """Hide or show scrollbar based on content height."""
        if self.snapshot_buttons_frame.winfo_reqheight() <= self.snapshot_canvas.winfo_height():
            self.snapshot_scrollbar.pack_forget()  # Hide the scrollbar
            self.snapshot_canvas.configure(yscrollcommand=None)  # Remove scrollbar functionality
        else:
            self.snapshot_scrollbar.pack(side="right", fill="y")
            self.snapshot_canvas.configure(yscrollcommand=self.snapshot_scrollbar.set)



    def create_log_tab_content(self):
        # Create a main container with padding
        main_frame = ttk.Frame(self.log_tab, padding="15 10 15 10")
        main_frame.pack(fill="both", expand=True)
        
        # Top control bar with buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=(0, 10))
        
        # Left side buttons
        left_buttons = ttk.Frame(control_frame)
        left_buttons.pack(side="left")
        
        # Clear log button
        self.clear_log_button = ttk.Button(
            left_buttons, 
            text="🗑 清空日志", 
            command=self.clear_log,
            width=15
        )
        self.clear_log_button.pack(side="left", padx=(0, 10))
        
        # Pause/Resume log monitoring button
        # self.log_monitoring_state # Assumed initialized in __init__
        self.pause_resume_button = ttk.Button(
            left_buttons, 
            text="⏸️ 暂停监视", 
            command=self.toggle_log_monitoring,
            width=15
        )
        self.pause_resume_button.pack(side="left", padx=5)
        
        # Right side information
        right_info = ttk.Frame(control_frame)
        right_info.pack(side="right")
        
        # Status indicator - shows if log monitoring is active
        self.status_frame = ttk.Frame(right_info)
        self.status_frame.pack(side="right", padx=5)
        
        self.status_label = ttk.Label(self.status_frame, text="状态:")
        self.status_label.pack(side="left", padx=(0, 5))
        
        self.status_indicator = ttk.Label(
            self.status_frame, 
            text="监视中", 
            foreground="green",
            font=("Arial", 9, "bold")
        )
        self.status_indicator.pack(side="left")
        
        # Log content area with border and scrollbars
        log_frame = ttk.LabelFrame(main_frame, text="系统日志", padding=(5, 5))
        log_frame.pack(fill="both", expand=True)
        
        # Create text widget with scrollbars
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill="both", expand=True)
        
        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(text_frame, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")
        
        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(text_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Log text widget with improved styling
        self.log_text = tk.Text(
            text_frame,
            wrap="none",
            state=tk.DISABLED, # Start disabled
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            background="#f8f8f8",
            font=("Consolas", 10)
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        
        # Configure scrollbars to work with text widget
        v_scrollbar.config(command=self.log_text.yview)
        h_scrollbar.config(command=self.log_text.xview)
        
        # *** Configure tags for coloring ***
        self.log_text.tag_configure("error_tag", foreground="red")
        # Using orange for warnings as pure yellow can be hard to read on light backgrounds
        self.log_text.tag_configure("warning_tag", foreground="orange") 
        # You could also add font weight: e.g., font=("Consolas", 10, "bold")

        # Status bar at the bottom
        status_bar = ttk.Frame(main_frame)
        status_bar.pack(fill="x", pady=(5, 0))
        
        # Last update time indicator
        self.last_update_var = tk.StringVar(value="最后更新: 未更新")
        last_update_label = ttk.Label(status_bar, textvariable=self.last_update_var)
        last_update_label.pack(side="left")
        
        # Help text at right
        help_label = ttk.Label(status_bar, text="提示: 右键点击可复制日志内容", foreground="gray")
        help_label.pack(side="right")
        
        self.last_log_content = None 
        self.after_id = None
        self.log_monitoring_state = True
        self.log_file_path = os.path.join(game_directory, '..', 'log.txt') # safer path handling
        
        # Create right-click menu
        self._create_right_click_menu()
        
        # Start log monitoring
        self.monitor_log()

    def toggle_log_monitoring(self):
        """Toggle between pausing and resuming log monitoring."""
        if self.log_monitoring_state:
            # Currently monitoring, so pause it
            if self.after_id is not None:
                self.master.after_cancel(self.after_id)
                self.after_id = None
                
            self.log_monitoring_state = False
            self.pause_resume_button.config(text="▶️ 恢复监视")
            self.status_indicator.config(text="已暂停", foreground="orange")
        else:
            # Currently paused, so resume monitoring
            self.log_monitoring_state = True
            self.pause_resume_button.config(text="⏸️ 暂停监视")
            self.status_indicator.config(text="监视中", foreground="green")
            self.monitor_log()  # Restart monitoring

    def monitor_log(self):
        """Monitor the log file for changes and update the log text with color coding."""
        
        def update_log():
            if not self.log_monitoring_state:
                return
                
            try:
                # Use the defined log file path
                with open(self.log_file_path, "r", encoding="utf-8") as f:
                    log_content = f.read()

                max_chars = 50000
                if len(log_content) > max_chars:
                     # Find the nearest newline before the cutoff to avoid breaking lines
                    cutoff_point = log_content.find('\n', len(log_content) - max_chars)
                    if cutoff_point != -1:
                       log_content = log_content[cutoff_point + 1:]
                    else: # If no newline found, just truncate (less ideal)
                       log_content = log_content[-max_chars:]

                # Only update if content has changed
                if log_content != self.last_log_content:
                    # Store the current scroll position
                    should_scroll = self.log_text.yview()[1] >= 0.99 # Check if scrolled near the bottom
                    
                    self.log_text.config(state=tk.NORMAL)
                    self.log_text.delete("1.0", tk.END)
                    
                    # --- Insert line by line with tags ---
                    lines = log_content.splitlines() # Split into lines
                    for line in lines:
                        lower_line = line.lower() # Check case-insensitively
                        tags_to_apply = [] # List to hold tags for this line
                        
                        if "error" in lower_line or "fail" in lower_line or "exception" in lower_line or "失败" in lower_line:
                            tags_to_apply.append("error_tag")
                        elif "warn" in lower_line:
                            tags_to_apply.append("warning_tag")
                            
                        # Insert the line with its newline and apply tags if any
                        self.log_text.insert(tk.END, line + "\n", tuple(tags_to_apply)) 
                    # --- End of line-by-line insertion ---

                    if should_scroll:
                       self.log_text.see(tk.END) # Scroll to the end only if it was already near the end

                    self.log_text.config(state=tk.DISABLED)
                    self.last_log_content = log_content
                    
                    current_time = time.strftime("%H:%M:%S", time.localtime())
                    self.last_update_var.set(f"最后更新: {current_time}")

            except FileNotFoundError:
                current_content = self.log_text.get("1.0", tk.END).strip()
                error_msg = f"日志文件未找到 ({self.log_file_path})"
                if error_msg not in current_content: # Avoid flooding if file stays missing
                    self.log_text.config(state=tk.NORMAL)
                    self.log_text.delete("1.0", tk.END) # Clear previous errors
                    self.log_text.insert("1.0", error_msg + "\n", ("error_tag",)) # Show error in red
                    self.log_text.config(state=tk.DISABLED)
                    self.last_log_content = None # Reset content tracking
            except Exception as e:
                current_content = self.log_text.get("1.0", tk.END).strip()
                error_msg = f"读取日志错误: {e}"
                # Avoid flooding with the same error
                if not current_content.endswith(str(e)): 
                   self.log_text.config(state=tk.NORMAL)
                   # Maybe don't delete existing content, just append the error?
                   # self.log_text.delete("1.0", tk.END) 
                   self.log_text.insert(tk.END, f"\n--- {error_msg} ---\n", ("error_tag",)) # Append error in red
                   self.log_text.see(tk.END)
                   self.log_text.config(state=tk.DISABLED)
                   self.last_log_content = None # Reset content tracking

            if self.log_monitoring_state:
                self.after_id = self.master.after(1500, update_log) # Check slightly more often (e.g., 1.5 seconds)

        update_log()

    def _create_right_click_menu(self):
        """Creates a right-click menu for the log text widget."""
        self.right_click_menu = tk.Menu(self.log_text, tearoff=0)
        self.right_click_menu.add_command(label="📋 复制", command=self._copy_selected_text)
        self.right_click_menu.add_command(label="📋 复制全部", command=self._copy_all_text)
        self.right_click_menu.add_separator()
        # --- 添加格式化 JSON 菜单项 ---
        self.right_click_menu.add_command(label="{} 格式化json", command=self._format_selected_json)
        # --- 结束添加 ---
        self.right_click_menu.add_separator() # 可以保留或添加分隔符
        self.right_click_menu.add_command(label="🔍 查找...", command=self._show_search_dialog)
        
        self.log_text.bind("<Button-3>", self._show_right_click_menu)

    def _fix_nonstandard_json(self, text):
        """修复常见非标准JSON格式"""
        # 替换非转义单引号为双引号
        fixed = re.sub(r"(?<!\\)'", '"', text)
        # 处理Python风格的布尔值和null
        fixed = re.sub(r'\bTrue\b', 'true', fixed)
        fixed = re.sub(r'\bFalse\b', 'false', fixed)
        fixed = re.sub(r'\bNone\b', 'null', fixed)
        return fixed

    def _extract_valid_json(self, s):
        """改进的状态机方法，返回(提取的JSON, 剩余字符串)"""
        n = len(s)
        for i in range(n):
            if s[i] in {'{', '['}:
                stack = 1
                in_string = False
                quote_char = None
                escape = False
                start = i
                for j in range(i + 1, n):
                    char = s[j]
                    if escape:
                        escape = False
                        continue
                    if char == '\\':
                        escape = True
                    elif char in {'"', "'"}:
                        if not in_string:
                            in_string = True
                            quote_char = char
                        elif char == quote_char:
                            in_string = False
                            quote_char = None
                    elif not in_string:
                        if char in {'{', '['}:
                            stack += 1
                        elif char in {'}', ']'}:
                            stack -= 1
                    if stack == 0:
                        candidate = s[start:j+1]
                        try:
                            fixed = self._fix_nonstandard_json(candidate)
                            json.loads(fixed)  # 验证有效性
                            remaining = s[:start] + s[j+1:]
                            return fixed, remaining
                        except json.JSONDecodeError:
                            break  # 继续查找其他可能
                continue
        return None, s  # 未找到有效JSON

    def _format_selected_json(self):
        """Formats the selected text as JSON and displays it in a new window."""
        try:
            selected_text = self.log_text.selection_get()
            if not selected_text.strip():
                messagebox.showwarning("格式化 JSON", "请先选择有效的 JSON 文本。")
                return

            try:
                # 循环提取所有JSON
                extracted_jsons = []
                remaining = selected_text
                while True:
                    json_str, remaining = self._extract_valid_json(remaining)
                    if json_str is None:
                        break
                    extracted_jsons.append(json_str)

                if not extracted_jsons:
                    raise json.JSONDecodeError("未找到有效JSON结构", "", 0)

                # 格式化输出
                formatted_list = []
                for idx, json_str in enumerate(extracted_jsons, 1):
                    parsed = json.loads(json_str)
                    formatted = json.dumps(parsed, indent=4, ensure_ascii=False)
                    if len(extracted_jsons) > 1:
                        formatted = f"/* JSON {idx} */\n{formatted}"
                    formatted_list.append(formatted)
                
                final_output = '\n\n'.join(formatted_list)

                # 4. 创建展示窗口（保持原UI逻辑）
                json_window = Toplevel(self.master)
                json_window.withdraw()
                json_window.title("格式化的 JSON")
                json_window.geometry("600x400")
                json_window.resizable(False, False)
                try:
                   json_window.attributes('-toolwindow', True)
                except tk.TclError:
                   pass 
                json_window.transient(self.master)
                
                text_frame = ttk.Frame(json_window)
                text_frame.pack(fill="both", expand=True, padx=10, pady=10)

                v_scrollbar = ttk.Scrollbar(text_frame, orient="vertical")
                v_scrollbar.pack(side="right", fill="y")
                h_scrollbar = ttk.Scrollbar(text_frame, orient="horizontal")
                h_scrollbar.pack(side="bottom", fill="x")

                json_text_widget = Text(
                    text_frame,
                    wrap="none",
                    yscrollcommand=v_scrollbar.set,
                    xscrollcommand=h_scrollbar.set,
                    font=("Consolas", 10)
                )
                json_text_widget.pack(side="left", fill="both", expand=True)

                v_scrollbar.config(command=json_text_widget.yview)
                h_scrollbar.config(command=json_text_widget.xview)

                json_text_widget.insert("1.0", final_output)
                json_text_widget.config(state=tk.DISABLED)

                
                json_window.place_window_center() # << CENTER IT
                json_window.deiconify() # << SHOW THE WINDOW
                json_window.focus_set()
                json_window.lift()
                json_window.attributes('-topmost', True) # Keep on top initially
                json_window.after(10, lambda: json_window.attributes('-topmost', False)) # Allow other windows on top later

            except json.JSONDecodeError as e:
                self.show_message_bubble("error", 
                    f"JSON解析错误，{e}")
                
            except Exception as e:
                self.show_message_bubble("error", 
                    f"处理 JSON 时发生未知错误: {str(e)}\n"
                    f"类型: {type(e).__name__}")

        except tk.TclError:
            self.show_message_bubble("error", "请先选择要格式化的 JSON 文本。")
        
    def _copy_selected_text(self):
        """Copies the selected text to the clipboard."""
        try:
            selected_text = self.log_text.selection_get()
            self.master.clipboard_clear()
            self.master.clipboard_append(selected_text)
            self.master.update()
        except tk.TclError:  # No text selected
            pass

    def _copy_all_text(self):
        """Copies all text to the clipboard."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.tag_add("sel", "1.0", "end")
        try:
            selected_text = self.log_text.selection_get()
            self.master.clipboard_clear()
            self.master.clipboard_append(selected_text)
            self.master.update()
        except tk.TclError:
            pass
        finally:
            self.log_text.tag_remove("sel", "1.0", "end")
            self.log_text.config(state=tk.DISABLED)
            
    def _show_search_dialog(self):
        """Shows a dialog to search for text in the logs."""
        # This is a placeholder for a search function
        # You would implement a proper search dialog here
        search_term = simpledialog.askstring("搜索", "请输入要搜索的文本:")
        if search_term:
            try:
                self._search_in_logs(search_term)
            except:
                pass

    def _search_in_logs(self, term):
        """Search for the given term in logs and highlight matches."""
        # Reset any previous search
        self.log_text.tag_remove("search", "1.0", "end")
        
        # Define a tag for highlighting
        self.log_text.tag_configure("search", background="yellow")
        
        # Starting position for search
        start_pos = "1.0"
        while True:
            start_pos = self.log_text.search(term, start_pos, stopindex="end", nocase=True)
            if not start_pos:
                break
            end_pos = f"{start_pos}+{len(term)}c"
            self.log_text.tag_add("search", start_pos, end_pos)
            start_pos = end_pos
        
        # Temporarily enable text widget to show the first match
        self.log_text.config(state=tk.NORMAL)
        self.log_text.see(self.log_text.search(term, "1.0", stopindex="end", nocase=True))
        self.log_text.config(state=tk.DISABLED)

    def _show_right_click_menu(self, event):
        """Displays the right-click menu at the location of the click."""
        try:
            self.right_click_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.right_click_menu.grab_release()

    def clear_log(self):
        self.master.after(0, self._clear_log)

    def _clear_log(self):
        try:
            with open("../log.txt", "w", encoding="utf-8") as f:
                f.write("")  # clear the file
                
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete("1.0", tk.END)
            self.log_text.config(state=tk.DISABLED)
            self.last_log_content = ""
            
            # Update last update time
            current_time = time.strftime("%H:%M:%S", time.localtime())
            self.last_update_var.set(f"最后更新: {current_time} (已清空)")
            
            self.show_message_bubble("成功", "日志清空成功")
        except Exception as e:
            messagebox.showerror("错误", f"清空日志文件出错: {e}")




    def create_regenerate_tab_content(self):
        # Create a main container with padding for better spacing
        main_frame = ttk.Frame(self.regenerate_tab, padding="20 15 20 15")
        main_frame.pack(fill="both", expand=True)
        
        # Add a title section
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text="内容生成工具", font=("Arial", 16, "bold"))
        title_label.pack(anchor="w")
        
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=(0, 20))
        
        # --- 角色重绘部分 - 使用更现代的设计 ---
        char_redraw_frame = ttk.LabelFrame(main_frame, text="角色重绘", padding=(15, 10))
        char_redraw_frame.pack(fill="x", pady=(0, 15))
        
        # 内部布局容器
        char_content_frame = ttk.Frame(char_redraw_frame)
        char_content_frame.pack(fill="x", padx=5, pady=10)
        
        # 角色下拉框标签和下拉框
        ttk.Label(char_content_frame, text="选择角色:").pack(side="left", padx=(0, 10))
        
        self.character_names = self.load_character_names()
        self.character_var = tk.StringVar(value=self.character_names[0] if self.character_names else "")
        self.character_dropdown = ttk.Combobox(
            char_content_frame, 
            textvariable=self.character_var, 
            values=self.character_names, 
            state="readonly", 
            width=30
        )
        self.character_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.character_dropdown.bind("<<ComboboxSelected>>", self.clear_dropdown_selection)
        
        # 生成角色按钮 - 使用主题强调色
        self.generate_character_button = ttk.Button(
            char_content_frame, 
            text="👤 生成角色", 
            command=self.generate_character,
            style="Accent.TButton",
            width=15
        )
        self.generate_character_button.pack(side="left", padx=(0, 5))
        
        # --- 其他生成选项部分 - 使用卡片式设计 ---
        other_gen_frame = ttk.LabelFrame(main_frame, text="其他生成选项", padding=(15, 10))
        other_gen_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 创建网格布局来组织按钮更加美观
        button_grid = ttk.Frame(other_gen_frame)
        button_grid.pack(fill="both", expand=True, padx=5, pady=10)
        
        # 配置网格的列，设置相等权重以便均匀分布
        button_grid.columnconfigure(0, weight=1)
        button_grid.columnconfigure(1, weight=1)
        
        # 按钮样式和大小配置
        button_width = 25
        button_pady = 12
        
        # 按钮 1: 生成背景音乐 (左上)
        self.generate_music_button = ttk.Button(
            button_grid, 
            text="🎵 生成背景音乐", 
            command=self.generate_music,
            width=button_width
        )
        self.generate_music_button.grid(row=0, column=0, padx=(5, 10), pady=(5, button_pady), sticky="nsew")
        
        # 按钮 2: 分支查看及文本导出 (右上)
        self.generate_conservation_button = ttk.Button(
            button_grid, 
            text="📖 分支查看及文本导出", 
            command=self.generate_storytext,
            width=button_width
        )
        self.generate_conservation_button.grid(row=0, column=1, padx=(10, 5), pady=(5, button_pady), sticky="nsew")
        
        # 按钮 3: 人物语音生成 (左下)
        self.voice_conservation_button = ttk.Button(
            button_grid, 
            text="🎤 人物语音生成", 
            command=self.generate_voice,
            width=button_width
        )
        self.voice_conservation_button.grid(row=1, column=0, padx=(5, 10), pady=(button_pady, 5), sticky="nsew")
        
        # 按钮 4: 背景图重绘 (右下)
        self.generate_background_button = ttk.Button(
            button_grid, 
            text="🖼️ 背景图重绘", 
            command=self.generate_background,
            width=button_width
        )
        self.generate_background_button.grid(row=1, column=1, padx=(10, 5), pady=(button_pady, 5), sticky="nsew")
        
        # 添加说明文本（可选）
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill="x", pady=(5, 0))
        
        info_text = "提示: 选择要生成的内容类型，点击对应按钮开始生成"
        info_label = ttk.Label(info_frame, text=info_text, foreground="gray")
        info_label.pack(side="left", padx=5)

    # --- The rest of your methods remain the same ---

    def load_character_names(self):
        """Loads the character names from the character.json file."""
        try:
            title = self.story_title_var.get()
            # Use os.path.join for better path handling
            json_path = os.path.join(game_directory, 'data', title, 'character.json')
            if not title:
                 print("Story title is empty, cannot load characters.") # Added check
                 return []
            if not os.path.exists(json_path):
                 print(f"Character file not found: {json_path}") # Added check
                 return []

            with open(json_path, "r", encoding='utf-8') as f:
                data = json.load(f)
                # Handle potential case where 'name' key might be missing
                names = [item.get('name', 'Unnamed') for item in data if isinstance(item, dict)]
            return names
        except FileNotFoundError: # This might be redundant now with os.path.exists
             print(f"Character file not found (in except): {json_path}")
             return []
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Error decoding character JSON: {e}\nFile: {json_path}")
            return []
        except Exception as e:
            messagebox.showerror("Error", f"Error loading character names: {e}")
            return []

    def generate_character(self):
        character_name = self.character_var.get()
        if not character_name:
            self.show_message_bubble("error", "请先选择一个人物。")
            return
        threading.Thread(target=self._generate_character, args=(character_name,), daemon=True).start() # Use daemon=True

    def _generate_character(self, name):
        try:
            self.show_message_bubble("Info",f"开始为角色 '{name}' 生成绘画...") # Added name
            # Ensure gui_functions exists and has the method
            if hasattr(gui_functions, 'regeneratecharacter'):
                 gui_functions.regeneratecharacter(name)
                 self.show_message_bubble("Success",f"角色 '{name}' 绘画生成成功")
            else:
                 self.show_message_bubble("Error","绘画生成功能不可用")
                 print("Error: gui_functions.regeneratecharacter not found")
        except Exception as e:
            self.show_message_bubble("Error",f"角色绘画生成失败: {e}")
            # Use logging instead of messagebox from thread? Or use queue/after
            print(f"Error calling regeneratecharacter: {e}") # Avoid messagebox in thread

    def generate_music(self):
        threading.Thread(target=self._generate_music, daemon=True).start() # Use daemon=True

    def _generate_music(self):
        try:
            self.show_message_bubble("Info","开始生成背景音乐...")
            if hasattr(gui_functions, 'generate_music'):
                gui_functions.generate_music()
                self.show_message_bubble("Success","背景音乐生成成功")
            else:
                self.show_message_bubble("Error","音乐生成功能不可用")
                print("Error: gui_functions.generate_music not found")
        except Exception as e:
            self.show_message_bubble("Error",f"音乐生成失败: {e}")
            print(f"Error calling generate_music: {e}")

    def generate_storytext(self):
        threading.Thread(target=self._generate_storytext, daemon=True).start() # Use daemon=True

    def _generate_storytext(self):
        try:
            self.show_message_bubble("Info", "开始处理故事文本/分支...") # Give feedback
            if hasattr(gui_functions, 'generate_storytext'):
                gui_functions.generate_storytext()
                self.show_message_bubble("Success","故事文本/分支处理完成") # Give feedback
            else:
                self.show_message_bubble("Error", "故事文本功能不可用")
                print("Error: gui_functions.generate_storytext not found")
        except Exception as e:
            self.show_message_bubble("Error",f"故事文本/分支处理失败: {e}")
            print(f"Error calling generate_storytext: {e}")

    def generate_voice(self):
        id = simpledialog.askstring("输入ID", "请输入要生成语音的文本ID:", parent=self.master)
        if id: # Check if user cancelled or entered empty string
            # Basic validation (is it a number? adjust as needed)
            if id.isdigit():
                 threading.Thread(target=self._generate_voice,args=(id,), daemon=True).start() # Use daemon=True
            else:
                 messagebox.showwarning("输入无效", "请输入有效的文本ID (通常是数字)。")
        else:
            print("Voice generation cancelled or ID not entered.")

    def _generate_voice(self, id):
        try:
            self.show_message_bubble("Info", f"开始为文本ID '{id}' 生成语音...")
            if hasattr(gui_functions, 'generate_voice'):
                gui_functions.generate_voice(id)
                self.show_message_bubble("Success",f"文本ID '{id}' 语音生成成功")
            else:
                 self.show_message_bubble("Error","语音生成功能不可用")
                 print("Error: gui_functions.generate_voice not found")
        except Exception as e:
            self.show_message_bubble("Error",f"语音生成失败 (ID: {id}): {e}")
            print(f"Error calling generate_voice for ID {id}: {e}")

    def generate_background(self):
        """Handles the 'Redraw Background' button click and subsequent steps."""
        # 1. Get Text ID
        text_id = simpledialog.askstring("输入ID", "请输入要重绘背景图的文本ID:", parent=self.master)
        if not text_id:
            print("Background redraw cancelled: No ID entered.")
            return # User cancelled or entered nothing

        # 2. Check Story Title
        current_story_title = self.story_title_var.get()
        if not current_story_title:
            self.show_message_bubble("error", "请先在首页选择一个故事")
            return

        # 3. Start the ID-specific generation in a thread immediately
        #    (if the function exists)
        if hasattr(gui_functions, 'generate_background'):
             gui_functions.generate_background(text_id)
        else:
             self.show_message_bubble("Warning", "ID相关背景生成功能 (gui_functions.generate_background(id)) 不可用")

        # 4. Load Locations
        place_json_path = os.path.join(game_directory, 'data', current_story_title, 'story', 'place.json')
        try:
            with open(place_json_path, 'r', encoding='utf-8') as f:
                locations = json.load(f)
            if not isinstance(locations, list):
                self.show_message_bubble("error", f"地点列表文件 ({place_json_path}) 格式无效 (应为列表)")
                return
            if not locations:
                self.show_message_bubble("error", f"地点列表文件 ({place_json_path}) 为空")
                return
        except FileNotFoundError:
            self.show_message_bubble("error", f"地点列表文件 ({place_json_path}) 未找到")
            return
        except json.JSONDecodeError:
            self.show_message_bubble("error", f"地点列表文件 ({place_json_path}) JSON 解析失败")
            return
        except Exception as e:
            self.show_message_bubble("error", f"加载地点列表时出错: {e}")
            return

        # 5. Show Location Selection Dialog
        dialog = LocationSelectionDialog(self.master, locations)
        self.master.wait_window(dialog) # Wait for user interaction

        # 6. Process Dialog Result
        if dialog.result is not None: # User clicked OK
            selected_locations = dialog.result
            print(f"Selected locations for redraw: {selected_locations}")

            # 7. Save Selected Locations
            try:
                with open(place_json_path, 'w', encoding='utf-8') as f:
                    json.dump(selected_locations, f, ensure_ascii=False, indent=4)
                print(f"Saved selected locations to {place_json_path}")
            except Exception as e:
                self.show_message_bubble("error", f"保存地点列表时出错: {e}")
                return # Don't proceed if saving failed

            # 8. Trigger General Background Generation in a thread
            if hasattr(gui_functions, 'generate_background'):
                self.show_message_bubble("Info", "开始通用背景图生成任务...")
                threading.Thread(target=self._generate_background_general, daemon=True).start()
            else:
                 self.show_message_bubble("Warning", "通用背景生成功能 (gui_functions.generate_background('generate')) 不可用")

        else: # User clicked Cancel
            print("Background redraw cancelled by user at location selection.")
            self.show_message_bubble("Info", "背景重绘已取消")



    def _generate_background_general(self):
         """Worker thread for general background generation after location selection."""
         try:
             # Function signature requires one argument, pass "generate"
             # Ensure the function exists before calling
            if hasattr(gui_functions, 'generate_background'):
                 gui_functions.generate_background("generate")
                 self.show_message_bubble("Success", "通用背景生成任务完成")
            # No need for an else here, checked in the calling function
         except AttributeError:
             self.show_message_bubble("Error", "背景生成函数 ('generate') 不存在")
             print(f"Error: gui_functions.generate_background('generate') missing during thread execution.")
         except Exception as e:
             self.show_message_bubble("Error", f"通用背景生成失败: {e}")
             print(f"Error calling generate_background with 'generate': {e}")


    def create_about_tab_content(self):
        # Create a main container with padding for better spacing
        main_frame = ttk.Frame(self.about_tab, padding="20 15 20 15")
        main_frame.pack(fill="both", expand=True)
        
        # Add a title section
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 15))
        
        # App logo and title
        logo_title_frame = ttk.Frame(title_frame)
        logo_title_frame.pack(fill="x")
        
        # You can replace this with an actual logo if available
        app_logo_label = ttk.Label(logo_title_frame, text="🎮", font=("Arial", 24))
        app_logo_label.pack(side="left")
        
        title_label = ttk.Label(logo_title_frame, text="AI galgame生成器", font=("Arial", 18, "bold"))
        title_label.pack(side="left", padx=(10, 0))
        
        # Try to get version info
        try:
            version_str = f"V{version_to_string(VERSION)}"
        except NameError:
            version_str = "V1.0.0"  # Fallback version
        
        version_label = ttk.Label(title_frame, text=version_str, font=("Arial", 10))
        version_label.pack(anchor="w", pady=(5, 0))
        
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=15)
        
        # Content area with card-like design
        content_frame = ttk.Frame(main_frame, padding=2)
        content_frame.pack(fill="both", expand=True)
        
        # Updates section
        update_frame = ttk.LabelFrame(content_frame, text="更新", padding=(15, 10))
        update_frame.pack(fill="x", pady=(0, 15))
        
        update_options_frame = ttk.Frame(update_frame)
        update_options_frame.pack(fill="x", padx=5, pady=10)
        
        # Auto-check updates option
        self.auto_check_update_var = tk.BooleanVar()
        self.auto_check_update_switch = ttk.Checkbutton(
            update_options_frame,
            text="启动时自动检查更新",
            variable=self.auto_check_update_var,
            command=self.save_auto_check_update,
            bootstyle="round-toggle"
        )
        self.auto_check_update_switch.pack(side="left", padx=(5, 15))
        
        # Check update button with accent styling
        self.check_update_button = ttk.Button(
            update_options_frame, 
            text="立即检查更新", 
            command=self.check_update_thread,
            style="Accent.TButton",
            width=15
        )
        self.check_update_button.pack(side="right", padx=5)
        
        # Help & Documentation section
        help_frame = ttk.LabelFrame(content_frame, text="帮助与文档", padding=(15, 10))
        help_frame.pack(fill="x", pady=(0, 15))
        
        # Documentation button 
        doc_frame = ttk.Frame(help_frame)
        doc_frame.pack(fill="x", padx=5, pady=10)
        
        ttk.Label(doc_frame, text="📚 用户手册").pack(side="left", padx=(5, 10))
        
        self.documentation_button = ttk.Button(
            doc_frame, 
            text="查看在线文档", 
            command=lambda: self.open_url("https://aigal.qqframe.cn"),
            width=15
        )
        self.documentation_button.pack(side="right", padx=5)
        
        # Contact or additional information section
        info_frame = ttk.LabelFrame(content_frame, text="关于软件", padding=(15, 10))
        info_frame.pack(fill="x", pady=(0, 15))
        
        info_content = ttk.Frame(info_frame)
        info_content.pack(fill="x", padx=5, pady=10)
        
        # Software description
        description_text = "这是一款利用AI自动生成galgame的工具，支持角色、背景音乐、语音和场景的生成。"
        description_label = ttk.Label(info_content, text=description_text, wraplength=400)
        description_label.pack(anchor="w", padx=5, pady=(0, 10))
        
        # Credits or copyright information
        copyright_text = "© 2025 开发团队. 保留所有权利。"
        copyright_label = ttk.Label(info_content, text=copyright_text, foreground="gray")
        copyright_label.pack(anchor="w", padx=5)
        
        # Bottom footer area with links
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill="x", pady=(5, 0))
        
        # Social or contact links
        github_button = ttk.Button(
            footer_frame, 
            text="GitHub", 
            command=lambda: self.open_url("https://github.com/1491860506/AIGal"),
            width=10
        )
        github_button.pack(side="left", padx=5)
        
        website_button = ttk.Button(
            footer_frame, 
            text="官方网站", 
            command=lambda: self.open_url("https://aigal.qqframe.cn"),
            width=10
        )
        website_button.pack(side="left", padx=5)
        
        # Load initial configuration
        self.load_about_config()
        
    def open_url(self, url):
        """Open a URL in the default web browser"""
        webbrowser.open(url)

    # --- Other methods (with minor improvements) ---

    def load_about_config(self):
        """Loads the auto check update state from the config file."""
        try:
            # Ensure 'about' key exists before accessing nested key
            about_config = self.config.setdefault("about", {})
            self.auto_check_update_var.set(about_config.get("auto_check_update", False))
            # No need to save here, setdefault modifies in place if key was missing
            # Only save if you want to ensure the default value is written back immediately
            # self.save_config() # Optional: uncomment if needed
        except AttributeError:
             messagebox.showerror("配置错误", "配置对象无效或不存在 'config' 属性。")
             self.auto_check_update_var.set(False) # Set a default
        except Exception as e:
            messagebox.showerror("错误", f"加载自动检查更新设置时出错: {e}")
            self.auto_check_update_var.set(False) # Set a default on error

    def save_auto_check_update(self):
        """Saves the auto check update setting to the config file."""
        try:
            # Ensure 'about' key exists
            if "about" not in self.config:
                self.config["about"] = {}
            self.config["about"]["auto_check_update"] = self.auto_check_update_var.get()
            self.save_config() # Assume self.save_config handles writing the self.config object
        except AttributeError:
             messagebox.showerror("配置错误", "配置对象无效或不存在 'config' 或 'save_config'。")
        except Exception as e:
            messagebox.showerror("错误", f"保存自动检查更新设置时出错: {e}")

    def check_update_thread(self):
        # Disable button while checking
        self.check_update_button.config(state="disabled", text="检查中...")
        # Use daemon=True so thread doesn't block app exit
        thread = threading.Thread(target=self.check_update, daemon=True)
        thread.start()

    def check_update(self):
        try:
            # Increased timeout, added headers maybe needed by some servers
            headers = {'User-Agent': 'AIGAL-App/1.0'} # Example User-Agent
            response = requests.get("https://r2.qqframe.cn/aigal/latest.json", timeout=10, headers=headers)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json() # Use response.json() directly

            # Add more robust checking for expected keys
            latest_version_str = data.get('version')
            update_info = data.get('description', '无更新详情。')
            url = data.get('url')

            if not latest_version_str or not url:
                 raise ValueError("更新服务器返回的数据格式无效 (缺少 version 或 url)")


            if latest_version_str > VERSION:
                # Ensure UI updates happen in the main thread if UpdateDialog isn't thread-safe
                # Using root.after or a queue is safer, but wait_window might be okay if Dialog handles it
                print(f"发现新版本: {latest_version_str}, 当前版本: {VERSION}")
                print(f"更新信息: {update_info}")
                print(f"下载地址: {url}")

                # It's generally safer to schedule GUI interactions from threads
                self.master.after(0, self.show_update_dialog, latest_version_str, update_info, url)

            else:
                self.show_message_bubble("success", f"当前已是最新版本 (V{version_to_string(VERSION)})")

        except requests.exceptions.RequestException as e:
            self.show_message_bubble("error", f"检查更新失败 (网络错误): {e}")
        except json.JSONDecodeError:
            self.show_message_bubble("error", "检查更新失败: 服务器返回无效数据")
        except ValueError as e:
             self.show_message_bubble("error", f"检查更新失败: {e}")
        except NameError:
             # Handle case where VERSION is not defined
             self.show_message_bubble("error", "检查更新失败: 应用版本信息未定义")
        except Exception as e:
            self.show_message_bubble("error", f"检查更新时发生未知错误: {e}")
        finally:
            # Re-enable button in the main thread
            # Use master.after to ensure it runs in the main GUI thread
            if hasattr(self, 'master'): # Check if master exists (for safety)
                 self.master.after(0, lambda: self.check_update_button.config(state="normal", text="检查更新"))

    def show_update_dialog(self, version, info, url):
        """Shows the update dialog (called from main thread via root.after)."""
        # Assuming UpdateDialog is properly defined elsewhere
        try:
            dialog = UpdateDialog(self.master, version, info, url) # Pass version/info/url if dialog needs them
            self.master.wait_window(dialog) # Making it modal

            if dialog.result: # Assuming True means user wants to update
                 self.update_application(url)
            else:
                 print("Update cancelled by user.")
        except NameError:
             messagebox.showerror("错误", "UpdateDialog 类未定义。")
        except Exception as e:
             messagebox.showerror("错误", f"显示更新对话框时出错: {e}")

    def update_application(self, url):
        """Initiates the download process."""
        # Ensure DownloadProgressDialog is thread-safe or run download in thread
        # and update progress via queue/after
        filename = url.split('/')[-1] if '/' in url else "update.zip" # Basic filename extraction
        print(f"Starting download for {url} to {filename}")
        try:
             # Assuming DownloadProgressDialog handles download and progress display
             download_dialog = DownloadProgressDialog(self.master, url, filename)
             # If DownloadProgressDialog spawns its own thread, fine.
             # If not, you'd need to wrap the download logic in a thread here.
             # self.master.wait_window(download_dialog) # Optional: make download modal
        except NameError:
            messagebox.showerror("错误", "DownloadProgressDialog 类未定义。")
            # Fallback: Maybe just open the URL in browser?
            # webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("错误", f"启动下载时出错: {e}")

    def auto_check_update_on_startup(self):
        """Automatically checks for updates if the setting is enabled."""
        if self.auto_check_update_var.get():
            print("Auto checking for updates on startup...")
            self.check_update_thread()

# --- Main ---
if __name__ == "__main__":
    log_redirector = LogRedirector(os.path.join(game_directory,'../log.txt'))
    sys.stdout = log_redirector
    sys.stderr = log_redirector
    root = Window(themename="minty",size=(1280,720))
    gui = GUI(root)
    root.place_window_center()
    root.title("AI GAL")
    try:
        root.mainloop()
    finally:
        log_redirector.close()
