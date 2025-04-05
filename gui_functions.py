import re
import requests
import json
import os
import urllib3
import time
import zipfile
import subprocess
from datetime import datetime
from getimage import get_single_person_image,generate_debug,get_places_images
from getchoice import getchoice,merge_story
from getvoice import getvoice
from getmusic import generate_background_music
import html
import webbrowser
try:
    import renpy
    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

config_file = os.path.join(game_directory,"config.json")
current_working_directory = os.getcwd()
parent_directory_of_cwd = os.path.dirname(current_working_directory)
aigal_exe_path = os.path.join(parent_directory_of_cwd, "AIGALGAME.exe")
aigal_log_path = os.path.join(parent_directory_of_cwd, "log.txt")

def load_config():
    """Loads the configuration from the config.json file."""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print("Config file not found, creating a new one.")
        return {}  # Or return a default config if necessary
    except json.JSONDecodeError:
        print("Error decoding config.json. Returning empty config.")
        return {}  # Or return a default config if necessary

def zip_files_and_folders(output_zip_file, items_to_zip):
    """
    将多个文件和文件夹压缩到一个 ZIP 文件中。

    :param output_zip_file: 输出的 ZIP 文件路径
    :param items_to_zip: 需要压缩的文件或文件夹列表
    """
    with zipfile.ZipFile(output_zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in items_to_zip:
            if os.path.isfile(item):
                # 如果是文件，直接写入 ZIP 文件中
                zipf.write(item, arcname=os.path.basename(item))
            elif os.path.isdir(item):
                # 如果是文件夹，递归地写入 ZIP 文件中
                for dirpath, dirnames, filenames in os.walk(item):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        # 将文件路径写入 ZIP 文件时保留目录结构
                        arcname = os.path.relpath(filepath, start=os.path.dirname(item))
                        zipf.write(filepath, arcname=arcname)

def extract_zip(filename,foldername):
    # 拼接完整的压缩文件路径
    if not os.path.exists(f'{game_directory}/data/{foldername}'):
        os.makedirs(f'{game_directory}/data/{foldername}')
    zip_file_path = f'{game_directory}/snap/{filename}'
    extract_to_path = f'{game_directory}/data/{foldername}'

    # 检查文件是否存在
    if not os.path.exists(zip_file_path):
        print(f"错误：文件 {zip_file_path} 不存在。")
        return

    # 尝试解压
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # 解压文件到目标目录
            zip_ref.extractall(extract_to_path)
            print(f"恢复{filename[:-4]}快照成功")
    except zipfile.BadZipFile:
        print(f"错误：文件 {zip_file_path} 不是有效的 ZIP 文件。")
    except PermissionError:
        print(f"错误：没有权限解压到 {extract_to_path}，请以管理员身份运行。")
    except Exception as e:
        print(f"解压过程中发生未知错误：{e}")

def delete_all_files_in_dir(directory):
    if not os.path.exists(directory):
        return
    if not os.path.isdir(directory):
        return
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path):  # 如果是文件，则删除
                os.remove(file_path)
        except Exception as e:
            print(f"删除文件 '{file_path}' 时出现错误: {e}")

def savesnap():
    config = load_config()  # Load config here

    filename=config["剧情"]["story_title"]
    items = [
        f'{game_directory}/data/{filename}/outline.json', 
        f'{game_directory}/data/{filename}/character.json',  
        f"{game_directory}/data/{filename}/story",
        f"{game_directory}/data/{filename}/choice.json",
        f"{game_directory}/data/{filename}/images",
        f"{game_directory}/data/{filename}/audio",
        f"{game_directory}/data/{filename}/music"
    ]
    now = datetime.now()
    
    filename=filename.replace("\n","")+"_{"+str(int(datetime.now().timestamp()))+"}"
    os.makedirs(f"{game_directory}/snap", exist_ok=True)
    zip_files_and_folders(f"{game_directory}/snap/{filename}.zip",items)

def regeneratecharacter(character):
    get_single_person_image(character)
def generate_music():
    generate_background_music()
def generate_choice():
    pass
def generate_voice(id):
    getvoice(id)
def generate_storytext():
    config = load_config()  # Load config here
    filename=config["剧情"]["story_title"]
    generate_choice_tree_html()
    webbrowser.open(f'file:///{game_directory}/data/{filename}/tree.html')
def test_ai_draw(model, kind):
    config = load_config()  # Load config here
    os.makedirs(f"{game_directory}/test", exist_ok=True)
    if kind=='character':
        result=generate_debug(config,rf'{game_directory}\test','(masterpiece), 1girl, micro bangs, widow\'s peak, black eyes, jungle, kimono skirt, cashmere, scenery, chibi, one eye closed, open mouth, smile, looking at viewer, sparkle, cute creature','test_character_'+model,model)
    else:
        result=generate_debug(config,rf'{game_directory}\test','Design a hyper-realistic scene, showcasing a weathered wooden house teetering on the edge of a rugged cliff, viewed from a low angle. The house features a small balcony with laundry hanging out to dry, casting sharp shadows under the bright midday sun. Lush greenery envelops the base of the cliff, while the expansive landscape is mostly hidden by dense foliage. Although the day is clear, the scene evokes an eerie and isolated atmosphere, with sharp, high-contrast details amplifying the sense of desolation and solitude','test_background_'+model,model)
    return result
def check_web_port(url):
    """使用requests库检查Web端口是否有响应"""
    try:
        requests.get(url, timeout=0.5)
        return True
    except:
        return False

def start():
    config = load_config()  # Load config here
    sovits_url = "http://localhost:9880/"
    rembg_url = "http://localhost:7000/"
    if check_web_port(sovits_url):
        pass
    else:
        return "语音未开启"
    #if check_web_port(rembg_url):
        #pass
    #else:
        #return "rembg未开启"
    subprocess.run(aigal_exe_path)
    return 1


def generate_background(id):
    if id=="generate":
        get_places_images(1)
    else:
        merge_story(id)


def format_json_to_text(json_data: dict) -> str:
    # ... (Keep the exact same function as in the previous version) ...
    lines = []
    if not isinstance(json_data, dict): return "Error: Invalid JSON data format."
    conversations = json_data.get("conversations")
    if not isinstance(conversations, list): return "Error: 'conversations' key missing/invalid."
    for conv in conversations:
        if not isinstance(conv, dict):
            lines.append("Error: Invalid conversation item.")
            continue
        character = conv.get("character", "")
        text = conv.get("text", "")
        place = conv.get("place", "")
        line_prefix = f"{character}：" if character else "旁白："
        line_suffix = f" [{place}]" if place else ""
        lines.append(f"{line_prefix}{text}{line_suffix}")
    return "\n".join(lines)

# --- Main HTML Generation Function ---
def generate_choice_tree_html() -> bool:
    """Generates HTML tree with View/Export buttons and format selection modals."""
    # ...(Configuration and Path setup - same as before)...
    config_file = os.path.join(game_directory, "config.json")
    choice_filename = "choice.json"
    output_html_filename = "tree.html"
    story_dir_name = "story"
    story_title = None
    choice_file_path = None
    output_html_path = None
    story_files_directory = None

    try:
        # ... (Load config, get story_title, set paths - same as before) ...
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        story_title = config.get("剧情", {}).get('story_title')
        if not story_title: raise ValueError("'story_title' not found in config['剧情']")
        data_story_dir = os.path.join(game_directory, "data", story_title)
        os.makedirs(data_story_dir, exist_ok=True)
        choice_file_path = os.path.join(data_story_dir, choice_filename)
        output_html_path = os.path.join(data_story_dir, output_html_filename)
        story_files_directory = os.path.join(data_story_dir, story_dir_name)
        if not all([choice_file_path, output_html_path, story_files_directory]):
             raise ValueError("Could not determine required file paths.")
    except (FileNotFoundError, json.JSONDecodeError, ValueError, Exception) as e:
        print(f"Error during setup: {e}")
        return False

    try:
        with open(choice_file_path, 'r', encoding='utf-8') as f:
            choice_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
         print(f"Error reading choice file {choice_file_path}: {e}")
         # You might want default data or just fail
         # choice_data = {"0": []}
         return False

    generated_ids_in_path = set()
    hidden_story_content_html = ""

    def generate_child_list_html(parent_id: str) -> str:
        """Builds the HTML <ul> for children, including buttons and hidden data."""
        nonlocal hidden_story_content_html
        if parent_id in generated_ids_in_path:
            return f'<ul class="nested error"><li><span>Cycle detected: {html.escape(parent_id)}</span></li></ul>'
        if parent_id not in choice_data or not isinstance(choice_data[parent_id], list):
            return ""

        generated_ids_in_path.add(parent_id)
        choices = choice_data[parent_id]
        children_html = '<ul class="nested">\n' if choices else ""

        for choice_item in choices:
            if isinstance(choice_item, dict):
                choice_text, next_id = "Unknown Choice", None
                for k, v in choice_item.items():
                    if k.startswith("choice"): choice_text = html.escape(str(v))
                    elif k == "id": next_id = str(v)

                if next_id is not None:
                    node_label = f'{choice_text} <span class="next-id">(ID: {html.escape(next_id)})</span>'
                    view_button_html, export_button_html = "", ""
                    story_file_path = os.path.join(story_files_directory, f"{next_id}.json")
                    file_error_span = ""

                    if os.path.exists(story_file_path):
                        try:
                            with open(story_file_path, 'r', encoding='utf-8') as sf:
                                raw_json_content = sf.read()
                            story_json = json.loads(raw_json_content)
                            formatted_story_text = format_json_to_text(story_json)
                            # Add buttons
                            view_button_html = f' <button class="view-story-btn" data-story-id="{html.escape(next_id)}">View</button>'
                            export_button_html = f' <button class="export-story-btn" data-story-id="{html.escape(next_id)}">Export</button>'
                            # Embed data
                            hidden_story_content_html += f'<pre class="story-text-content" id="story-text-{html.escape(next_id)}">{html.escape(formatted_story_text)}</pre>\n'
                            hidden_story_content_html += f'<script type="application/json" class="story-json-content" id="story-json-{html.escape(next_id)}">{raw_json_content}</script>\n'
                        # ...(Keep previous error handling for corrupt files)...
                        except (json.JSONDecodeError, IOError) as e:
                            print(f"Warning: Corrupt/unreadable story file {story_file_path}: {e}")
                            file_error_span = ' <span class="file-error">(Story File Error)</span>'
                        except Exception as e:
                            print(f"Warning: Unexpected error processing {story_file_path}: {e}")
                            file_error_span = ' <span class="file-error">(Processing Error)</span>'

                    grandchild_list_html = generate_child_list_html(next_id)
                    # **Add data-parent-id and data-represented-id**
                    children_html += f'<li data-parent-id="{html.escape(parent_id)}" data-represented-id="{html.escape(next_id)}">' # Add parent/self IDs
                    children_html += f'<span class="node-label">{node_label}</span>'
                    children_html += view_button_html # Add view button
                    children_html += export_button_html # Add export button
                    children_html += file_error_span # Add error span if needed
                    children_html += grandchild_list_html # Add children recursively
                    children_html += f'</li>\n'
                else:
                    children_html += f'<li class="leaf error"><span>Choice (Missing ID)</span></li>\n'
            else:
                children_html += f'<li class="leaf error"><span>Invalid choice format</span></li>\n'

        if choices: children_html += '</ul>\n'
        generated_ids_in_path.remove(parent_id)
        return children_html

    # Process Root Node ("0") - Add Buttons and Data
    root_id, root_label = "0", "Start (ID: 0)"
    root_view_button_html, root_export_button_html = "", ""
    root_story_file_path = os.path.join(story_files_directory, f"{root_id}.json")
    root_file_error_span = ""
    if os.path.exists(root_story_file_path):
        try:
            with open(root_story_file_path, 'r', encoding='utf-8') as sf:
                raw_json_content = sf.read()
            story_json = json.loads(raw_json_content)
            formatted_story_text = format_json_to_text(story_json)
            root_view_button_html = f' <button class="view-story-btn" data-story-id="0">View</button>'
            root_export_button_html = f' <button class="export-story-btn" data-story-id="0">Export</button>'
            hidden_story_content_html += f'<pre class="story-text-content" id="story-text-0">{html.escape(formatted_story_text)}</pre>\n'
            hidden_story_content_html += f'<script type="application/json" class="story-json-content" id="story-json-0">{raw_json_content}</script>\n'
        # ...(Keep previous error handling for corrupt file)...
        except (json.JSONDecodeError, IOError) as e:
             print(f"Warning: Corrupt/unreadable story file {root_story_file_path}: {e}")
             root_file_error_span = ' <span class="file-error">(Story File Error)</span>'
        except Exception as e:
             print(f"Warning: Unexpected error processing {root_story_file_path}: {e}")
             root_file_error_span = ' <span class="file-error">(Processing Error)</span>'

    root_children_html = generate_child_list_html(root_id)
    # **Add data-represented-id to root li**
    tree_html_content = f"""
    <ul class="tree">
        <li data-represented-id="0">
            <span class="node-label">{root_label}</span>{root_view_button_html}{root_export_button_html}{root_file_error_span}
            {root_children_html}
        </li>
    </ul>"""

    # --- HTML Template (Includes TWO Modals) ---
    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Choice Tree: {html.escape(story_title)}</title>
    <style>
        /* ...(Keep ALL previous CSS for tree, view modal, etc.)... */
        body {{ font-family: sans-serif; margin: 20px; line-height: 1.4; color: #333; }}
        ul.tree, ul.nested {{ list-style-type: none; padding-left: 25px; }}
        ul.nested {{ display: none; border-left: 1px dashed #ccc; margin-left: 5px; }}
        ul.nested.active {{ display: block; }}
        .tree li {{ margin: 4px 0; position: relative; }}
        .tree li::before {{ content: ""; position: absolute; top: 0; left: -15px; border-left: 1px solid #ccc; border-bottom: 1px solid #ccc; width: 10px; height: 0.7em; }}
        ul.tree > li::before {{ display: none; }}
        .tree li:last-child::before {{ height: 0.7em; }}
        .tree span.node-label {{ cursor: pointer; padding: 3px 8px; border-radius: 4px; display: inline-block; background-color: #e9f5ff; border: 1px solid #b3d7ff; transition: background-color 0.2s, border-color 0.2s; position: relative; z-index: 1; margin-right: 5px; }}
        .tree span.node-label:hover {{ background-color: #d0eaff; border-color: #99caff; }}
        .tree span.node-label.has-children::before {{ content: "\\25B6"; color: #333; display: inline-block; margin-right: 8px; font-size: 0.8em; transition: transform 0.2s ease-in-out; }}
        .tree span.node-label.expanded::before {{ transform: rotate(90deg); }}
        .tree .error span {{ color: #c00; font-weight: bold; background-color: #fee; border: 1px solid #fcc; padding: 2px 4px; }}
        .tree .file-error {{ font-size: 0.8em; color: #e67e22; font-style: italic; margin-left: 5px;}}
        .tree .next-id {{ font-size: 0.9em; color: #0056b3; margin-left: 5px; font-weight: bold; }}
        .tree span.node-label.leaf-node {{ background-color: #f8f9fa; border-color: #dee2e6; cursor: default; }}
        .view-story-btn, .export-story-btn {{ margin-left: 8px; padding: 2px 6px; font-size: 0.8em; cursor: pointer; color: white; border: none; border-radius: 3px; vertical-align: middle; }}
        .view-story-btn {{ background-color: #28a745; }}
        .view-story-btn:hover {{ background-color: #218838; }}
        .export-story-btn {{ background-color: #ffc107; color: #333;}} /* Yellow */
        .export-story-btn:hover {{ background-color: #e0a800; }}

        /* View Modal Styles (same as before) */
        .modal-overlay {{ display: none; position: fixed; z-index: 100; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.5); justify-content: center; align-items: center; }}
        .modal-overlay.active {{ display: flex; }}
        .modal-content {{ background-color: #fefefe; margin: auto; padding: 0; border: 1px solid #888; width: 80%; max-width: 750px; max-height: 85vh; border-radius: 5px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); display: flex; flex-direction: column; }}
        .modal-header {{ padding: 15px 20px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }}
        .modal-header h2 {{ margin: 0; font-size: 1.2em; }}
        .modal-controls {{ display: flex; gap: 5px; }}
        .format-toggle-btn {{ padding: 5px 10px; font-size: 0.9em; border: 1px solid #ccc; background-color: #f0f0f0; border-radius: 3px; cursor: pointer; }}
        .format-toggle-btn.active {{ background-color: #007bff; color: white; border-color: #007bff; }}
        .format-toggle-btn:not(.active):hover {{ background-color: #e0e0e0; }}
        .modal-close-btn {{ color: #aaa; font-size: 28px; font-weight: bold; cursor: pointer; background: none; border: none; padding: 0 5px; line-height: 1; }}
        .modal-close-btn:hover, .modal-close-btn:focus {{ color: black; text-decoration: none; }}
        .modal-body {{ padding: 15px 20px; overflow-y: auto; flex-grow: 1; }}
        .modal-body pre {{ white-space: pre-wrap; word-wrap: break-word; margin: 0; font-size: 0.9em; background-color: #f8f8f8; padding: 15px; border: 1px solid #eee; border-radius: 3px; }}

        /* Export Format Modal Styles */
        #exportModal .modal-content {{ /* Use ID for specificity */
            max-width: 350px; /* Smaller modal */
            max-height: auto;
            padding: 20px;
            text-align: center;
        }}
        #exportModal .modal-body {{
             padding: 20px 0 10px 0;
             overflow-y: visible; /* No scroll needed */
        }}
        #exportModal h3 {{ margin-top: 0; margin-bottom: 20px; font-size: 1.1em; }}
        #exportModal .export-format-btn {{
            padding: 8px 15px;
            font-size: 1em;
            margin: 0 10px;
            cursor: pointer;
            border-radius: 4px;
            border: 1px solid;
        }}
        #exportJsonBtn {{ background-color: #007bff; color: white; border-color: #007bff; }}
        #exportJsonBtn:hover {{ background-color: #0056b3; }}
        #exportTxtBtn {{ background-color: #6c757d; color: white; border-color: #6c757d; }}
        #exportTxtBtn:hover {{ background-color: #5a6268; }}
    </style>
</head>
<body>
    <h1>Choice Tree: {html.escape(story_title)}</h1>
    <p>Click choices to expand. Click 'View' or 'Export'.</p>
    {tree_html_content}

    <!-- Hidden container for story data -->
    <div id="hidden-story-data" style="display: none;">
        {hidden_story_content_html}
    </div>

    <!-- View Modal (same as before) -->
    <div id="storyModal" class="modal-overlay">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Story Content (ID: <span id="modal-story-id"></span>)</h2>
                <div class="modal-controls">
                    <button data-format="json" class="format-toggle-btn">json</button>
                    <button data-format="text" class="format-toggle-btn active">text</button>
                </div>
                <button class="modal-close-btn" aria-label="Close view modal">&times;</button>
            </div>
            <div class="modal-body">
                <pre id="modal-story-text"></pre>
            </div>
        </div>
    </div>

    <!-- Export Format Selection Modal -->
    <div id="exportModal" class="modal-overlay">
        <div class="modal-content">
             <button class="modal-close-btn" aria-label="Close export modal">&times;</button>
             <h3>Select Export Format</h3>
             <div class="modal-body">
                 <button id="exportJsonBtn" class="export-format-btn">JSON</button>
                 <button id="exportTxtBtn" class="export-format-btn">TXT</button>
             </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', (event) => {{
            const viewModal = document.getElementById('storyModal');
            const viewModalCloseBtn = viewModal.querySelector('.modal-close-btn');
            const viewModalStoryTextPre = viewModal.querySelector('#modal-story-text');
            const viewModalStoryIdSpan = viewModal.querySelector('#modal-story-id');
            const viewModalFormatButtons = viewModal.querySelectorAll('.format-toggle-btn');

            const exportModal = document.getElementById('exportModal');
            const exportModalCloseBtn = exportModal.querySelector('.modal-close-btn');
            const exportJsonBtn = document.getElementById('exportJsonBtn');
            const exportTxtBtn = document.getElementById('exportTxtBtn');

            let currentViewData = {{ text: '', json: '' }};
            let currentViewFormat = 'text';
            let targetExportId = null; // Store the ID for export

            // --- Helper: Format JSON Conversations to Text (JS Version) ---
            function formatConversationsToTextJS(conversations) {{
                if (!Array.isArray(conversations)) return "Error: Invalid conversations data.";
                return conversations.map(conv => {{
                    if (typeof conv !== 'object' || conv === null) return "Error: Invalid item.";
                    const character = conv.character || "";
                    const text = conv.text || "";
                    const place = conv.place || "";
                    const prefix = character ? `${{character}}：` : "旁白：";
                    const suffix = place ? ` [${{place}}]` : "";
                    return `${{prefix}}${{text}}${{suffix}}`;
                }}).join('\\n');
            }}

            // --- Helper: Trace ID Chain Client-Side ---
            function traceChainClientSide(targetId) {{
                const chain = [targetId];
                let currentId = targetId;
                let sanityCheck = 0; // Prevent infinite loops
                const maxDepth = 100;

                while (currentId !== "0" && sanityCheck < maxDepth) {{
                    // Find the LI element representing the current ID
                    const currentLi = document.querySelector(`li[data-represented-id="${{currentId}}"]`);
                    if (!currentLi) {{
                        console.error(`Could not find LI for ID: ${{currentId}}`);
                        return null; // Indicate failure
                    }}
                    const parentId = currentLi.dataset.parentId;
                    if (parentId === undefined || parentId === null) {{ // Should only happen for root=0 or error
                        if (currentId !== "0") console.error(`Missing parent ID for: ${{currentId}}`);
                        break;
                    }}
                     if (chain.includes(parentId)) {{ // Cycle detection
                         console.error(`Cycle detected at ID: ${{parentId}}`);
                         return null;
                     }}
                    chain.unshift(parentId); // Add parent to the beginning
                    currentId = parentId;
                    sanityCheck++;
                }}
                 if (sanityCheck >= maxDepth) {{
                     console.error("Exceeded max trace depth, likely an issue.");
                     return null;
                 }}
                return chain; // Returns chain ordered from root to target
            }}

            // --- Helper: Trigger File Download ---
            function triggerDownload(filename, content, mimeType) {{
                const blob = new Blob([content], {{ type: mimeType }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a); // Required for Firefox
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url); // Clean up
            }}

            // --- Main Event Listener (Delegated) ---
            document.body.addEventListener('click', function(e) {{
                const target = e.target;

                // Handle node label clicks (expand/collapse)
                if (target.classList.contains('node-label')) {{
                    const span = target;
                    const parentLi = span.closest('li');
                    const nestedList = parentLi?.querySelector(':scope > ul.nested');
                    if (nestedList) {{
                        nestedList.classList.toggle('active');
                        span.classList.toggle('expanded');
                    }}
                }}
                // Handle "View" button clicks
                else if (target.classList.contains('view-story-btn')) {{
                    const storyId = target.dataset.storyId;
                    const storyTextEl = document.getElementById('story-text-' + storyId);
                    const storyJsonEl = document.getElementById('story-json-' + storyId);

                    if (storyTextEl && storyJsonEl) {{
                        currentViewData.text = storyTextEl.textContent;
                        currentViewData.json = storyJsonEl.textContent;
                        viewModalStoryIdSpan.textContent = storyId;
                        displayViewContent('text'); // Display text format by default
                        viewModal.classList.add('active');
                    }} else {{
                        alert('Error: Story content element not found for ID ' + storyId);
                    }}
                }}
                // Handle View Modal Format Toggle
                else if (target.classList.contains('format-toggle-btn')) {{
                    displayViewContent(target.dataset.format);
                }}
                // Handle View Modal Close Button
                else if (target === viewModalCloseBtn) {{
                    viewModal.classList.remove('active');
                }}
                // Handle View Modal Overlay Click
                else if (target === viewModal) {{
                    viewModal.classList.remove('active');
                }}
                // Handle "Export" button clicks
                else if (target.classList.contains('export-story-btn')) {{
                    targetExportId = target.dataset.storyId; // Store the ID
                    exportModal.classList.add('active'); // Show format selection
                }}
                // Handle Export Modal Format Selection (JSON)
                else if (target === exportJsonBtn) {{
                    processAndDownloadExport('json');
                    exportModal.classList.remove('active');
                }}
                 // Handle Export Modal Format Selection (TXT)
                 else if (target === exportTxtBtn) {{
                    processAndDownloadExport('txt');
                    exportModal.classList.remove('active');
                }}
                // Handle Export Modal Close Button
                else if (target === exportModalCloseBtn) {{
                    exportModal.classList.remove('active');
                }}
                 // Handle Export Modal Overlay Click
                 else if (target === exportModal) {{
                     exportModal.classList.remove('active');
                 }}
            }});

            // --- Function to display view content ---
            function displayViewContent(format) {{
                currentViewFormat = format;
                let displayText = "";
                if (format === 'text') {{
                    displayText = currentViewData.text;
                }} else if (format === 'json') {{
                    try {{
                        const jsonObj = JSON.parse(currentViewData.json);
                        displayText = JSON.stringify(jsonObj, null, 2);
                    }} catch (e) {{
                        displayText = "Error: Invalid JSON.\\n\\n" + currentViewData.json;
                    }}
                }}
                viewModalStoryTextPre.textContent = displayText;
                viewModalFormatButtons.forEach(btn => {{
                    btn.classList.toggle('active', btn.dataset.format === format);
                }});
            }}

            // --- Function to Process and Download Export ---
            function processAndDownloadExport(format) {{
                if (!targetExportId) return; // Should not happen

                const idChain = traceChainClientSide(targetExportId);
                if (!idChain) {{
                    alert("Error: Could not trace the story chain for export.");
                    return;
                }}

                let allConversations = [];
                let success = true;

                for (const id of idChain) {{
                    const storyJsonEl = document.getElementById('story-json-' + id);
                    if (!storyJsonEl) {{
                        alert(`Error: Missing story data for required ID: ${{id}} in the chain.`);
                        success = false;
                        break;
                    }}
                    try {{
                        const storyJson = JSON.parse(storyJsonEl.textContent);
                        if (storyJson.conversations && Array.isArray(storyJson.conversations)) {{
                            allConversations = allConversations.concat(storyJson.conversations);
                        }}
                    }} catch (e) {{
                        alert(`Error: Invalid JSON data for ID: ${{id}}.\\n${{e}}`);
                        success = false;
                        break;
                    }}
                }}

                if (!success) return; // Stop if any data was missing/invalid

                let fileContent = "";
                let mimeType = "";
                const filename = `story_export_${{targetExportId}}.${{format}}`;

                if (format === 'txt') {{
                    fileContent = formatConversationsToTextJS(allConversations);
                    mimeType = "text/plain;charset=utf-8";
                }} else if (format === 'json') {{
                    // Create new list of conversations excluding the 'id' key
                    const conversationsWithoutId = allConversations.map(conv => {{
                        // Create a copy, then delete 'id'
                        const newConv = {{ ...conv }}; // Shallow copy is fine here
                        delete newConv.id;
                        return newConv;
                    }});
                    const exportJsonObj = {{ conversations: conversationsWithoutId }};
                    fileContent = JSON.stringify(exportJsonObj, null, 2); // Pretty print
                    mimeType = "application/json;charset=utf-8";
                }}

                triggerDownload(filename, fileContent, mimeType);
                targetExportId = null; // Reset after export
            }}

            // --- Initial setup for node styles (leaf/has-children) ---
            document.querySelectorAll('.tree span.node-label').forEach(span => {{
                 const parentLi = span.closest('li');
                 const nestedList = parentLi?.querySelector(':scope > ul.nested');
                 span.classList.toggle('has-children', !!nestedList);
                 span.classList.toggle('leaf-node', !nestedList);
            }});

            // Auto-expand first level
            const rootLabel = document.querySelector('ul.tree > li > span.node-label');
            const rootNestedList = rootLabel?.closest('li')?.querySelector(':scope > ul.nested');
            if (rootNestedList && rootLabel?.classList.contains('has-children')) {{
               rootNestedList.classList.add('active');
               rootLabel.classList.add('expanded');
            }}
        }});
    </script>
</body>
</html>"""

    # --- Write HTML File ---
    try:
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"Successfully generated choice tree HTML with Export: {output_html_path}")
        return True
    except Exception as e:
        print(f"Error writing HTML file {output_html_path}: {e}")
        return False
