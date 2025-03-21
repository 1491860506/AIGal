import tkinter as tk
from tkinter import ttk
from tkinter import filedialog,simpledialog
import tkinter.font as tkFont
import tkinter.messagebox as messagebox
import configparser
import os
import threading
import zipfile
import sys
import json
import re
from ttkbootstrap import *
import time
import datetime
import shutil
import requests
import textwrap


config_file = 'config.ini'
section_name = '剧情'
language_key = 'language'
language_value = '中文'
config = configparser.ConfigParser()
if os.path.exists(config_file):
    config.read(config_file, encoding="utf-8")
if not config.has_section(section_name):
    config.add_section(section_name)
if not config.has_option(section_name, language_key):
    config.set(section_name, language_key, language_value)
with open(config_file, 'w', encoding='utf-8') as configfile:
    config.write(configfile)


# Import necessary modules
try:
    import gui_functions
except ImportError:
    print("gui_functions.py not found. Some functionality may be missing.")

try:
    import renpy
    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

class HoverButton(tk.Canvas):
    def __init__(self, parent, tooltip_text, max_line_width=40, tooltip_background="#333333", tooltip_foreground="white", tooltip_font=("Microsoft YaHei", 12), **kwargs):
        tk.Canvas.__init__(self, parent, width=30, height=30, highlightthickness=0, background=kwargs.get('background', 'white'))
        self.parent = parent
        self.tooltip_text = tooltip_text
        self.max_line_width = max_line_width
        self.tooltip_background = tooltip_background
        self.tooltip_foreground = tooltip_foreground
        self.tooltip_font = tooltip_font
        self.tooltip = None

        self.oval = self.create_oval(5, 5, 25, 25, fill="white", outline="red", width=2)
        self.question_mark = self.create_text(15, 15, text="?", fill="red", font=("Microsoft YaHei", 12, "bold"))  # Updated font here

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, event=None):
        self.show_tooltip()

    def on_leave(self, event=None):
        self.hide_tooltip()

    def show_tooltip(self):
        if self.tooltip is not None:
            return

        # Wrap the text to fit the tooltip width
        wrapped_text = textwrap.fill(self.tooltip_text, width=self.max_line_width)

        # Create the tooltip window
        self.tooltip = tk.Toplevel(self.parent)
        self.tooltip.overrideredirect(True)  # Remove window decorations
        self.tooltip.wm_geometry("+%d+%d" % (self.winfo_rootx() + 25, self.winfo_rooty() + 25)) # Position near the button

        # Create a label for the tooltip text
        label = tk.Label(self.tooltip, text=wrapped_text, background=self.tooltip_background,
                         foreground=self.tooltip_foreground, relief="solid", borderwidth=1,
                         font=self.tooltip_font, justify="left")  # Left-justify the text
        label.pack(ipadx=5, ipady=5)

    def hide_tooltip(self):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None



class ModelSettingTab:
    def __init__(self, parent, llm_config_tab, tab_name):
        self.frame = ttk.Frame(parent)
        self.llm_config_tab = llm_config_tab
        self.tab_name = tab_name
        self.config = llm_config_tab.config
        self.config_file = llm_config_tab.config_file
        self.config_names = llm_config_tab.config_names
        self.create_widgets()
        self.load_settings()  # Load settings when the tab is created
    def create_widgets(self):
        self.settings = []

        # Frame for Add and Save buttons
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(pady=5)

        add_button = tk.Button(button_frame, text="➕ 新增", command=self.add_setting)
        add_button.pack(side=tk.LEFT, padx=5)

        self.save_button = tk.Button(button_frame, text="💾 保存", command=self.save_settings)
        self.save_button.pack(side=tk.LEFT, padx=5)

        tip_text="程序会首先使用最高优先级下的模型：同一优先级下权重越高的模型被选中的概率越大，当该优先级下的全部模型均超出尝试次数而失败时，程序会选择下一优先级。当对应项未选择接入模型时，则使用默认配置，否则优先使用对应项下的配置"
        self.hover_button = HoverButton(button_frame, tooltip_text=tip_text)
        self.hover_button.pack(pady=20)


        self.setting_frame = ttk.Frame(self.frame)
        self.setting_frame.pack(fill="both", expand=True)


        # Headers
        config_label = tk.Label(self.setting_frame, text="配置")
        config_label.grid(row=0, column=0, padx=5, pady=2)

        model_label = tk.Label(self.setting_frame, text="                            模型")
        model_label.grid(row=0, column=1, padx=5, pady=2)

        weight_label = tk.Label(self.setting_frame, text="                               权重")
        weight_label.grid(row=0, column=2, padx=5, pady=2)

        priority_label = tk.Label(self.setting_frame, text="优先级")
        priority_label.grid(row=0, column=3, padx=5, pady=2)

    def add_setting(self):
        """Adds a new setting row."""
        setting = SettingRow(self.setting_frame, self, len(self.settings) + 1)
        self.settings.append(setting)

    def delete_setting(self, setting_row):
        """Deletes a setting row."""
        self.settings.remove(setting_row)
        setting_row.destroy()
        self.reorder_settings()

    def reorder_settings(self):
        """Reorders the setting rows after a deletion."""
        for i, setting in enumerate(self.settings):
            setting.row_num = i + 1
            setting.update_row_num()

    def save_settings(self):
        """Saves the settings to the config file."""
        settings_data = []
        for setting in self.settings:
            weight = setting.weight_var.get()
            priority = setting.priority_var.get()
            config = setting.config_var.get()
            model = setting.model_var.get()

            if not config or not model or not weight or not priority:
                self.llm_config_tab.show_message_bubble("error", "存在项为空")
                return  # Prevent saving

            settings_data.append({
                "config": config,
                "model": model,
                "weigh": weight,
                "priority": priority
            })

        settings_json = json.dumps(settings_data, ensure_ascii=False)
        self.config["模型"][f"{self.tab_name}_setting"] = settings_json

        with open(self.config_file, "w", encoding="utf-8") as configfile:
            self.config.write(configfile)
        self.llm_config_tab.show_message_bubble("Success", f"{self.tab_name}设置已保存！")

    def load_settings(self):
        """Loads the settings from the config file."""
        try:
            settings_json = self.config["模型"].get(f"{self.tab_name}_setting", "[]")
            settings_data = json.loads(settings_json)

            # Sort settings data based on priority (descending) and weight (descending)
            settings_data.sort(key=lambda x: (int(x.get("priority", 0)), int(x.get("weigh", 0))), reverse=True)

            for data in settings_data:
                setting = SettingRow(self.setting_frame, self, len(self.settings) + 1,
                                     config_value=data.get("config", ""),
                                     model_value=data.get("model", ""),
                                     weight_value=data.get("weigh", "1.0"),
                                     priority_value=data.get("priority", "50"))
                self.settings.append(setting)

        except Exception as e:
            self.llm_config_tab.show_message_bubble("Error", f"Error loading {self.tab_name} settings: {e}")
            print("Error", f"Error loading {self.tab_name} settings: {e}")

class SettingRow:
    def __init__(self, parent, model_setting_tab, row_num, config_value="", model_value="", weight_value="1", priority_value="0"):
        self.parent = parent
        self.model_setting_tab = model_setting_tab
        self.row_num = row_num
        self.config_names = model_setting_tab.config_names # Get config names from parent
        self.llm_config_tab = model_setting_tab.llm_config_tab
        self.frame = ttk.Frame(parent)
        self.frame.grid(row=row_num, column=0, columnspan=5, sticky="ew")

        self.config_var = tk.StringVar(value=config_value)
        self.config_dropdown = ttk.Combobox(self.frame, textvariable=self.config_var, values=self.config_names, state="readonly") # Use config_names
        self.config_dropdown.grid(row=0, column=0, padx=5, pady=2)
        self.config_dropdown.bind("<<ComboboxSelected>>", self.clear_selection)

        self.model_var = tk.StringVar(value=model_value)
        self.model_dropdown = ttk.Combobox(self.frame, textvariable=self.model_var, values=model_setting_tab.llm_config_tab.model_names, state="readonly")
        self.model_dropdown.grid(row=0, column=1, padx=5, pady=2)
        self.model_dropdown.bind("<<ComboboxSelected>>", self.clear_selection)

        self.weight_var = tk.StringVar(value=weight_value)
        self.weight_entry = tk.Entry(self.frame, textvariable=self.weight_var, width=10)
        self.weight_entry.grid(row=0, column=2, padx=5, pady=2)
        self.weight_entry.config(validate="key")
        self.weight_entry.config(validatecommand=(self.weight_entry.register(self.validate_positive_int), '%P'))

        self.priority_var = tk.StringVar(value=priority_value)
        self.priority_entry = tk.Entry(self.frame, textvariable=self.priority_var, width=10)
        self.priority_entry.grid(row=0, column=3, padx=5, pady=2)
        self.priority_entry.config(validate="key")
        self.priority_entry.config(validatecommand=(self.priority_entry.register(self.validate_nature_int), '%P'))

        self.delete_button = ttk.Button(self.frame, text="🗑 删除", command=self.delete,
                                   bootstyle="danger")
        self.delete_button.grid(row=0, column=4, padx=5, pady=2)

    def delete(self):
        """Deletes this setting row."""
        self.model_setting_tab.delete_setting(self)

    def destroy(self):
        """Destroys the frame."""
        self.frame.destroy()

    def update_row_num(self):
        """Updates the row number."""
        self.frame.grid(row=self.row_num, column=0, columnspan=5, sticky="ew")

    def clear_selection(self, event=None):
        if event:
            event.widget.selection_clear()

    def validate_positive_int(self, new_value):
        if new_value == "":
            return True
        try:
            value = int(new_value)
            return value > 0
        except ValueError:
            return False
    def validate_nature_int(self, new_value):
        if new_value == "":
            return True
        try:
            value = int(new_value)
            return value >= 0
        except ValueError:
            return False
        


class PromptConfigTab:
    def __init__(self, parent, llm_config_tab):
        self.frame = ttk.Frame(parent)
        self.llm_config_tab = llm_config_tab
        self.config = llm_config_tab.config  # Keep this line, even if unused
        self.config_file = llm_config_tab.config_file  # Keep this line, even if unused
        self.prompt_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), rf"{game_directory}\prompt.json") #Define the path to prompt.json
        self.create_widgets()
        self.load_prompt_settings()

        # Add variables to track current selection
        self.current_kind_var = tk.StringVar()
        self.current_id_var = tk.StringVar()

    def create_widgets(self):
        """Creates the widgets for the prompt configuration tab."""
        self.kind_number_data = [
            {"kind": "大纲", "number": 6},
            {"kind": "选项", "number": 6},
            {"kind": "故事开头", "number": 6},
            {"kind": "故事继续", "number": 6},
            {"kind": "故事结尾", "number": 6},
            {"kind": "全部人物绘画", "number": 2},
            {"kind": "单个人物绘画", "number": 2},
            {"kind": "故事地点绘画", "number": 2},
            {"kind": "结尾地点绘画", "number": 2},
            {"kind": "背景音乐生成", "number": 2},
            {"kind": "开头音乐生成", "number": 6},
            {"kind": "结尾音乐生成", "number": 6},
            {"kind": "故事总结", "number": 6},
            {"kind": "翻译", "number": 6}
        ]

        # Button Frame
        button_frame = ttk.Frame(self.frame)
        button_frame.grid(row=0, column=0, columnspan=5, padx=5, pady=5)

        # Import Button
        import_button = tk.Button(button_frame, text="导入", command=self.import_prompt_config)
        import_button.pack(side=tk.LEFT, padx=10)

        # Export Button
        export_button = tk.Button(button_frame, text="导出", command=self.export_prompt_config)
        export_button.pack(side=tk.LEFT, padx=10)

        # Save button
        save_button = tk.Button(button_frame, text="💾 保存", command=self.save_prompt_config)
        save_button.pack(side=tk.LEFT, padx=10)

        # Kind selection
        kind_label = tk.Label(self.frame, text="提示词类型")
        kind_label.grid(row=1, column=0, padx=5, pady=2)

        self.kind_var = tk.StringVar()
        self.kind_dropdown = ttk.Combobox(self.frame, textvariable=self.kind_var, values=[item["kind"] for item in self.kind_number_data], state="readonly")
        self.kind_dropdown.grid(row=1, column=1, padx=5, pady=2)
        self.kind_dropdown.bind("<<ComboboxSelected>>", self.update_id_dropdown)

        # ID selection
        id_label = tk.Label(self.frame, text="编号")
        id_label.grid(row=1, column=2, padx=5, pady=2)

        self.id_var = tk.StringVar()
        self.id_dropdown = ttk.Combobox(self.frame, textvariable=self.id_var, values=[], state="readonly")
        self.id_dropdown.grid(row=1, column=3, padx=5, pady=2)
        self.id_dropdown.bind("<<ComboboxSelected>>", self.load_prompt_content)  # Load content on selection

        # Prompt text area
        prompt_label = tk.Label(self.frame, text="提示词")
        prompt_label.grid(row=2, column=0, padx=5, pady=2)

        self.prompt_text = Text(self.frame, width=67, height=19)
        self.prompt_text.grid(row=2, column=1, columnspan=3, padx=5, pady=2)

    def export_prompt_config(self):
        """Exports the prompt configuration to a JSON file."""
        prompt_config = self.load_prompt_settings()

        # Open file dialog to select export path
        filepath = filedialog.asksaveasfilename(defaultextension=".json",
                                                filetypes=[("JSON files", "*.json"), ("All files", "*.*")])

        if filepath:
            try:
                # Format the JSON with indentation for readability
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(prompt_config, f, indent=4, ensure_ascii=False)

                self.llm_config_tab.show_message_bubble("Success", "提示词导出成功 " + filepath)

            except Exception as e:
                self.llm_config_tab.show_message_bubble("Error", f"导出错误: {e}")

    def import_prompt_config(self):
        """Imports the prompt configuration from a JSON file."""
        # Open file dialog to select import path
        filepath = filedialog.askopenfilename(defaultextension=".json",
                                               filetypes=[("JSON files", "*.json"), ("All files", "*.*")])

        if filepath:
            try:
                # Read the JSON data from the file
                with open(filepath, "r", encoding="utf-8") as f:
                    imported_config = json.load(f)

                # Validate the imported data (optional, but recommended)
                if not isinstance(imported_config, list):
                    raise ValueError("Invalid JSON format: Expected a list.")
                for item in imported_config:
                    if not isinstance(item, dict) or "kind" not in item or "content" not in item:
                        raise ValueError("Invalid JSON format: Each item must be a dictionary with 'kind' and 'content' keys.")

                # Save the imported data into the prompt.json
                with open(self.prompt_file, "w", encoding="utf-8") as f:
                    json.dump(imported_config, f, indent=4, ensure_ascii=False)

                # Update the UI
                self.load_prompt_settings()  # Reload the settings
                self.update_id_dropdown() # Update the dropdowns

                self.llm_config_tab.show_message_bubble("Success", "提示词已从 " + filepath + " 导入")

            except (FileNotFoundError, json.JSONDecodeError) as e:
                self.llm_config_tab.show_message_bubble("Error", f"文件错误: {e}")
            except ValueError as e:
                self.llm_config_tab.show_message_bubble("Error", f"数据格式错误: {e}")
            except Exception as e:
                self.llm_config_tab.show_message_bubble("Error", f"导入错误: {e}")

    def update_id_dropdown(self, event=None):
        """Updates the ID dropdown based on the selected kind."""
        self.save_current_prompt() # Save before changing
        selected_kind = self.kind_var.get()
        try:
            event.widget.selection_clear()
        except:
            pass
        for item in self.kind_number_data:
            if item["kind"] == selected_kind:
                num_prompts = item["number"]
                id_values = [str(i) for i in range(1, num_prompts + 1)]
                self.id_dropdown['values'] = id_values
                if id_values:
                    self.id_var.set(id_values[0])  # Select the first ID
                    self.load_prompt_content()  # Load content after setting the first ID
                else:
                    self.id_var.set("")
                    self.prompt_text.delete("1.0", tk.END)  # Clear the text area
                self.current_kind_var.set(selected_kind)
                self.current_id_var.set(self.id_var.get())
                return

    def load_prompt_content(self, event=None):
        """Loads the prompt content from the config file."""
        self.save_current_prompt() # Save before changing
        selected_kind = self.kind_var.get()
        selected_id = self.id_var.get()

        if not selected_kind or not selected_id:
            self.prompt_text.delete("1.0", tk.END)  # Clear the text area
            self.current_kind_var.set("")
            self.current_id_var.set("")
            try:
                event.widget.selection_clear()
            except:
                pass
            return

        prompt_config = self.load_prompt_settings()

        for kind_config in prompt_config:
            if kind_config["kind"] == selected_kind:
                for content in kind_config["content"]:
                    if content["id"] == selected_id:
                        self.prompt_text.delete("1.0", tk.END)  # Clear existing text
                        self.prompt_text.insert("1.0", content["prompt"])  # Insert loaded text
                        self.current_kind_var.set(selected_kind)
                        self.current_id_var.set(selected_id)
                        try:
                            event.widget.selection_clear()
                        except:
                            pass
                        return

        # If no prompt is found, clear the text area
        self.prompt_text.delete("1.0", tk.END)
        self.current_kind_var.set(selected_kind)
        self.current_id_var.set(selected_id)
        try:
            event.widget.selection_clear()
        except:
            pass

    def save_current_prompt(self):
        """Saves the current prompt to the prompt.json file."""
        selected_kind = self.current_kind_var.get()
        selected_id = self.current_id_var.get()
        prompt_content = self.prompt_text.get("1.0", tk.END).strip()

        if not selected_kind or not selected_id:
            #print("No kind or id selected, skipping save.")
            return # Nothing to save

        # Load existing prompt config
        prompt_config = self.load_prompt_settings()

        # Find the kind, if it exists, otherwise create it
        kind_found = False
        for kind_config in prompt_config:
            if kind_config["kind"] == selected_kind:
                kind_found = True
                # Find the prompt, if it exists, otherwise create it
                id_found = False
                for content in kind_config["content"]:
                    if content["id"] == selected_id:
                        content["prompt"] = prompt_content
                        id_found = True
                        break
                if not id_found:
                    kind_config["content"].append({"id": selected_id, "prompt": prompt_content})
                break # Kind was found, exit the loop
        if not kind_found:
            # Kind not found, create the kind and the prompt
            prompt_config.append({
                "kind": selected_kind,
                "content": [{"id": selected_id, "prompt": prompt_content}]
            })

        # Save the prompt config to prompt.json
        try:
            with open(self.prompt_file, "w", encoding="utf-8") as f:
                json.dump(prompt_config, f, indent=4, ensure_ascii=False)
            #self.llm_config_tab.show_message_bubble("Success", "提示词配置已保存！") #No need to show success message every time
        except Exception as e:
            self.llm_config_tab.show_message_bubble("Error", f"保存错误: {e}")

    def save_prompt_config(self):
        """Saves the prompt configuration to the prompt.json file."""
        self.save_current_prompt()
        self.llm_config_tab.show_message_bubble("Success", "提示词配置已保存！")

    def load_prompt_settings(self):
        """Loads the prompt configuration from the prompt.json file."""
        try:
            with open(self.prompt_file, "r", encoding="utf-8") as f:
                prompt_config = json.load(f)
                return prompt_config
        except FileNotFoundError:
            # Handle the case where the file doesn't exist
            return []
        except json.JSONDecodeError:
            # Handle the case where the JSON is invalid
            self.llm_config_tab.show_message_bubble("Error", "Error loading prompt config: Invalid JSON format.")
            return []
        except Exception as e:
            self.llm_config_tab.show_message_bubble("Error", f"Error loading prompt config: {e}")
            print("Error", f"Error loading prompt config: {e}")
            return []
        

class ModelSelectionDialog(Toplevel):
    def __init__(self, parent, all_models, existing_models):
        super().__init__(parent)
        self.title("选择需要导入的模型")
        self.result = None
        self.all_models = all_models
        self.existing_models = existing_models
        self.selections = {}

        self.create_widgets()
        self.adjust_dialog_size()
        #self.center_window()
        self.place_window_center()

    def create_widgets(self):
        """Creates the checkbuttons for model selection."""
        num_models = len(self.all_models)
        num_cols = 5
        num_rows = (num_models + num_cols - 1) // num_cols

        self.checkbutton_frame = ttk.Frame(self)
        self.checkbutton_frame.pack(pady=10)

        for i, model in enumerate(self.all_models):
            is_existing = model in self.existing_models
            self.selections[model] = tk.BooleanVar(value=is_existing)  # Set initial state

            row = i // num_cols
            col = i % num_cols
            cb = ttk.Checkbutton(self.checkbutton_frame, text=model, variable=self.selections[model], bootstyle="round-toggle")
            cb.grid(row=row, column=col, padx=5, pady=2, sticky="w")

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        ok_button = ttk.Button(button_frame, text="确定", command=self.on_ok)
        ok_button.pack(side="left", padx=5)

        cancel_button = ttk.Button(button_frame, text="取消", command=self.on_cancel)
        cancel_button.pack(side="left", padx=5)

    def adjust_dialog_size(self):
        """Adjusts the dialog size based on the number of models and their lengths."""
        num_models = len(self.all_models)
        num_cols = 5
        num_rows = (num_models + num_cols - 1) // num_cols

        # Calculate the maximum row length
        max_row_length = 0
        for row in range(num_rows):
            row_length = 0
            for col in range(num_cols):
                index = row * num_cols + col
                if index < num_models:
                    row_length += len(self.all_models[index])
            max_row_length = max(max_row_length, row_length)

        # Calculate width based on maximum row length, average character width, and padding
        avg_char_width = 11  # Approximate average character width in pixels
        checkbutton_width = 47 # Approximate width of a checkbutton
        width_padding = 10 # Add padding to width
        frame_width = max_row_length * avg_char_width + num_cols * checkbutton_width + width_padding

        # Calculate height based on number of rows and some padding
        row_height = 27 # height of each row
        height_padding = 80 # Add padding to height
        frame_height = num_rows * row_height + height_padding

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

        # --- Style Configuration ---
        style = ttk.Style()

        # Define colors
        self.bg_color = "#f0f0f0"  # Light gray background
        self.tab_bg_color = "#d9d9d9"  # Slightly darker tab background
        self.tab_fg_color = "#000"  # Black text
        self.selected_tab_bg_color = "#fff"  # White for selected tab
        self.selected_tab_fg_color = "#000"  # Black text for selected tab
        self.border_color = "#aaa"  # Light border color

        # Configure the notebook
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=self.tab_bg_color,
                        foreground=self.tab_fg_color,
                        borderwidth=3,
                        padding=[10, 5])  # Add padding for better spacing
        style.map("TNotebook.Tab",
                  background=[("selected", self.selected_tab_bg_color),
                              ("active", "#e6e6e6")],  # Lighter on hover
                  foreground=[("selected", self.selected_tab_fg_color)])

        # Configure the frame inside the tab
        style.configure("TFrame", background=self.bg_color, borderwidth=0)

        self.configure(style="TNotebook")



class GUI:
    
    def __init__(self, master):
        self.config = configparser.ConfigParser()
        self.config_file = "config.ini"
        self.master = master

        # --- Font Configuration ---
        self.default_font = tkFont.Font(family="Microsoft YaHei", size=10)  # Change as desired
        #self.button_font = tkFont.Font(family="Microsoft YaHei", size=10, weight="bold")
        master.option_add("*Font", self.default_font)
        style = ttk.Style()
        style.configure('.', font=("Microsoft YaHei", 10))
        #style.configure('TButton', font=("Arial", 16))

        master.title("AI GAL")

        # Notebook (Tabs)
        self.notebook = ThemedNotebook(master) # Use themed notebook

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

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.notebook.pack(expand=True, fill="both")


    def clear_dropdown_selection(self, event):
        event.widget.selection_clear()

    def on_tab_change(self, event):
        self.master.focus_set()
        selected_tab = self.notebook.select()  # Returns the widget ID of the selected tab
        if selected_tab == str(self.regenerate_tab):       # Comparing widget IDs
            
            self.character_dropdown.destroy()
            self.character_names = self.load_character_names()
            self.character_var = tk.StringVar(value=self.character_names[0] if self.character_names else "")  # Set default value

            self.character_dropdown = ttk.Combobox(self.regenerate_tab, textvariable=self.character_var, values=self.character_names, state="readonly")
            self.character_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
            self.character_dropdown.bind("<<ComboboxSelected>>", self.clear_dropdown_selection)
        if selected_tab== str(self.snapshot_tab):
            self.populate_snapshot_buttons()

    def show_message_bubble(self, status, text, max_line_width=20): # Added max_line_width parameter
        successlist=["success","Success","成功","True","true",0]
        errorlist=["Error","error","fail","failed","Fail","Failed","错误","False","false",-1]
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

        if status == "Success":
            fg_color = "green"  # Text color
            text="✔️"+text
        elif status == "Error":
            fg_color = "red"  # Text color
            text="❌ "+text
        else:
            fg_color = "#9F79EE"  # Text color
            text="⏳ "+text

        bg_color = "#F6F6EF"  # Background color for the bubble

        # Create a Toplevel window for the bubble
        bubble = tk.Toplevel(self.master)
        bubble.overrideredirect(True)  # Remove window decorations
        bubble.config(bg=bg_color)  # Set the background color

        # --- Calculate Text Size and Wrap Text ---
        font = tkFont.Font(family="黑体", size=10)
        wrapped_text = self.wrap_text(text, font, max_line_width)
        text_width = font.measure(wrapped_text)
        text_height = font.metrics("linespace") * wrapped_text.count('\n') + font.metrics("linespace") # Added linespace

        # --- Rounded Corners (Canvas-Based) ---
        corner_radius = 10  # Radius of the rounded corners
        canvas_width = text_width + 2 * corner_radius + 20 # Padding
        canvas_height = text_height + 2 * corner_radius + 10 # Padding
        canvas = tk.Canvas(bubble, bg=bg_color, height=canvas_height, width=canvas_width, bd=0, highlightthickness=0)
        canvas.pack()

        # Draw rounded rectangle
        canvas.create_rectangle(0, corner_radius, canvas_width, canvas_height - corner_radius, fill=bg_color, outline=bg_color)  # Middle
        canvas.create_rectangle(corner_radius, 0, canvas_width - corner_radius, canvas_height, fill=bg_color, outline=bg_color)  # Middle
        canvas.create_arc(0, 0, 2 * corner_radius, 2 * corner_radius, start=90, extent=90, fill=bg_color, outline=bg_color, style="pieslice")  # Top Left
        canvas.create_arc(canvas_width - 2 * corner_radius, 0, canvas_width, 2 * corner_radius, start=0, extent=90, fill=bg_color, outline=bg_color, style="pieslice")  # Top Right
        canvas.create_arc(0, canvas_height - 2 * corner_radius, 2 * corner_radius, canvas_height, start=180, extent=90, fill=bg_color, outline=bg_color, style="pieslice")  # Bottom Left
        canvas.create_arc(canvas_width - 2 * corner_radius, canvas_height - 2 * corner_radius, canvas_width, canvas_height, start=270, extent=90, fill=bg_color, outline=bg_color, style="pieslice")  # Bottom Right
        canvas.create_text(canvas_width/2, canvas_height/2, text=wrapped_text, font=("黑体", 10),fill=fg_color)

        # Calculate the position of the bubble relative to the main window
        window_width = self.master.winfo_width()
        window_height = self.master.winfo_height()
        bubble_width = canvas_width #bubble.winfo_reqwidth() # canvas_width
        bubble_height = canvas_height #bubble.winfo_reqheight() # canvas_height

        x = self.master.winfo_x() + window_width - bubble_width - 20
        y = self.master.winfo_y() + 50

        bubble.geometry(f"+{x}+{y}")

        def destroy_bubble(status):
            if status=="Success":
                delay=3
            elif status=="Error":
                delay=3
            else:
                delay=1
            time.sleep(delay)
            bubble.destroy()

        threading.Thread(target=destroy_bubble,args=(status,)).start()

    def is_chinese(self, char):
        """判断一个字符是否为中文"""
        return '\u4e00' <= char <= '\u9fa5'

    def calculate_text_width(self, text, font, chinese_ratio=1.0):
        """计算文本的精确宽度，区分中英文字符"""
        width = 0
        for char in text:
            if self.is_chinese(char):
                width += font.measure("中")  # 中文字符宽度
            else:
                width += font.measure("a") * 0.6 # 英文字符宽度，调整系数
        return width

    def wrap_text(self, text, font, max_width, chinese_ratio=1.0):
        """Wraps the given text to fit within the specified width."""
        words = text.split()
        lines = []
        current_line = []
        current_width = 0
        for word in words:
            word_width = self.calculate_text_width(word, font, chinese_ratio)
            test_width = current_width + word_width + font.measure(" ") # Add space width
            if test_width <= max_width * font.measure("中"):
                current_line.append(word)
                current_width = test_width
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_width = word_width
        lines.append(' '.join(current_line))
        return '\n'.join(lines)






    def create_home_tab_content(self):
        # --- Frames for better organization ---
        top_frame = ttk.Frame(self.home_tab)
        top_frame.pack(side="top", fill="x", padx=5, pady=5)

        middle_frame = ttk.Frame(self.home_tab)
        middle_frame.pack(side="top", fill="x", padx=5, pady=5)

        bottom_frame = ttk.Frame(self.home_tab)
        bottom_frame.pack(side="bottom", fill="both", expand=True, padx=5, pady=5)

        music_frame = ttk.Frame(self.home_tab)
        music_frame.pack(side="top", fill="x", padx=5, pady=5)

        # --- Widgets ---
        # Row 0
        self.outline_switch_var = tk.BooleanVar()
        self.ai_music_switch_var = tk.BooleanVar()

        self.outline_switch_label = tk.Label(top_frame, text="大纲指导生成")
        self.outline_switch_label.pack(side="left", padx=5, pady=5)
        self.outline_switch = ttk.Checkbutton(top_frame, variable=self.outline_switch_var,command=self.save_outline_switch,
                                               bootstyle="round-toggle")
        self.outline_switch.pack(side="left", padx=5, pady=5)



        # Row 1
        lang_frame = ttk.Frame(top_frame)
        lang_frame.pack(side="left", fill="x", padx=5, pady=5)

        self.lang_var = tk.StringVar()
        self.lang_label = tk.Label(lang_frame, text="语言")
        self.lang_label.pack(side="left", padx=5, pady=5)
        self.lang = ttk.Combobox(lang_frame, textvariable=self.lang_var, values=["中文", "英文", "日文"],
                                  state="readonly")
        self.lang.pack(side="left", padx=5, pady=5)
        self.lang.bind("<<ComboboxSelected>>",
                               lambda event: [self.save_language(event),
                                              self.clear_dropdown_selection(event)])

        story_frame = ttk.Frame(top_frame)
        story_frame.pack(side="left", fill="x", padx=5, pady=5)

        self.story_title_var = tk.StringVar()
        self.story_names = [""]
        self.story_title_label = tk.Label(story_frame, text="切换故事")
        self.story_title_label.pack(side="left", padx=5, pady=5)
        self.story_title = ttk.Combobox(story_frame, textvariable=self.story_title_var,
                                         values=self.story_names, state="readonly")
        self.story_title.pack(side="left", padx=5, pady=5)
        self.story_title.bind("<<ComboboxSelected>>",
                               lambda event: [self.save_story_title(event),
                                              self.clear_dropdown_selection(event)])

        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side="left", fill="x", padx=5, pady=5)
        # Rename Story Button
        self.rename_button = ttk.Button(button_frame, text="🖋 故事改名", command=self.rename_story,
                                        bootstyle="secondary")
        self.rename_button.pack(side="left", padx=5, pady=5)

        # Delete Story Button
        self.delete_button = ttk.Button(button_frame, text="🗑 删除故事", command=self.delete_story,
                                        bootstyle="danger")
        self.delete_button.pack(side="left", padx=5, pady=5)

        # Row 2
        self.outline_content_label = tk.Label(middle_frame, text="故事生成提示")
        self.outline_content_label.pack(side="top", anchor="w", padx=5, pady=5)
        self.outline_content_entry = tk.Text(middle_frame, width=120, height=15)
        self.outline_content_entry.pack(side="left", fill="both", expand=True, padx=5, pady=5)


        # Row 8
        buttons_frame = ttk.Frame(self.home_tab)
        buttons_frame.pack(side="bottom", fill="x", padx=5, pady=5)


        self.start_button = tk.Button(buttons_frame, text="▶ 开始游戏" , command=self.start,
                                   font=("Microsoft YaHei", 14))
        self.start_button.pack(side="left", padx=5, pady=5)

        self.load_config()

    def rename_story(self):
        selected_story = self.story_title_var.get()
        if not selected_story:
            self.show_message_bubble("Error", "当前未选中故事")
            return

        new_name = simpledialog.askstring("Rename Story", "Enter new story name:",
                                          parent=self.master)
        if new_name:
            old_path = os.path.join("data", selected_story)
            new_path = os.path.join("data", new_name)

            try:
                os.rename(old_path, new_path)

                # Update config file
                self.config.read(self.config_file, encoding="utf-8")
                if "剧情" in self.config:
                    self.config["剧情"]["story_title"] = new_name
                    with open(self.config_file, "w", encoding="utf-8") as configfile:
                        self.config.write(configfile)

                # Refresh story list
                self.story_names = [f for f in os.listdir("data") if
                                    os.path.isdir(os.path.join("data", f))]
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
                self.config.read(self.config_file, encoding="utf-8")
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
            self.story_names = [f for f in os.listdir("data") if os.path.isdir(os.path.join("data", f))]
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
            if "剧情" not in self.config:
                self.config["剧情"] = {}

            self.config["剧情"]["story_title"] = str(self.story_title_var.get())

            with open(self.config_file, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)
            if str(self.story_title_var.get())!="":
                self.show_message_bubble("Success", f"成功切换故事到{str(self.story_title_var.get())}")
            else:
                self.show_message_bubble("Success", "已选择空项，开始游戏将会创建新故事")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving story title: {e}")
    def save_language(self, event=None):
        try:
            if "剧情" not in self.config:
                self.config["剧情"] = {}

            self.config["剧情"]["language"] = str(self.lang_var.get())

            with open(self.config_file, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)
            self.show_message_bubble("Success", f"成功切换到语言：{str(self.lang_var.get())}")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving language: {e}")
    def save_outline_switch(self):
        try:
            # Create section '剧情' if it does not exist
            if "剧情" not in self.config:
                self.config["剧情"] = {}

            # Save the switch state
            self.config["剧情"]["if_on"] = str(self.outline_switch_var.get())
            with open(self.config_file, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)

        except Exception as e:
            messagebox.showerror("Error", f"Error saving outline switch state: {e}")
    def save_outline_content(self):
        try:
            # Create section '剧情' if it does not exist
            if "剧情" not in self.config:
                self.config["剧情"] = {}

            # Save the outline content
            self.config["剧情"]["outline_content_entry"] = self.outline_content_entry.get("1.0", tk.END) # Get text from Text widget
            with open(self.config_file, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)

        except Exception as e:
            messagebox.showerror("Error", f"Error saving outline content: {e}")
    def load_config(self):
        try:
            self.config.read(self.config_file, encoding="utf-8")
            try:
                self.story_names = [f for f in os.listdir("data") if os.path.isdir(os.path.join("data", f))]
                self.story_names.sort()
                self.story_names.extend([""])
                self.story_title['values'] = self.story_names
            except:
                print("load error for story title")
            # Load switch states
            if "剧情" in self.config and "if_on" in self.config["剧情"]:
                self.outline_switch_var.set(self.config["剧情"].getboolean("if_on"))
            self.lang_var.set(self.config["剧情"].get("language", ""))
            self.story_title_var.set(self.config["剧情"].get("story_title", ""))
            self.outline_content_entry.insert(1.0, self.config["剧情"].get("outline_content_entry", ""))

        except FileNotFoundError:
            print("Config file not found, creating a new one.")
        except Exception as e:
            messagebox.showerror("Error", f"读取配置失败: {e}")
    def delete_story(self):
        selected_story = self.story_title_var.get()
        if not selected_story:
            self.show_message_bubble("Error", "当前选项无法删除")  # Or however you display messages
            return
        if selected_story == "":
              self.show_message_bubble("Error", "当前选项为空，无法删除")  # Or however you display messages
              return
        story_path = os.path.join("data", selected_story)
        if not os.path.exists(story_path) or not os.path.isdir(story_path):
            self.show_message_bubble("Error", f"目录不存在: {selected_story}")
            return
        try:
            shutil.rmtree(story_path)  # Use shutil.rmtree to delete the directory and its contents
            self.show_message_bubble("Success", f"成功删除故事: {selected_story}")
            self.config["剧情"]["story_title"]=''
            with open(self.config_file, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)

            # Update the story list
            self.story_names = [f for f in os.listdir("data") if os.path.isdir(os.path.join("data", f))]
            self.story_names.sort()
            self.story_names.append("")  # Keep the blank entry
            self.story_title['values'] = self.story_names
            self.story_title_var.set("")  # Clear the selected story after deletion

        except Exception as e:
            messagebox.showerror("Error", f"删除故事失败: {e}")


            












    def create_llm_config_tab_content(self):
        # Configuration Selection Frame
        config_select_frame = tk.Frame(self.llm_config_tab)
        config_select_frame.pack(pady=5)

        self.config_names = []  # List to store configuration names
        self.config_selection_var = tk.StringVar()
        self.config_selection_dropdown = ttk.Combobox(config_select_frame, textvariable=self.config_selection_var, values=self.config_names, state="readonly")
        self.config_selection_dropdown.pack(side=tk.LEFT, padx=5)
        self.config_selection_dropdown.bind("<<ComboboxSelected>>", self.on_config_select)  # Binding Selection

        add_config_button = tk.Button(config_select_frame, text="➕ 新增", command=self.add_llm_config)
        add_config_button.pack(side=tk.LEFT, padx=5)

        copy_config_button = tk.Button(config_select_frame, text="📋 复制", command=self.copy_llm_config)
        copy_config_button.pack(side=tk.LEFT, padx=5)

        delete_config_button = ttk.Button(config_select_frame, text="🗑 删除", command=self.delete_llm_config, bootstyle="danger")
        delete_config_button.pack(side=tk.LEFT, padx=5)

        integration_config_button = tk.Button(config_select_frame, text="⚙️ 接入模型配置", command=self.open_integration_window)
        integration_config_button.pack(side=tk.LEFT, pady=10, padx=5)

        # Main Content Frame
        main_content_frame = tk.Frame(self.llm_config_tab)
        main_content_frame.pack(pady=5, fill=tk.BOTH, expand=True)

        basic_info_frame = tk.LabelFrame(main_content_frame, text="基本信息配置区")
        basic_info_frame.pack(side=tk.TOP, padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Basic Information Variables and Labels/Entries
        # Use grid layout for inline labels and entries
        row = 0
        self.model_baseurl_var = tk.StringVar()
        model_baseurl_label = tk.Label(basic_info_frame, text="模型baseurl")
        model_baseurl_label.grid(row=row, column=0, sticky=W, padx=5, pady=2)
        self.model_baseurl_entry = tk.Entry(basic_info_frame, textvariable=self.model_baseurl_var, width=120)
        self.model_baseurl_entry.grid(row=row, column=1, sticky=E, padx=5, pady=2)
        row += 1

        self.api_key_var = tk.StringVar()
        api_key_label = tk.Label(basic_info_frame, text="api-key")
        api_key_label.grid(row=row, column=0, sticky=W, padx=5, pady=2)
        self.api_key_entry = tk.Entry(basic_info_frame, textvariable=self.api_key_var, width=120)
        self.api_key_entry.grid(row=row, column=1, sticky=E, padx=5, pady=2)
        row += 1

        save_button = tk.Button(basic_info_frame, text="💾 保存", command=self.save_llm_config,
                                   font=("Microsoft YaHei", 12))
        save_button.grid(row=row, column=1, sticky=W, padx=5, pady=2)
        row += 1

        # Model Configuration Frame
        model_config_frame = tk.LabelFrame(main_content_frame, text="模型配置")
        model_config_frame.pack(side=tk.TOP, padx=10, pady=10, fill=tk.BOTH, expand=True)

        row = 0

        # Model Management Frame - Moved Inside Model Config Frame
        model_management_frame = tk.Frame(model_config_frame) # Changed parent to model_config_frame
        model_management_frame.grid(row=row, column=0, columnspan=2, sticky=W + E, padx=5, pady=5)
        row += 1

        add_model_button = ttk.Button(model_management_frame, text="➕ 新增模型", command=self.add_llm_model)
        add_model_button.pack(side=tk.LEFT, padx=5)

        delete_model_button = ttk.Button(model_management_frame, text="🗑 删除模型", command=self.delete_llm_model, bootstyle="danger")
        delete_model_button.pack(side=tk.LEFT, padx=5)

        get_models_button = ttk.Button(model_management_frame, text="📥 从服务器获取模型", command=self.get_models_from_server)
        get_models_button.pack(side=tk.LEFT, padx=5)

        # Add the "测试模型" button
        test_model_button = ttk.Button(model_management_frame, text="✔ 测试模型", command=self.test_llm_model)
        test_model_button.pack(side=tk.LEFT, padx=5)

        # Model Selection Frame - Moved Inside Model Config Frame
        model_selection_frame = ttk.Frame(model_config_frame)  # Changed parent to model_config_frame
        model_selection_frame.grid(row=row, column=0, columnspan=2, sticky=W + E, padx=5, pady=5)
        row += 1

        model_label = tk.Label(model_selection_frame, text="选择模型")
        model_label.pack(side=tk.LEFT, padx=5)

        self.model_names = []  # List to store model names for the current config
        self.model_selection_var = tk.StringVar()
        self.model_selection_dropdown = ttk.Combobox(model_selection_frame, textvariable=self.model_selection_var, values=self.model_names, state="readonly")
        self.model_selection_dropdown.pack(side=tk.LEFT, padx=5)
        self.model_selection_dropdown.bind("<<ComboboxSelected>>", self.on_model_select)

        self.current_model_name_var = tk.StringVar() # Track current model name

        self.model_retry_var = tk.StringVar(value="3")  # Default value
        model_retry_label = tk.Label(model_config_frame, text="最大尝试次数") # Parent is now model_config_frame
        model_retry_label.grid(row=row, column=0, sticky=W, padx=5, pady=2)
        self.model_retry_entry = tk.Entry(model_config_frame, textvariable=self.model_retry_var, width=10) # Parent is now model_config_frame
        self.model_retry_entry.grid(row=row, column=1, sticky=E, padx=5, pady=2)
        self.model_retry_entry.config(validate="key")
        self.model_retry_entry.config(validatecommand=(self.model_retry_entry.register(self.llm_validate_range_retry), '%P'))
        row += 1

        self.temperature_var = tk.StringVar()
        temperature_label = tk.Label(model_config_frame, text="temperature") # Parent is now model_config_frame
        temperature_label.grid(row=row, column=0, sticky=W, padx=5, pady=2)
        self.temperature_entry = tk.Entry(model_config_frame, textvariable=self.temperature_var, width=10) # Parent is now model_config_frame
        self.temperature_entry.grid(row=row, column=1, sticky=E, padx=5, pady=2)
        self.temperature_entry.config(validate="key")
        self.temperature_entry.config(validatecommand=(self.temperature_entry.register(self.llm_validate_range_temperature), '%P'))
        row += 1

        self.top_p_var = tk.StringVar()
        top_p_label = tk.Label(model_config_frame, text="top_p") # Parent is now model_config_frame
        top_p_label.grid(row=row, column=0, sticky=W, padx=5, pady=2)
        self.top_p_entry = tk.Entry(model_config_frame, textvariable=self.top_p_var, width=10) # Parent is now model_config_frame
        self.top_p_entry.grid(row=row, column=1, sticky=E, padx=5, pady=2)
        row += 1

        self.frequency_penalty_var = tk.StringVar()
        frequency_penalty_label = tk.Label(model_config_frame, text="frequency_penalty") # Parent is now model_config_frame
        frequency_penalty_label.grid(row=row, column=0, sticky=W, padx=5, pady=2)
        self.frequency_penalty_entry = tk.Entry(model_config_frame, textvariable=self.frequency_penalty_var, width=10) # Parent is now model_config_frame
        self.frequency_penalty_entry.grid(row=row, column=1, sticky=E, padx=5, pady=2)
        self.frequency_penalty_entry.config(validate="key")
        self.frequency_penalty_entry.config(validatecommand=(self.frequency_penalty_entry.register(self.llm_validate_range_penalty), '%P'))
        row += 1

        self.presence_penalty_var = tk.StringVar()
        presence_penalty_label = tk.Label(model_config_frame, text="presence_penalty") # Parent is now model_config_frame
        presence_penalty_label.grid(row=row, column=0, sticky=W, padx=5, pady=2)
        self.presence_penalty_entry = tk.Entry(model_config_frame, textvariable=self.presence_penalty_var, width=10) # Parent is now model_config_frame
        self.presence_penalty_entry.grid(row=row, column=1, sticky=E, padx=5, pady=2)
        self.presence_penalty_entry.config(validate="key")
        self.presence_penalty_entry.config(validatecommand=(self.presence_penalty_entry.register(self.llm_validate_range_penalty), '%P'))
        row += 1

        self.max_tokens_var = tk.StringVar()
        max_tokens_label = tk.Label(model_config_frame, text="max_tokens") # Parent is now model_config_frame
        max_tokens_label.grid(row=row, column=0, sticky=W, padx=5, pady=2)
        self.max_tokens_entry = tk.Entry(model_config_frame, textvariable=self.max_tokens_var, width=10) # Parent is now model_config_frame
        self.max_tokens_entry.grid(row=row, column=1, sticky=E, padx=5, pady=2)
        self.max_tokens_entry.config(validate="key")
        self.max_tokens_entry.config(validatecommand=(self.max_tokens_entry.register(self.llm_validate_range_retry), '%P'))
        row += 1

        # Save Model Config Button
        self.save_model_config_button = tk.Button(model_config_frame, text="💾保存模型配置", command=self.save_current_model_config,
                                   font=("Microsoft YaHei", 14)) # Parent is now model_config_frame
        self.save_model_config_button.grid(row=row, column=0, columnspan=2, pady=10)

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
            if new_config_name in self.config_names:
                self.show_message_bubble("错误", "配置名称已存在")
                return

            self.config_names.append(new_config_name)
            self.config_selection_dropdown['values'] = self.config_names  # Update dropdown list
            self.config_selection_var.set(new_config_name)  # Select the new configuration
            self.model_names = [] # Clear model names
            self.model_selection_dropdown['values'] = self.model_names
            self.clear_llm_config_values()
            self.clear_model_config_values()

    def copy_llm_config(self):
        """Copies the selected LLM configuration to a new configuration."""
        selected_config = self.config_selection_var.get()
        if not selected_config:
            self.show_message_bubble("错误", "请选择要复制的配置")
            return

        new_config_name = simpledialog.askstring("📄 复制配置", "请输入复制后的配置名称:", parent=self.master)
        if new_config_name:
            if new_config_name in self.config_names:
                self.show_message_bubble("错误", "配置名称已存在")
                return

            self.config_names.append(new_config_name)
            self.config_selection_dropdown['values'] = self.config_names
            self.config_selection_var.set(new_config_name)

            # Copy values from selected config
            self.load_llm_config_values(selected_config)
            self.save_llm_config()

    def delete_llm_config(self):
        """Deletes the selected LLM configuration."""
        selected_config = self.config_selection_var.get()

        if not selected_config:
            self.show_message_bubble("错误", "请选择要删除的配置")
            return

        self.config_names.remove(selected_config)
        self.config_selection_dropdown['values'] = self.config_names

        # Delete configurations from the config file
        for key in list(self.config["模型"]):
            if key.startswith(f"config_{selected_config}_"):
                self.config.remove_option('模型', key)
        with open(self.config_file, "w", encoding="utf-8") as configfile:
            self.config.write(configfile)
        self.show_message_bubble("Success", "已删除")
        # Select the first configuration, if available
        if self.config_names:
            self.config_selection_var.set(self.config_names[0])
            self.load_llm_config_values(self.config_names[0])
        else:
            self.config_selection_var.set("")  # Clear selection
            self.clear_llm_config_values()
            self.clear_model_config_values()

    def load_llm_config(self):
        """Loads LLM configurations from config.txt."""
        try:
            self.config.read(self.config_file, encoding="utf-8")
            if "模型" not in self.config:
                self.config["模型"] = {}
            # Load configuration names
            self.config_names = sorted(list({name.split('_')[1] for name in self.config["模型"] if name.startswith("config_")}))  # Extract unique config names
            self.config_selection_dropdown['values'] = self.config_names

            if self.config_names:
                self.config_selection_var.set(self.config_names[0])  # Select the first configuration
                self.load_llm_config_values(self.config_names[0])  # Load its values

        except FileNotFoundError:
            print("Config file not found, creating a new one.")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading LLM config: {e}")

    def save_llm_config(self):
        """Saves the LLM configuration to config.txt."""
        try:
            if "模型" not in self.config:
                self.config["模型"] = {}

            selected_config = self.config_selection_var.get()

            # Save basic information
            if selected_config:
                self.config["模型"][f"config_{selected_config}_model_baseurl"] = self.model_baseurl_var.get()
                self.config["模型"][f"config_{selected_config}_api_key"] = self.api_key_var.get()

            with open(self.config_file, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)
            self.show_message_bubble("Success", "成功保存配置信息！")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving LLM config: {e}")

    def load_llm_config_values(self, config_name):
        """Loads the values for a specific LLM configuration."""
        try:
            self.config.read(self.config_file, encoding="utf-8")

            # Load basic information
            self.model_baseurl_var.set(self.config["模型"].get(f"config_{config_name}_model_baseurl", ""))
            self.api_key_var.set(self.config["模型"].get(f"config_{config_name}_api_key", ""))

            # Load model names and select the first one
            models_json = self.config["模型"].get(f"config_{config_name}_models", "[]")
            self.models = json.loads(models_json)
            self.model_names = [model["name"] for model in self.models]
            self.model_selection_dropdown['values'] = self.model_names

            if self.model_names:
                self.model_selection_var.set(self.model_names[0])
                self.load_model_config_values(self.model_names[0])
            else:
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
            url=base_url.replace("chat/completions","models")
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
            # Simulate network request delay
            #time.sleep(2)
            # Placeholder for actual API call
            # In a real application, you would make an HTTP request here
            # response = requests.get(f"{base_url}/models", headers={"api-key": api_key})
            # models_from_server = response.json()
            #models_from_server = ["deepseek-r1", "deepseek-v3", "model3", "m"]  # Placeholder response

            # Filter out existing models



            # Display selection dialog in the main thread
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

        for model in self.models:
            if model["name"] == model_name:
                model["max_retry"] = self.model_retry_var.get()
                model["temperature"] = self.temperature_var.get()
                model["top_p"] = self.top_p_var.get()
                model["frequency_penalty"] = self.frequency_penalty_var.get()
                model["presence_penalty"]=self.presence_penalty_var.get()
                model["max_tokens"] = self.max_tokens_var.get()
                break

        # Save the updated models list to the config file
        models_json = json.dumps(self.models, ensure_ascii=False)
        self.config["模型"][f"config_{selected_config}_models"] = models_json

        with open(self.config_file, "w", encoding="utf-8") as configfile:
            self.config.write(configfile)

    def open_integration_window(self):
        """Opens a new window for integration configuration."""
        integration_window = tk.Toplevel(self.master)
        integration_window.title("接入模型配置区")

        # Calculate the center position
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        window_width = 800  # Adjust as needed
        window_height = 600  # Adjust as needed
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        integration_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Make the window modal and stay on top
        integration_window.transient(self.master) # Make it a child of the main window
        integration_window.grab_set()            # Grab all events for this window

        # Create a notebook (tabbed interface)
        notebook = ttk.Notebook(integration_window)
        notebook.pack(fill="both", expand=True)

        # Create tabs
        tab_names = ["默认", "大纲", "正文", "选项", "人物", "背景", "音乐","对话","总结", "其他"]
        self.tabs = {}
        for tab_name in tab_names:
            tab = ModelSettingTab(notebook, self, tab_name)
            notebook.add(tab.frame, text=tab_name)
            self.tabs[tab_name] = tab

        # Create prompts tab
        self.prompt_tab = PromptConfigTab(notebook, self)
        notebook.add(self.prompt_tab.frame, text="提示词")
        
    def test_llm_model(self):
        """Tests the currently selected LLM model."""
        base_url = self.model_baseurl_var.get()
        api_key = self.api_key_var.get()
        model_name = self.current_model_name_var.get()

        if not base_url or not api_key or not model_name:
            self.show_message_bubble("错误", "请先填写模型baseurl、api-key和选择模型")
            return

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

            response = requests.post(base_url, headers=headers, data=data)
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
        # --- Cloud Sovits Switch and API Key ---
        self.sovits_frame = ttk.Frame(self.sovits_tab)
        self.sovits_frame.pack(side="top", fill="x", padx=5, pady=5)

        self.cloud_sovits_switch_var = tk.BooleanVar()
        self.cloud_sovits_switch = ttk.Checkbutton(self.sovits_frame, variable=self.cloud_sovits_switch_var,
                                               bootstyle="round-toggle")
        self.cloud_sovits_switch.pack(side="left", padx=5, pady=5)
        self.cloud_sovits_switch_label = tk.Label(self.sovits_frame, text="云端语音合成开关")
        self.cloud_sovits_switch_label.pack(side="left", padx=5, pady=5)

        self.sovits_api_key_label = tk.Label(self.sovits_frame, text="api key输入框")
        self.sovits_api_key_label.pack(side="left", padx=5, pady=5)
        self.sovits_api_key_entry = tk.Entry(self.sovits_frame, width=80)
        self.sovits_api_key_entry.pack(side="left", padx=0, pady=5)

        # --- File Paths, Text Content, and Model Names ---
        self.sovits_entries_frame = ttk.Frame(self.sovits_tab)
        self.sovits_entries_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        self.file_path_entries = []
        self.text_content_entries = []
        self.model_name_entries = []

        for i in range(7):
            frame = ttk.Frame(self.sovits_entries_frame)
            frame.pack(side="top", fill="x", padx=5, pady=2)

            file_path_label = tk.Label(frame, text=f"文件{i+1}")
            file_path_label.pack(side="left", padx=2, pady=2)
            file_path_entry = tk.Text(frame, width=50,height=2)
            file_path_entry.pack(side="left", padx=2, pady=2)
            self.file_path_entries.append(file_path_entry)

            select_button = tk.Button(frame, text="📁", command=lambda idx=i: self.select_file(idx))
            select_button.pack(side="left", padx=2, pady=2)

            text_content_label = tk.Label(frame, text=f"文本{i + 1}")
            text_content_label.pack(side="left", padx=2, pady=2)
            text_content_entry = tk.Text(frame, width=40,height=2)
            text_content_entry.pack(side="left", padx=2, pady=2)
            self.text_content_entries.append(text_content_entry)

            model_name_label = tk.Label(frame, text=f"模型{i + 1}")
            model_name_label.pack(side="left", padx=2, pady=2)
            model_name_entry = tk.Text(frame, width=25,height=2)
            model_name_entry.pack(side="left", padx=2, pady=2)
            self.model_name_entries.append(model_name_entry)

        # --- Buttons at the bottom ---
        self.sovits_buttons_frame = ttk.Frame(self.sovits_tab)
        self.sovits_buttons_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        self.fill_text_button = tk.Button(self.sovits_buttons_frame, text="✍️一键填入文本内容", command=self.fill_text_content)
        self.fill_text_button.pack(side="left", padx=100, pady=5)

        self.model_name_label = tk.Label(self.sovits_buttons_frame, text="模型名称")
        self.model_name_label.pack(side="left", padx=5, pady=5)
        self.model_name_all_entry = tk.Entry(self.sovits_buttons_frame, width=20)
        self.model_name_all_entry.pack(side="left", padx=5, pady=5)

        self.fill_model_button = tk.Button(self.sovits_buttons_frame, text="✍️一键填入", command=self.fill_model_names)
        self.fill_model_button.pack(side="left", padx=5, pady=5)

        self.save_sovits_button = tk.Button(self.sovits_buttons_frame, text="💾 保存", command=self.save_sovits_config)
        self.save_sovits_button.pack(side="right", padx=5, pady=5)
        self.load_sovits_config()


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
                name_without_extension=re.sub(r'\【.*?\】', '', name_without_extension)
                name_without_extension=re.sub(r'\[.*?\]', '', name_without_extension)
                self.text_content_entries[i].insert("1.0",name_without_extension )
    def fill_model_names(self):
        model_name = self.model_name_all_entry.get()
        for i, model_name_entry in enumerate(self.model_name_entries):
            model_name_entry.delete("1.0", tk.END)
            model_name_entry.insert("1.0", model_name)

    def load_sovits_config(self):
        try:
            self.config.read(self.config_file, encoding="utf-8")

            if "SOVITS" in self.config:
                # Load switch state
                if "if_cloud" in self.config["SOVITS"]:
                    self.cloud_sovits_switch_var.set(self.config["SOVITS"].getboolean("if_cloud"))
                # Load api key
                if "api_key" in self.config["SOVITS"]:
                    self.sovits_api_key_entry.insert(0, self.config["SOVITS"].get("api_key", ""))
                # Load file paths, text content, and model names
                for i in range(7):
                    path_key = f"path{i+1}"
                    text_key = f"text{i+1}"
                    model_key = f"model{i+1}"

                    if path_key in self.config["SOVITS"]:
                        self.file_path_entries[i].delete("1.0", tk.END)
                        self.file_path_entries[i].insert("1.0", self.config["SOVITS"].get(path_key, ""))
                    if text_key in self.config["SOVITS"]:
                        self.text_content_entries[i].delete("1.0", tk.END)
                        self.text_content_entries[i].insert("1.0", self.config["SOVITS"].get(text_key, ""))
                    if model_key in self.config["SOVITS"]:
                        self.model_name_entries[i].delete("1.0", tk.END)
                        self.model_name_entries[i].insert("1.0", self.config["SOVITS"].get(model_key, ""))

        except FileNotFoundError:
            print("Config file not found, creating a new one.")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading sovits config: {e}")

    def save_sovits_config(self):
        try:
            # Create the SOVITS section if it doesn't exist
            if "SOVITS" not in self.config:
                self.config["SOVITS"] = {}

            # Save switch state
            self.config["SOVITS"]["if_cloud"] = str(self.cloud_sovits_switch_var.get())
            #Save api key
            self.config["SOVITS"]["api_key"] = str(self.sovits_api_key_entry.get())
            # Save file paths, text content, and model names
            for i in range(7):
                path_key = f"path{i+1}"
                text_key = f"text{i+1}"
                model_key = f"model{i+1}"

                self.config["SOVITS"][path_key] = self.file_path_entries[i].get("1.0", tk.END)
                self.config["SOVITS"][text_key] = self.text_content_entries[i].get("1.0", tk.END)
                self.config["SOVITS"][model_key] = self.model_name_entries[i].get("1.0", tk.END)

            with open(self.config_file, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)

            self.show_message_bubble("Success", "语音配置已保存")
            #show_message_bubble(self,"Success", "Sovits Configuration saved successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving sovits config: {e}")








    def create_ai_draw_config_tab_content(self):
        # --- Top Row Frame ---
        top_row_frame = tk.Frame(self.ai_draw_config_tab)
        top_row_frame.pack(pady=5, fill=tk.X)

        # AI Drawing Switch
        self.cloud_on_var = tk.BooleanVar(value=self.config.getboolean('AI_draw', 'cloud_on', fallback=False))
        self.cloud_on_switch = ttk.Checkbutton(top_row_frame, text="AI绘画开关", variable=self.cloud_on_var,
                                               bootstyle="round-toggle")
        self.cloud_on_switch.pack(side=tk.LEFT, padx=5)

        # Config Edit
        config_edit_frame = tk.Frame(top_row_frame)
        config_edit_frame.pack(side=tk.LEFT, padx=5)
        self.config_edit_label = ttk.Label(config_edit_frame, text="配置编辑")
        self.config_edit_label.pack(side=tk.LEFT)
        self.config_edit_combo = ttk.Combobox(config_edit_frame, state="readonly")
        self.config_edit_combo.pack(side=tk.LEFT, padx=5)
        self.config_edit_combo.bind("<<ComboboxSelected>>", lambda event: [self.ai_draw_load_selected_config(event), self.clear_dropdown_selection(event)])
        self.config_edit_combo.bind("<Button-1>", self.clear_dropdown_selection)

        self.add_config_button = ttk.Button(config_edit_frame, text="➕ 新增", command=self.ai_draw_add_config)
        self.add_config_button.pack(side=tk.LEFT, padx=5)
        self.delete_config_button = ttk.Button(config_edit_frame, text="🗑 删除", command=self.ai_draw_delete_config,
                                   bootstyle="danger")
        self.delete_config_button.pack(side=tk.LEFT, padx=5)

        # New Buttons Frame
        new_buttons_frame = tk.Frame(top_row_frame)
        new_buttons_frame.pack(side=tk.LEFT, padx=5)

        self.rename_config_button = ttk.Button(new_buttons_frame, text="🖋 配置改名", command=self.ai_draw_rename_config,
                                        bootstyle="secondary")
        self.rename_config_button.pack(side=tk.LEFT, padx=5)

        self.copy_config_button = ttk.Button(new_buttons_frame, text="📋 复制配置", command=self.ai_draw_copy_config)
        self.copy_config_button.pack(side=tk.LEFT, padx=5)


        # Save Button
        self.save_button = ttk.Button(top_row_frame, text="💾 保存", command=self.ai_draw_save_current_config)  # Modified save command
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.person_background_config_button = ttk.Button(top_row_frame, text="⚙️ 人物与背景绘画设置", command=self.ai_draw_open_character_background_settings)
        self.person_background_config_button.pack(side=tk.LEFT, padx=5)

        # --- Configuration Area ---
        self.config_frame = tk.Frame(self.ai_draw_config_tab)
        self.config_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        self.ai_draw_create_config_widgets(self.config_frame)
        self.configs = self.ai_draw_load_config_names()
        self.ai_draw_load_all_configs()


    def ai_draw_rename_config(self):
        current_config = self.config_edit_combo.get()
        if not current_config:
            messagebox.showerror("错误", "请选择要改名的配置！")
            return

        new_config_name = simpledialog.askstring("配置改名", "请输入新的配置名称:", initialvalue=current_config)
        if new_config_name:
            if new_config_name in self.configs:
                messagebox.showerror("错误", "配置名称已存在！")
                return

            # Rename in the list
            index = self.configs.index(current_config)
            self.configs[index] = new_config_name

            # Update comboboxes
            self.ai_draw_update_comboboxes()
            self.config_edit_combo.set(new_config_name)

            # Rename in config.ini
            for key, value in list(self.config['AI_draw'].items()):
                if key.startswith(f'config_{current_config}_'):
                    new_key = key.replace(f'config_{current_config}_', f'config_{new_config_name}_')
                    self.config['AI_draw'][new_key] = value
                    self.config['AI_draw'].pop(key)

            self.ai_draw_save_config()
            self.ai_draw_load_selected_config()
            self.show_message_bubble("Success", "配置已改名！")

    def ai_draw_copy_config(self):
        current_config = self.config_edit_combo.get()
        if not current_config:
            messagebox.showerror("错误", "请选择要复制的配置！")
            return

        new_config_name = simpledialog.askstring("复制配置", "请输入复制后的配置名称:")
        if new_config_name:
            if new_config_name in self.configs:
                messagebox.showerror("错误", "配置名称已存在！")
                return

            self.configs.append(new_config_name)
            self.ai_draw_update_comboboxes()
            self.config_edit_combo.set(new_config_name)

            # Copy values in config.ini
            for key, value in self.config['AI_draw'].items():
                if key.startswith(f'config_{current_config}_'):
                    new_key = key.replace(f'config_{current_config}_', f'config_{new_config_name}_')
                    self.config['AI_draw'][new_key] = value

            self.ai_draw_save_config()
            self.ai_draw_load_selected_config()
            self.show_message_bubble("Success", "配置已复制！")

    def ai_draw_open_character_background_settings(self):
        self.character_background_window = tk.Toplevel(self.master)
        self.character_background_window.title("人物与背景绘画设置")

        # Window settings
        window_width = 800
        window_height = 600
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = int((screen_width / 2) - (window_width / 2))
        y = int((screen_height / 2) - (window_height / 2))
        self.character_background_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.character_background_window.resizable(False, False)

        # --- Notebook (Tabs) ---
        self.character_background_notebook = ttk.Notebook(self.character_background_window)
        self.character_tab = ttk.Frame(self.character_background_notebook)
        self.background_tab = ttk.Frame(self.character_background_notebook)
        self.character_background_notebook.add(self.character_tab, text="人物绘画配置区")
        self.character_background_notebook.add(self.background_tab, text="背景绘画配置区")
        self.character_background_notebook.pack(expand=True, fill="both")

        self.ai_draw_create_character_tab_content(self.character_tab)
        self.ai_draw_create_background_tab_content(self.background_tab)

    def ai_draw_create_character_tab_content(self, parent):
        # --- Character Tab Content ---
        self.character_config_entries = []

        # "绘制非主要人物" Switch
        self.draw_non_main_character_var = tk.BooleanVar(value=False)
        self.draw_non_main_character_switch = ttk.Checkbutton(parent, text="绘制非主要人物", variable=self.draw_non_main_character_var,
                                               bootstyle="round-toggle")
        self.draw_non_main_character_switch.pack(pady=5, anchor=tk.W)

        # Frame for buttons
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, anchor=tk.W)

        # "新增" button
        self.add_character_config_button = ttk.Button(button_frame, text="➕ 新增", command=lambda: self.ai_draw_add_config_entry(self.character_tab, self.character_config_entries))
        self.add_character_config_button.pack(side=tk.LEFT, padx=5)

        # "保存" button
        self.save_character_config_button = ttk.Button(button_frame, text="💾 保存", command=self.ai_draw_save_character_config)
        self.save_character_config_button.pack(side=tk.LEFT, padx=5)

        tip_text = "开启绘制非主要人物则会尝试为配角生成AI绘画提示词并生成图片，这会增加LLM模型和AI绘图消耗量（尚未写逻辑，暂时保持关闭）。程序优先选择优先级最高的图像生成模型，并在同等优先级的模型中，根据预设的权重分配生成任务，权重高的模型承担更多任务。当高优先级模型达到并发上限或生成失败时，程序会动态调整任务分配，或自动切换到较低优先级的模型继续生成。"
        self.hover_button = HoverButton(button_frame, tooltip_text=tip_text)
        self.hover_button.pack(pady=20)

        # Header labels frame
        header_labels_frame = tk.Frame(parent)
        header_labels_frame.pack(fill=tk.X, anchor=tk.W)

        # Header labels
        model_label = ttk.Label(header_labels_frame, text="模型", width=28)  # Adjust width as needed
        model_label.pack(side=tk.LEFT, padx=5)
        weight_label = ttk.Label(header_labels_frame, text="权重", width=6)  # Adjust width as needed
        weight_label.pack(side=tk.LEFT, padx=5)
        priority_label = ttk.Label(header_labels_frame, text="优先级", width=5)  # Adjust width as needed
        priority_label.pack(side=tk.LEFT, padx=5)

        self.ai_draw_load_character_config(self.character_tab, self.character_config_entries)

    def ai_draw_create_background_tab_content(self, parent):
        # --- Background Tab Content ---
        self.background_config_entries = []

        # Frame for "传入上下文" and "传入条数"
        context_frame = tk.Frame(parent)
        context_frame.pack(fill=tk.X, anchor=tk.W, pady=5)

        # "传入上下文" Label and Dropdown
        self.convey_context_label = ttk.Label(context_frame, text="传入上下文")
        self.convey_context_label.pack(side=tk.LEFT, padx=5)

        self.convey_context_var = tk.StringVar(value="不传入")  # Default value
        self.convey_context_combo = ttk.Combobox(context_frame, textvariable=self.convey_context_var,
                                                        values=["不传入", "部分传入", "全部传入"], state="readonly", width=10)
        self.convey_context_combo.pack(side=tk.LEFT, padx=5)
        self.convey_context_combo.bind("<<ComboboxSelected>>", lambda event: [self.ai_draw_toggle_context_entry(event), self.clear_dropdown_selection(event)])

        # "传入条数" Entry (initially hidden)
        self.context_entry_label = ttk.Label(context_frame, text="传入条数")
        self.context_entry = ttk.Entry(context_frame, width=5)
        self.context_entry_label.pack(side=tk.LEFT, padx=5)
        self.context_entry.pack(side=tk.LEFT, padx=5)

        # Frame to hold label and entry
        self.context_entry_frame = context_frame # Reuse the context_frame
        self.ai_draw_toggle_context_entry() # Initial toggle

        # Frame for buttons
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, anchor=tk.W)

        # "新增" button
        self.add_background_config_button = ttk.Button(button_frame, text="➕ 新增", command=lambda: self.ai_draw_add_config_entry(self.background_tab, self.background_config_entries))
        self.add_background_config_button.pack(side=tk.LEFT, padx=5)

        # "保存" button
        self.save_background_config_button = ttk.Button(button_frame, text="💾 保存", command=self.ai_draw_save_background_config)
        self.save_background_config_button.pack(side=tk.LEFT, padx=5)

        tip_text = "传入上下文选项是指，LLM模型会传入最近对话的多少条来生成背景绘画提示词，这是为了使生成的背景图更贴近故事。程序优先选择优先级最高的图像生成模型，并在同等优先级的模型中，根据预设的权重分配生成任务，权重高的模型承担更多任务。当高优先级模型达到并发上限或生成失败时，程序会动态调整任务分配，或自动切换到较低优先级的模型继续生成。"
        self.hover_button = HoverButton(button_frame, tooltip_text=tip_text)
        self.hover_button.pack(pady=20)

        # Header labels frame
        header_labels_frame = tk.Frame(parent)
        header_labels_frame.pack(fill=tk.X, anchor=tk.W)

        # Header labels
        model_label = ttk.Label(header_labels_frame, text="模型", width=28)  # Adjust width as needed
        model_label.pack(side=tk.LEFT, padx=5)
        weight_label = ttk.Label(header_labels_frame, text="权重", width=6)  # Adjust width as needed
        weight_label.pack(side=tk.LEFT, padx=5)
        priority_label = ttk.Label(header_labels_frame, text="优先级", width=5)  # Adjust width as needed
        priority_label.pack(side=tk.LEFT, padx=5)

        self.ai_draw_load_background_config(self.background_tab, self.background_config_entries)

    def ai_draw_add_config_entry(self, parent, config_entries):
        entry_frame = tk.Frame(parent)
        entry_frame.pack(fill=tk.X, anchor=tk.W)

        # Model dropdown
        model_var = tk.StringVar()
        model_combo = ttk.Combobox(entry_frame, textvariable=model_var, values=self.configs, state="readonly", width=25)
        model_combo.pack(side=tk.LEFT, padx=5)
        model_combo.bind("<<ComboboxSelected>>", self.clear_dropdown_selection)

        # Weight entry (positive integers only)
        weight_var = tk.StringVar(value="1")  # Default weight is 1
        weight_entry = ttk.Entry(entry_frame, textvariable=weight_var, width=5)
        weight_entry.pack(side=tk.LEFT, padx=5)
        weight_entry.config(validate="key")
        weight_entry.config(validatecommand=(weight_entry.register(self.ai_draw_validate_positive_int), '%P'))

        # Priority entry (natural numbers only)
        priority_var = tk.StringVar(value="0")  # Default priority is 0
        priority_entry = ttk.Entry(entry_frame, textvariable=priority_var, width=5)
        priority_entry.pack(side=tk.LEFT, padx=5)
        priority_entry.config(validate="key")
        priority_entry.config(validatecommand=(priority_entry.register(self.ai_draw_validate_natural_number), '%P'))

        # Delete button
        delete_button = ttk.Button(entry_frame, text="🗑 删除", command=lambda: self.ai_draw_delete_config_entry(entry_frame, config_entries), bootstyle="danger")
        delete_button.pack(side=tk.LEFT, padx=5)
        
        test_button = ttk.Button(entry_frame, text="✔ 测试", command=lambda: self.ai_draw_test_config(model_combo.get(),parent))
        test_button.pack(side=tk.LEFT, padx=5)

        config_entries.append({
            "frame": entry_frame,
            "model_var": model_var,
            "model_combo": model_combo,
            "weight_var": weight_var,
            "weight_entry": weight_entry,
            "priority_var": priority_var,
            "priority_entry": priority_entry
        })

    def ai_draw_test_config(self,model,name):
        if str(name).endswith("frame"):
            kind='character'
        else:
            kind='background'
        threading.Thread(target=self._ai_draw_test_config, args=(str(model),str(kind),)).start()
        self.show_message_bubble("","开始测试")
    def _ai_draw_test_config(self,model,kind):
        try:
            result=gui_functions.test_ai_draw(model,kind)
            if result=="succeess":
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

    def ai_draw_load_character_config(self, parent, config_entries):
        config_str = self.config.get('AI_draw', 'character_config', fallback='[]')
        try:
            config_data = json.loads(config_str)

            # Sort the configuration data based on priority (ascending) and weight (descending)
            config_data.sort(key=lambda x: (-x['priority'], -x['weigh']))

            for item in config_data:
                self.ai_draw_add_config_entry(parent, config_entries)
                entry = config_entries[-1]
                entry["model_var"].set(item["config"])
                entry["weight_var"].set(str(item["weigh"]))
                entry["priority_var"].set(str(item["priority"]))
        except json.JSONDecodeError:
            print("Error decoding character config JSON")

        # Load the "绘制非主要人物" switch state
        self.draw_non_main_character_var.set(self.config.getboolean('AI_draw', 'draw_non_main_character', fallback=False))

    def ai_draw_save_character_config(self):
        config_data = []
        for entry in self.character_config_entries:
            config_data.append({
                "config": entry["model_var"].get(),
                "weigh": int(entry["weight_var"].get()),
                "priority": int(entry["priority_var"].get())
            })
        config_str = json.dumps(config_data)
        self.config.set('AI_draw', 'character_config', config_str)

        # Save the "绘制非主要人物" switch state
        self.config.set('AI_draw', 'draw_non_main_character', str(self.draw_non_main_character_var.get()))

        self.ai_draw_save_config()
        self.show_message_bubble("Success", "人物配置已保存！")

    def ai_draw_load_background_config(self, parent, config_entries):
        config_str = self.config.get('AI_draw', 'background_config', fallback='[]')
        try:
            config_data = json.loads(config_str)

            # Sort the configuration data based on priority (ascending) and weight (descending)
            config_data.sort(key=lambda x: (x['priority'], -x['weigh']))

            for item in config_data:
                self.ai_draw_add_config_entry(parent, config_entries)
                entry = config_entries[-1]
                entry["model_var"].set(item["config"])
                entry["weight_var"].set(str(item["weigh"]))
                entry["priority_var"].set(str(item["priority"]))
        except json.JSONDecodeError:
            print("Error decoding background config JSON")

        # Load the "传入上下文" options
        self.convey_context_var.set(self.config.get('AI_draw', 'convey_context', fallback='不传入'))
        if self.config.has_option('AI_draw', 'context_entry'):
            self.context_entry.delete(0, tk.END)
            self.context_entry.insert(0, self.config.get('AI_draw', 'context_entry', fallback=''))
        self.ai_draw_toggle_context_entry()

    def ai_draw_save_background_config(self):
        config_data = []
        for entry in self.background_config_entries:
            config_data.append({
                "config": entry["model_var"].get(),
                "weigh": int(entry["weight_var"].get()),
                "priority": int(entry["priority_var"].get())
            })
        config_str = json.dumps(config_data)
        self.config.set('AI_draw', 'background_config', config_str)

        # Save the "传入上下文" options
        self.config.set('AI_draw', 'convey_context', self.convey_context_var.get())
        self.config.set('AI_draw', 'context_entry', self.context_entry.get())

        self.ai_draw_save_config()
        self.show_message_bubble("Success", "背景配置已保存！")

    def ai_draw_toggle_context_entry(self, event=None):
        if self.convey_context_var.get() == "部分传入":
            self.context_entry_label.pack(side=tk.LEFT, padx=5)
            self.context_entry.pack(side=tk.LEFT, padx=5)
        else:
            self.context_entry_label.pack_forget()
            self.context_entry.pack_forget()


    def ai_draw_create_config_widgets(self, parent):
        # --- First Request ---
        self.first_request_frame = tk.Frame(parent)
        self.first_request_frame.pack(fill=tk.X)

        # Max Attempts and Delay
        attempts_delay_frame = tk.Frame(self.first_request_frame)
        attempts_delay_frame.pack(side=tk.TOP, fill=tk.X)

        self.max_attempts_label = ttk.Label(attempts_delay_frame, text="最大尝试次数")
        self.max_attempts_label.pack(side=tk.LEFT, padx=5)
        self.max_attempts_entry = ttk.Entry(attempts_delay_frame, width=10)
        self.max_attempts_entry.pack(side=tk.LEFT, padx=5)
        self.max_attempts_entry.config(validate="key")
        self.max_attempts_entry.config(validatecommand=(self.max_attempts_entry.register(self.ai_draw_validate_positive_int), '%P'))

        self.delay_time_label = ttk.Label(attempts_delay_frame, text="延迟时间 (s)")
        self.delay_time_label.pack(side=tk.LEFT, padx=5)
        self.delay_time_entry = ttk.Entry(attempts_delay_frame, width=10)
        self.delay_time_entry.pack(side=tk.LEFT, padx=5)
        self.delay_time_entry.config(validate="key")
        self.delay_time_entry.config(validatecommand=(self.delay_time_entry.register(self.ai_draw_validate_natural_number), '%P'))

        self.maxconcurrency_label = ttk.Label(attempts_delay_frame, text="最大并发数")
        self.maxconcurrency_label.pack(side=tk.LEFT, padx=5)
        self.maxconcurrency_entry = ttk.Entry(attempts_delay_frame, width=10)
        self.maxconcurrency_entry.pack(side=tk.LEFT, padx=5)
        self.maxconcurrency_entry.config(validate="key")
        self.maxconcurrency_entry.config(validatecommand=(self.maxconcurrency_entry.register(self.ai_draw_validate_positive_int), '%P'))

        self.request_timeout_label = ttk.Label(attempts_delay_frame, text="请求超时时间(s)")
        self.request_timeout_label.pack(side=tk.LEFT, padx=5)
        self.request_timeout_entry = ttk.Entry(attempts_delay_frame, width=10)
        self.request_timeout_entry.pack(side=tk.LEFT, padx=5)
        self.request_timeout_entry.config(validate="key")
        self.request_timeout_entry.config(validatecommand=(self.request_timeout_entry.register(self.ai_draw_validate_positive_int), '%P'))

        # Request URL and Method
        url_method_frame = tk.Frame(self.first_request_frame)
        url_method_frame.pack(side=tk.TOP, fill=tk.X)

        self.request_url_label = ttk.Label(url_method_frame, text="请求URL")
        self.request_url_label.pack(side=tk.LEFT, padx=5)
        self.request_url_entry = ttk.Entry(url_method_frame)
        self.request_url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.request_method_label = ttk.Label(url_method_frame, text="请求方法")
        self.request_method_label.pack(side=tk.LEFT, padx=5)
        self.request_method_var = tk.StringVar(value="POST")  # Default to POST
        self.request_method_combo = ttk.Combobox(url_method_frame, textvariable=self.request_method_var,
                                                 values=["POST", "GET"], state="readonly", width=8)
        self.request_method_combo.pack(side=tk.LEFT, padx=5)
        self.request_method_combo.bind("<<ComboboxSelected>>", lambda event: [self.ai_draw_toggle_request_body(event), self.clear_dropdown_selection(event)])
        self.request_method_combo.bind("<Button-1>", self.clear_dropdown_selection)

        # --- Headers ---
        self.headers_frame = tk.Frame(parent)
        self.headers_frame.pack(fill=tk.X)
        self.headers_label = ttk.Label(self.headers_frame, text="请求头")
        self.headers_label.pack(side=tk.LEFT, padx=5)
        self.add_header_button = ttk.Button(self.headers_frame, text="➕ 新增", command=lambda: self.ai_draw_add_header(self.headers_list))
        self.add_header_button.pack(side=tk.LEFT, padx=5)
        self.headers_list = []  # List to store header entries

        # --- Request Body Placeholder Frame ---
        self.request_body_placeholder_frame = tk.Frame(parent)
        self.request_body_placeholder_frame.pack(fill=tk.X)

        # --- Request Body ---
        self.request_body_frame = tk.Frame(self.request_body_placeholder_frame) # Request body frame is now child of placeholder
        self.request_body_label = ttk.Label(self.request_body_frame, text="请求体")
        self.request_body_label.pack(side=tk.LEFT, padx=5)
        self.request_body_text = tk.Text(self.request_body_frame, height=5)
        self.request_body_text.pack(fill=tk.X, expand=True, padx=5)

        # --- JSON Path & Conditions ---
        self.conditions_frame = tk.Frame(parent)
        self.conditions_frame.pack(fill=tk.X)

        self.json_path_label = ttk.Label(self.conditions_frame, text="JSON路径")
        self.json_path_label.pack(side=tk.LEFT, padx=5)
        self.json_path_entry = ttk.Entry(self.conditions_frame)
        self.json_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.success_condition_label = ttk.Label(self.conditions_frame, text="成功条件")
        self.success_condition_label.pack(side=tk.LEFT, padx=5)
        self.success_condition_entry = ttk.Entry(self.conditions_frame)
        self.success_condition_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.fail_condition_label = ttk.Label(self.conditions_frame, text="失败条件")
        self.fail_condition_label.pack(side=tk.LEFT, padx=5)
        self.fail_condition_entry = ttk.Entry(self.conditions_frame)
        self.fail_condition_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # --- Second Request Switch ---
        self.second_request_var = tk.BooleanVar(value=False)
        self.second_request_switch = ttk.Checkbutton(parent, text="是否二次请求", variable=self.second_request_var,
                                                    command=self.ai_draw_toggle_second_request, bootstyle="round-toggle")
        self.second_request_switch.pack(pady=5)

        # --- Second Request Configuration ---
        self.second_request_frame = tk.Frame(parent)
        #  Pack this frame only when the switch is turned on

        self.ai_draw_create_second_request_widgets()
        self.ai_draw_toggle_request_body()  # Initial toggle
        self.ai_draw_toggle_second_request()
        
    def ai_draw_create_second_request_widgets(self):
        # --- Second Request ---
        second_inner_frame = tk.Frame(self.second_request_frame)
        second_inner_frame.pack(fill=tk.X)

        # Request URL
        self.second_request_url_label = ttk.Label(second_inner_frame, text="请求URL")
        self.second_request_url_label.pack(side=tk.LEFT, padx=5)
        self.second_request_url_entry = ttk.Entry(second_inner_frame)
        self.second_request_url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Request Method
        self.second_request_method_label = ttk.Label(second_inner_frame, text="请求方法")
        self.second_request_method_label.pack(side=tk.LEFT, padx=5)
        self.second_request_method_var = tk.StringVar(value="POST")
        self.second_request_method_combo = ttk.Combobox(second_inner_frame, textvariable=self.second_request_method_var,
                                                        values=["POST", "GET"], state="readonly", width=8)
        self.second_request_method_combo.pack(side=tk.LEFT, padx=5)
        self.second_request_method_combo.bind("<<ComboboxSelected>>",  lambda event: [self.ai_draw_toggle_second_request_body(event), self.clear_dropdown_selection(event)])
        self.second_request_method_combo.bind("<Button-1>", self.clear_dropdown_selection)

        self.second_request_timeout_label = ttk.Label(second_inner_frame, text="请求超时时间(s)")
        self.second_request_timeout_label.pack(side=tk.LEFT, padx=5)
        self.second_request_timeout_entry = ttk.Entry(second_inner_frame, width=10)
        self.second_request_timeout_entry.pack(side=tk.LEFT, padx=5)
        self.second_request_timeout_entry.config(validate="key")
        self.second_request_timeout_entry.config(validatecommand=(self.second_request_timeout_entry.register(self.ai_draw_validate_positive_int), '%P'))

        # --- Headers ---
        self.second_headers_frame = tk.Frame(self.second_request_frame)
        self.second_headers_frame.pack(fill=tk.X)
        self.second_headers_label = ttk.Label(self.second_headers_frame, text="请求头")
        self.second_headers_label.pack(side=tk.LEFT, padx=5)

        self.second_add_header_button = ttk.Button(self.second_headers_frame, text="➕ 新增", command=lambda: self.ai_draw_add_header(self.second_headers_list))
        self.second_add_header_button.pack(side=tk.LEFT, padx=5)
        self.second_headers_list = []

        # --- Request Body Placeholder Frame for Second Request ---
        self.second_request_body_placeholder_frame = tk.Frame(self.second_request_frame)
        self.second_request_body_placeholder_frame.pack(fill=tk.X)

        # --- Request Body ---
        self.second_request_body_frame = tk.Frame(self.second_request_body_placeholder_frame) # Second request body frame is child of its placeholder
        self.second_request_body_label = ttk.Label(self.second_request_body_frame, text="请求体")
        self.second_request_body_label.pack(side=tk.LEFT, padx=5)
        self.second_request_body_text = tk.Text(self.second_request_body_frame, height=5)
        self.second_request_body_text.pack(fill=tk.X, expand=True, padx=5)

        # --- JSON Path & Conditions ---
        self.second_conditions_frame = tk.Frame(self.second_request_frame)
        self.second_conditions_frame.pack(fill=tk.X)

        self.second_json_path_label = ttk.Label(self.second_conditions_frame, text="JSON路径")
        self.second_json_path_label.pack(side=tk.LEFT, padx=5)
        self.second_json_path_entry = ttk.Entry(self.second_conditions_frame)
        self.second_json_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.second_success_condition_label = ttk.Label(self.second_conditions_frame, text="成功条件")
        self.second_success_condition_label.pack(side=tk.LEFT, padx=5)
        self.second_success_condition_entry = ttk.Entry(self.second_conditions_frame)
        self.second_success_condition_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.second_fail_condition_label = ttk.Label(self.second_conditions_frame, text="失败条件")
        self.second_fail_condition_label.pack(side=tk.LEFT, padx=5)
        self.second_fail_condition_entry = ttk.Entry(self.second_conditions_frame)
        self.second_fail_condition_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.ai_draw_toggle_second_request_body()

    def ai_draw_toggle_request_body(self, event=None):
        if self.request_method_var.get() == "POST":
            self.request_body_placeholder_frame.pack(fill=tk.X, before=self.conditions_frame)
            self.request_body_frame.pack(in_=self.request_body_placeholder_frame, fill=tk.X)
        else:
            self.request_body_frame.pack_forget()
            self.request_body_placeholder_frame.pack_forget()
            
    def ai_draw_toggle_second_request_body(self, event=None):
        if self.second_request_method_var.get() == "POST":
            self.second_request_body_placeholder_frame.pack(fill=tk.X, before=self.second_conditions_frame)
            self.second_request_body_frame.pack(in_=self.second_request_body_placeholder_frame, fill=tk.X)
        else:
            self.second_request_body_frame.pack_forget()
            self.second_request_body_placeholder_frame.pack_forget()

    def ai_draw_toggle_second_request(self):
        if self.second_request_var.get():
            self.second_request_frame.pack(fill=tk.X)
        else:
            self.second_request_frame.pack_forget()

    def ai_draw_add_header(self, header_list):
        header_frame = tk.Frame(self.headers_frame if header_list is self.headers_list else self.second_headers_frame)
        header_frame.pack(fill=tk.X)

        delete_button = ttk.Button(header_frame, text="🗑 删除", command=lambda frame=header_frame, hl=header_list: self.ai_draw_delete_header(frame, hl),
                                   bootstyle="danger")
        delete_button.pack(side=tk.LEFT, padx=2, ipadx=8)

        key_entry = ttk.Entry(header_frame)
        key_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        value_entry = ttk.Entry(header_frame)
        value_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        header_list.append((key_entry, value_entry, header_frame))

    def ai_draw_delete_header(self, header_frame, header_list):
        for key_entry, value_entry, frame in header_list:
            if frame == header_frame:
                header_list.remove((key_entry, value_entry, frame))
                frame.destroy()
                break

    def ai_draw_set_default_config_fields(self):
            self.max_attempts_entry.insert(0, "1")
            self.delay_time_entry.insert(0, "5")
            self.maxconcurrency_entry.insert(0, "1")
            self.request_timeout_entry.insert(0, "30")
            self.second_request_timeout_entry.insert(0, "30")

    def ai_draw_add_config(self):
        config_name = simpledialog.askstring("➕ 新增配置", "请输入配置名称:")
        if config_name:
            if config_name in self.configs:
                messagebox.showerror("错误", "配置名称已存在！")
                return
            self.configs.append(config_name)
            self.ai_draw_update_comboboxes()
            self.config_edit_combo.set(config_name)
            self.ai_draw_clear_config_fields()
            self.ai_draw_set_default_config_fields()
            self.ai_draw_create_new_config(config_name)  # Create the config entries in config.ini

    def ai_draw_create_new_config(self, config_name):
        # Sets default values
        for item in [
            'request_method', 'delay_time', 'request_url', 'json_path',
            'success_condition', 'fail_condition', 'second_request_method',
            'second_request_url', 'second_json_path', 'second_success_condition',
            'second_fail_condition', 'second_request','max_attempts','headers','second_headers','request_body','second_request_body','maxconcurrency','request_timeout','second_request_timeout'
        ]:
            self.config.set('AI_draw', f'config_{config_name}_{item}', '')

        self.config.set('AI_draw', f'config_{config_name}_second_request', 'False')

        self.ai_draw_save_config()

    def ai_draw_delete_config(self):
        selected_config = self.config_edit_combo.get()
        if selected_config:
            result = messagebox.askyesno("确认", f"确定要删除配置 '{selected_config}' 吗？")
            if result:
                self.configs.remove(selected_config)
                self.ai_draw_update_comboboxes()
                if self.configs:
                    self.config_edit_combo.set(self.configs[0])
                    self.ai_draw_load_selected_config()
                else:
                    self.config_edit_combo.set("")
                    self.ai_draw_clear_config_fields()

                # Remove config entries from config.ini
                keys_to_remove = [key for key in self.config['AI_draw'] if key.startswith(f'config_{selected_config}_')]
                for key in keys_to_remove:
                    self.config.remove_option('AI_draw', key)
                self.ai_draw_save_config()

    def ai_draw_update_comboboxes(self):
        self.config_edit_combo['values'] = self.configs

    def ai_draw_clear_config_fields(self):
        self.max_attempts_entry.delete(0, tk.END)
        self.request_method_var.set("POST")
        self.delay_time_entry.delete(0, tk.END)
        self.request_url_entry.delete(0, tk.END)
        self.request_body_text.delete('1.0', tk.END)
        self.json_path_entry.delete(0, tk.END)
        self.success_condition_entry.delete(0, tk.END)
        self.fail_condition_entry.delete(0, tk.END)
        self.maxconcurrency_entry.delete(0, tk.END)
        self.request_timeout_entry.delete(0, tk.END)
        for key_entry, value_entry, frame in self.headers_list:
            frame.destroy()
        self.headers_list.clear()

        self.second_request_var.set(False)
        self.second_request_method_var.set("POST")
        self.second_request_url_entry.delete(0, tk.END)
        self.second_request_body_text.delete('1.0', tk.END)
        self.second_json_path_entry.delete(0, tk.END)
        self.second_success_condition_entry.delete(0, tk.END)
        self.second_fail_condition_entry.delete(0, tk.END)
        self.second_request_timeout_entry.delete(0, tk.END)
        for key_entry, value_entry, frame in self.second_headers_list:
            frame.destroy()
        self.second_headers_list.clear()
        self.ai_draw_toggle_second_request()  # Ensure second request area is hidden
        self.ai_draw_toggle_request_body()
        self.ai_draw_toggle_second_request_body()

    def ai_draw_load_config_names(self):
        configs = []
        if "AI_draw" not in self.config:
            return []
        for key in self.config['AI_draw']:
            if key.startswith('config_') and key.endswith('_request_method'): #robust way to find configs
                config_name = key.split('_')[1]
                if config_name not in configs:
                    configs.append(config_name)
        return configs

    def ai_draw_load_selected_config(self, event=None):
        selected_config = self.config_edit_combo.get()
        if not selected_config:
            return
        self.ai_draw_clear_config_fields()

        # Load values from config.ini
        self.max_attempts_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_max_attempts', fallback=''))
        self.request_method_var.set(self.config.get('AI_draw', f'config_{selected_config}_request_method', fallback='POST'))
        self.delay_time_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_delay_time', fallback=''))
        self.request_url_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_request_url', fallback=''))
        self.maxconcurrency_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_maxconcurrency', fallback=''))
        self.request_timeout_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_request_timeout', fallback=''))

        request_body = self.config.get('AI_draw', f'config_{selected_config}_request_body', fallback='')
        self.request_body_text.insert('1.0', request_body)

        self.json_path_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_json_path', fallback=''))
        self.success_condition_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_success_condition', fallback=''))
        self.fail_condition_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_fail_condition', fallback=''))

        # Load headers
        header_str = self.config.get('AI_draw', f'config_{selected_config}_headers', fallback='')
        if header_str:
            try:
                headers = eval(header_str)  # Convert string to list of tuples
                for key, value in headers:
                    self.ai_draw_add_header(self.headers_list)
                    self.headers_list[-1][0].insert(0, key)
                    self.headers_list[-1][1].insert(0, value)
            except (SyntaxError, TypeError):
                messagebox.showerror("Error", f"Invalid header data for config: {selected_config}")

        # Load second request
        self.second_request_var.set(self.config.getboolean('AI_draw', f'config_{selected_config}_second_request', fallback=False))
        self.second_request_method_var.set(self.config.get('AI_draw', f'config_{selected_config}_second_request_method', fallback='POST'))
        self.second_request_url_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_second_request_url', fallback=''))

        second_request_body = self.config.get('AI_draw', f'config_{selected_config}_second_request_body', fallback='')
        self.second_request_body_text.insert('1.0', second_request_body)

        self.second_json_path_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_second_json_path', fallback=''))
        self.second_success_condition_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_second_success_condition', fallback=''))
        self.second_fail_condition_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_second_fail_condition', fallback=''))
        self.second_request_timeout_entry.insert(0, self.config.get('AI_draw', f'config_{selected_config}_second_request_timeout', fallback=''))

        # Load second headers
        second_header_str = self.config.get('AI_draw', f'config_{selected_config}_second_headers', fallback='')
        if second_header_str:
            try:
                second_headers = eval(second_header_str)
                for key, value in second_headers:
                    self.ai_draw_add_header(self.second_headers_list)
                    self.second_headers_list[-1][0].insert(0, key)
                    self.second_headers_list[-1][1].insert(0, value)
            except (SyntaxError, TypeError):
                 messagebox.showerror("Error", f"Invalid second header data for config: {selected_config}")

        self.ai_draw_toggle_second_request()
        self.ai_draw_toggle_request_body()
        self.ai_draw_toggle_second_request_body()


    def ai_draw_save_current_config(self):
        if "AI_draw" not in self.config:
            self.config["AI_draw"] = {}
        selected_config = self.config_edit_combo.get()
        if not selected_config:
            messagebox.showerror("错误", "请选择要保存的配置！")
            return

        self.config.set('AI_draw', 'cloud_on', str(self.cloud_on_var.get()))

        # Save main config
        self.config.set('AI_draw', f'config_{selected_config}_max_attempts', self.max_attempts_entry.get())
        self.config.set('AI_draw', f'config_{selected_config}_request_method', self.request_method_var.get())
        self.config.set('AI_draw', f'config_{selected_config}_delay_time', self.delay_time_entry.get())
        self.config.set('AI_draw', f'config_{selected_config}_request_url', self.request_url_entry.get())
        self.config.set('AI_draw', f'config_{selected_config}_request_body', self.request_body_text.get('1.0', tk.END).strip())
        self.config.set('AI_draw', f'config_{selected_config}_json_path', self.json_path_entry.get())
        self.config.set('AI_draw', f'config_{selected_config}_success_condition', self.success_condition_entry.get())
        self.config.set('AI_draw', f'config_{selected_config}_fail_condition', self.fail_condition_entry.get())
        self.config.set('AI_draw', f'config_{selected_config}_maxconcurrency', self.maxconcurrency_entry.get())
        self.config.set('AI_draw', f'config_{selected_config}_request_timeout', self.request_timeout_entry.get())

        # Save headers
        headers = [(key.get(), value.get()) for key, value, _ in self.headers_list]
        self.config.set('AI_draw', f'config_{selected_config}_headers', str(headers))

        # Save second request config
        self.config.set('AI_draw', f'config_{selected_config}_second_request', str(self.second_request_var.get()))
        self.config.set('AI_draw', f'config_{selected_config}_second_request_method', self.second_request_method_var.get())
        self.config.set('AI_draw', f'config_{selected_config}_second_request_url', self.second_request_url_entry.get())
        self.config.set('AI_draw', f'config_{selected_config}_second_request_body', self.second_request_body_text.get('1.0', tk.END).strip())
        self.config.set('AI_draw', f'config_{selected_config}_second_json_path', self.second_json_path_entry.get())
        self.config.set('AI_draw', f'config_{selected_config}_second_success_condition', self.second_success_condition_entry.get())
        self.config.set('AI_draw', f'config_{selected_config}_second_fail_condition', self.second_fail_condition_entry.get())
        self.config.set('AI_draw', f'config_{selected_config}_second_request_timeout', self.second_request_timeout_entry.get())

        # Save second headers
        second_headers = [(key.get(), value.get()) for key, value, _ in self.second_headers_list]
        self.config.set('AI_draw', f'config_{selected_config}_second_headers', str(second_headers))

        self.ai_draw_save_config()
        self.show_message_bubble("Success", "配置已保存！")

    def ai_draw_save_config(self):
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def ai_draw_load_all_configs(self):
        self.ai_draw_update_comboboxes()
        if self.configs:
            self.config_edit_combo.set(self.configs[0]) # Select first by default
            self.ai_draw_load_selected_config()









    def create_ai_music_config_tab_content(self):
        # --- Frames for better organization ---
        top_frame = ttk.Frame(self.ai_music_config_tab)
        top_frame.pack(side="top", fill="x", padx=5, pady=5)

        middle_frame = ttk.Frame(self.ai_music_config_tab)
        middle_frame.pack(side="top", fill="x", padx=5, pady=5)

        bottom_frame = ttk.Frame(self.ai_music_config_tab)
        bottom_frame.pack(side="bottom", fill="both", expand=True, padx=5, pady=5)

        # AI Music Switch
        self.ai_music_switch_var = tk.BooleanVar()
        self.ai_music_switch_label = tk.Label(top_frame, text="生成背景音乐")
        self.ai_music_switch_label.pack(side="left", padx=5, pady=5)
        self.ai_music_switch = ttk.Checkbutton(top_frame, variable=self.ai_music_switch_var,bootstyle="round-toggle", command=self.save_ai_music_switch)  # Call save function on toggle
        self.ai_music_switch.pack(side="left", padx=5, pady=5)

        self.ai_opening_music_switch_var = tk.BooleanVar()
        self.ai_opening_music_switch_label = tk.Label(top_frame, text="生成片头曲")
        self.ai_opening_music_switch_label.pack(side="left", padx=5, pady=5)
        self.ai_opening_music_switch = ttk.Checkbutton(top_frame, variable=self.ai_opening_music_switch_var,bootstyle="round-toggle", command=self.save_ai_music_switch)  # Call save function on toggle
        self.ai_opening_music_switch.pack(side="left", padx=5, pady=5)

        self.ai_ending_music_switch_var = tk.BooleanVar()
        self.ai_ending_music_switch_label = tk.Label(top_frame, text="生成片尾曲")
        self.ai_ending_music_switch_label.pack(side="left", padx=5, pady=5)
        self.ai_ending_music_switch = ttk.Checkbutton(top_frame, variable=self.ai_ending_music_switch_var,bootstyle="round-toggle", command=self.save_ai_music_switch)  # Call save function on toggle
        self.ai_ending_music_switch.pack(side="left", padx=5, pady=5)


        # Music URL
        self.music_url_label = tk.Label(middle_frame, text="音乐URL")
        self.music_url_label.pack(side="left", padx=5, pady=5)
        self.music_url_entry = tk.Entry(middle_frame, width=50)
        self.music_url_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        # Music Token
        self.music_token_label = tk.Label(middle_frame, text="音乐Token")
        self.music_token_label.pack(side="left", padx=5, pady=5)
        self.music_token_entry = tk.Entry(middle_frame, width=50)
        self.music_token_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        # Save Button (AI Music Config Only)
        self.save_ai_music_button = tk.Button(bottom_frame, text="💾 保存AI音乐配置", command=self.save_ai_music_config)
        self.save_ai_music_button.pack(side="bottom", padx=5, pady=5)

        self.load_ai_music_config()  # Load config when tab is created

    def save_ai_music_switch(self):
           try:
            # Create sections if they don't exist
            if "AI音乐" not in self.config:
                self.config["AI音乐"] = {}

            # Save switch states
            self.config["AI音乐"]["if_on"] = str(self.ai_music_switch_var.get())
            self.config["AI音乐"]["opening_if_on"] = str(self.ai_opening_music_switch_var.get())
            self.config["AI音乐"]["ending_if_on"] = str(self.ai_ending_music_switch_var.get())

            with open(self.config_file, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)

           except Exception as e:
               messagebox.showerror("Error", f"Error saving AI music switch state: {e}")
    def save_ai_music_config(self):
        try:
            # Create section 'AI音乐' if it does not exist
            if "AI音乐" not in self.config:
                self.config["AI音乐"] = {}

            # Save entry values
            self.config["AI音乐"]["base_url"] = self.music_url_entry.get()
            self.config["AI音乐"]["api_key"] = self.music_token_entry.get()

            with open(self.config_file, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)
            self.show_message_bubble("Success", "AI音乐配置保存成功!")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving AI music config: {e}")

    def load_ai_music_config(self):
        try:

            self.config.read(self.config_file, encoding="utf-8")
            # Load switch states
            if "AI音乐" in self.config and "if_on" in self.config["AI音乐"]:
                self.ai_music_switch_var.set(self.config["AI音乐"].getboolean("if_on"))
                self.ai_opening_music_switch_var.set(self.config["AI音乐"].getboolean("opening_if_on"))
                self.ai_ending_music_switch_var.set(self.config["AI音乐"].getboolean("ending_if_on"))

            # Load entry values
            if "AI音乐" in self.config:
                self.music_url_entry.insert(0, self.config["AI音乐"].get("base_url", ""))
                self.music_token_entry.insert(0, self.config["AI音乐"].get("api_key", ""))

        except FileNotFoundError:
            print("Config file not found, creating a new one.")
        except Exception as e:
            messagebox.showerror("Error", f"读取AI音乐配置失败: {e}")













    def create_snapshot_tab_content(self):
        self.generate_snapshot_button = tk.Button(self.snapshot_tab, text="✨ 生成快照文件", command=self.savesnap)
        self.generate_snapshot_button.pack(pady=5)
        # Create a Canvas and Scrollbar
        self.snapshot_canvas = tk.Canvas(self.snapshot_tab, highlightthickness=0)  # Remove highlight
        self.snapshot_scrollbar = ttk.Scrollbar(self.snapshot_tab, orient="vertical", command=self.snapshot_canvas.yview)
        self.snapshot_canvas.configure(yscrollcommand=self.snapshot_scrollbar.set)

        self.snapshot_canvas.pack(side="left", fill="both", expand=True)
        self.snapshot_scrollbar.pack(side="right", fill="y")
        # Create a Frame inside the Canvas to hold the buttons
        self.snapshot_buttons_frame = tk.Frame(self.snapshot_canvas)
        self.snapshot_canvas.create_window((0, 0), window=self.snapshot_buttons_frame, anchor="center") # Use center anchor
        self.snapshot_buttons_frame.bind("<Configure>", self.snapshot_on_frame_configure)
        self.snapshot_canvas.bind("<MouseWheel>", self.snapshot_on_mousewheel)  # Bind mousewheel
    def savesnap(self):
         if not self.story_title_var.get():
            self.show_message_bubble("Error","当前没有选择生成快照的故事")
            return
         threading.Thread(target=self._savesnap).start()
    def _savesnap(self):
        try:
            self.show_message_bubble("Success","正在生成快照")
            gui_functions.savesnap()
        except NameError:
            self.show_message_bubble("Error","快照生成失败")
        self.populate_snapshot_buttons() # Refresh the buttons
    def extract_zip(self, filename,foldername):
        threading.Thread(target=self._extract_zip, args=(filename,foldername,)).start()
    def _extract_zip(self, filename,foldername):
        try:
            gui_functions.extract_zip(filename,foldername)
            self.show_message_bubble("Success","成功恢复快照")
            self.config.read(self.config_file, encoding="utf-8")
            new_story_title = self.config["剧情"].get("story_title", "")
            self.master.after(0, self.update_story_title, new_story_title)
        except NameError:
            self.show_message_bubble("Error","快照恢复失败")
    def populate_snapshot_buttons(self):
        """Populate the snapshot tab with buttons for each zip file in the snap directory."""
        # Clear existing buttons
        for widget in self.snapshot_buttons_frame.winfo_children():
            widget.destroy()

        # Create buttons for each zip file
        snap_dir = "snap"  # Directory containing zip files

        try:
            # Get a list of all zip files in the snap directory with their modification times
            files_with_time = []
            for filename in os.listdir(snap_dir):
                if filename.endswith(".zip"):
                    filepath = os.path.join(snap_dir, filename)
                    modification_time = os.path.getmtime(filepath)  # Get the Unix timestamp representing the last modification time
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

            labels.reverse() #反轉 labels，使其与原始文件列表顺序一致

            # Create buttons for each zip file
            for row_num, ((filename, modification_time), label) in enumerate(zip(files_with_time, labels)):
                # Format the modification time
                datetime_object = datetime.datetime.fromtimestamp(modification_time)
                formatted_time = datetime_object.strftime("%Y-%m-%d %H:%M:%S")

                # Create the label for the modification time
                time_label = tk.Label(self.snapshot_buttons_frame, text=formatted_time)
                time_label.grid(row=row_num, column=0, sticky=tk.W, padx=(0, 5), pady=2)  # Left align

                button = tk.Button(self.snapshot_buttons_frame, text=label, command=lambda f=filename,foldername=name: self.extract_zip(f,foldername))
                button.grid(row=row_num, column=1, sticky=tk.W, pady=2)  # Left align

                delete_button = ttk.Button(self.snapshot_buttons_frame, text="🗑 删除", command=lambda f=filename: self.delete_snapshot(f),
                                   bootstyle="danger")
                delete_button.grid(row=row_num, column=2, sticky=tk.W, padx=5, pady=2)  # Left align

        except FileNotFoundError:
            print("Snap directory not found.")
            os.makedirs(snap_dir)  # Create the directory if it doesn't exist
        except Exception as e:
            messagebox.showerror("Error", f"Error reading snapshot files: {e}")
        self.snapshot_on_frame_configure(None)
        

    def delete_snapshot(self, filename):
        snap_dir = "snap"
        filepath = os.path.join(snap_dir, filename)
        try:
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {filename}?"):
                os.remove(filepath)
                self.populate_snapshot_buttons()  # Refresh the button list
                self.show_message_bubble("Success", f"删除成功")
        except Exception as e:
            messagebox.showerror("Error", f"Error deleting {filename}: {e}")
        self.snapshot_canvas.yview_moveto(0)
    def snapshot_on_frame_configure(self, event):
        self.snapshot_canvas.configure(scrollregion=self.snapshot_canvas.bbox("all"))
        self.snapshot_hide_scrollbar()
    def snapshot_on_mousewheel(self, event):
        self.snapshot_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    def snapshot_hide_scrollbar(self):
        if self.snapshot_buttons_frame.winfo_height() <= self.snapshot_canvas.winfo_height():
            self.snapshot_scrollbar.pack_forget()  # Hide the scrollbar
            self.snapshot_canvas.configure(yscrollcommand=None) #Remove scrollbar functionality
            self.snapshot_canvas.unbind("<MouseWheel>")
        else:
            self.snapshot_scrollbar.pack(side="right", fill="y")
            self.snapshot_canvas.configure(yscrollcommand=self.snapshot_scrollbar.set)
            self.snapshot_canvas.bind("<MouseWheel>", self.snapshot_on_mousewheel) # 重新绑定滚轮
            









    def create_log_tab_content(self):
        self.clear_log_button = tk.Button(self.log_tab, text="🗑 清空日志", command=self.clear_log)
        self.clear_log_button.pack(pady=5)
        clear_log_height = self.clear_log_button.winfo_reqheight()

        self.log_text = tk.Text(self.log_tab, wrap="word", width=140, state=tk.DISABLED)  # Added state=tk.DISABLED
        self.log_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        self.last_log_content = None

        self._create_right_click_menu()  # Create right-click menu
        self.monitor_log()

    def _create_right_click_menu(self):
        """Creates a right-click menu for the log text widget with copy functionality."""
        self.right_click_menu = tk.Menu(self.log_text, tearoff=0)
        self.right_click_menu.add_command(label="📋 复制", command=self._copy_selected_text)
        self.log_text.bind("<Button-3>", self._show_right_click_menu)

    def _copy_selected_text(self):
        """Copies the selected text in the log text widget to the clipboard."""
        try:
            selected_text = self.log_text.selection_get()
            self.master.clipboard_clear()
            self.master.clipboard_append(selected_text)
            self.master.update()
        except tk.TclError:  # No text selected
            pass

    def _show_right_click_menu(self, event):
        """Displays the right-click menu at the location of the click."""
        try:
            self.right_click_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.right_click_menu.grab_release()

    def monitor_log(self):
        """Monitor the log file for changes and update the log text."""

        def update_log():
            try:
                with open("../log.txt", "r", encoding="utf-8") as f:
                    log_content = f.read()

                # Limit log content to 5000 characters
                log_content = log_content[-5000:] if len(log_content) > 5000 else log_content

                if log_content != self.last_log_content:
                    self.log_text.config(state=tk.NORMAL) # Enable temporarily
                    self.log_text.delete("1.0", tk.END)
                    self.log_text.insert("1.0", log_content)
                    self.log_text.see(tk.END)  # Scroll to the end
                    self.log_text.config(state=tk.DISABLED) # Disable again
                    self.last_log_content = log_content  # Update last log content

            except FileNotFoundError:
                self.log_text.config(state=tk.NORMAL) # Enable temporarily
                self.log_text.delete("1.0", tk.END)
                self.log_text.insert("1.0", "Log file not found.")
                self.log_text.config(state=tk.DISABLED) # Disable again
            except Exception as e:
                messagebox.showerror("Error", f"Error reading log file: {e}")

            self.master.after(3000, update_log)  # Check every 3 seconds

        update_log()  # Initial call to start monitoring

    def clear_log(self):
        threading.Thread(target=self._clear_log).start()

    def _clear_log(self):
        try:
            with open("../log.txt", "w", encoding="utf-8") as f:
                f.write("")  # clear the file
            self.log_text.config(state=tk.NORMAL)  # Enable temporarily
            self.log_text.delete("1.0", tk.END)
            self.log_text.config(state=tk.DISABLED)  # Disable again
            self.last_log_content = "" #also reset last log content here.
            self.show_message_bubble("Success", "日志清空成功")
        except Exception as e:
            messagebox.showerror("Error", f"Error clearing log file: {e}")






        



    def create_regenerate_tab_content(self):
        # 重绘人物图
        self.redraw_label = tk.Label(self.regenerate_tab, text="重绘人物图")
        self.redraw_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # 下拉框
        self.character_names = self.load_character_names()
        self.character_var = tk.StringVar(value=self.character_names[0] if self.character_names else "")  # Set default value

        self.character_dropdown = ttk.Combobox(self.regenerate_tab, textvariable=self.character_var, values=self.character_names, state="readonly")
        self.character_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.character_dropdown.bind("<<ComboboxSelected>>", self.clear_dropdown_selection)
        # 生成按钮
        self.generate_character_button = tk.Button(self.regenerate_tab, text="👤 生成", command=self.generate_character)
        self.generate_character_button.grid(row=0, column=2, padx=5, pady=5)

        # 背景音乐生成
        self.music_label = tk.Label(self.regenerate_tab, text="背景音乐生成")
        self.music_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.generate_music_button = tk.Button(self.regenerate_tab, text="🎵 生成背景音乐", command=self.generate_music)
        self.generate_music_button.grid(row=1, column=1, padx=5, pady=5)

        # 故事文本生成
        self.conservation_label = tk.Label(self.regenerate_tab, text="生成故事文本")
        self.conservation_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.generate_conservation_button = tk.Button(self.regenerate_tab, text="📖 生成故事文本", command=self.generate_storytext)
        self.generate_conservation_button.grid(row=2, column=1, padx=5, pady=5)

        # 选项生成
        self.conservation_label = tk.Label(self.regenerate_tab, text="重新生成选项")
        self.conservation_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.generate_conservation_button = tk.Button(self.regenerate_tab, text="☑️ 生成选项文件", command=self.generate_choice)
        self.generate_conservation_button.grid(row=3, column=1, padx=5, pady=5)

        # 选项语音生成
        self.voice_label = tk.Label(self.regenerate_tab, text="人物语音生成")
        self.voice_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.voice_conservation_button = tk.Button(self.regenerate_tab, text="🎤 人物语音生成", command=self.generate_voice)
        self.voice_conservation_button.grid(row=4, column=1, padx=5, pady=5)
    def load_character_names(self):
        
        try:
            title=self.story_title_var.get()
            with open(rf"{game_directory}\data\{title}\character.json", "r", encoding='utf-8') as f:
                data=json.load(f)
                names = [item['name'] for item in data]
            return names
        except FileNotFoundError:
            return []
        except Exception as e:
            messagebox.showerror("Error", f"Error loading character names: {e}")
            return []
    def generate_character(self):
        character_name = self.character_var.get()
        threading.Thread(target=self._generate_character, args=(character_name,)).start()
    def _generate_character(self, name):
        try:
            self.show_message_bubble("","开始生成角色绘画")
            gui_functions.regeneratecharacter(name)
            self.show_message_bubble("Success","角色绘画生成成功")
        except AttributeError:
            self.show_message_bubble("Error","绘画生成失败")
        except Exception as e:
            messagebox.showerror("Error", f"Error calling regeneratecharacter: {e}")
    def generate_music(self):
        threading.Thread(target=self._generate_music).start()
    def _generate_music(self):
        try:
            self.show_message_bubble("","开始生成音乐")
            gui_functions.generate_music()
            self.show_message_bubble("Success","成功音乐成功")
            print("音乐生成成功")
        except AttributeError:
            self.show_message_bubble("Error","音乐生成失败")
            print("音乐生成失败")
        except Exception as e:
            messagebox.showerror("Error", f"Error calling generate_music: {e}")
    def generate_storytext(self):
        character_name = self.character_var.get()
        threading.Thread(target=self._generate_storytext).start()
    def _generate_storytext(self):
        try:
            gui_functions.generate_storytext()
            self.show_message_bubble("Success","故事文本生成成功")
        except AttributeError:
            self.show_message_bubble("Error","故事文本生成失败")
        except Exception as e:
            messagebox.showerror("Error", f"Error calling generate_storytext: {e}")
 

    def generate_choice(self):
        threading.Thread(target=self._generate_choice).start()
    def _generate_choice(self):
        try:
            gui_functions.generate_choice()
            self.show_message_bubble("Success","成功生成选项")
        except AttributeError:
            self.show_message_bubble("Error","选项生成失败")
        except Exception as e:
            messagebox.showerror("Error", f"Error calling generate_choice: {e}")
    def generate_voice(self):
        threading.Thread(target=self._generate_voice).start()
    def _generate_voice(self):
        try:
            gui_functions.generate_voice()
            self.show_message_bubble("Success","成功生成语音")
        except AttributeError:
            self.show_message_bubble("Error","选项生成失败")
        except Exception as e:
            messagebox.showerror("Error", f"Error calling generate_voice: {e}")

        









# --- Main ---
if __name__ == "__main__":
    log_redirector = LogRedirector('../log.txt')
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
