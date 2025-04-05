import json
from GPT import gpt, gpt_destroy
import os
import re
import time
import random
from handle_prompt import process_prompt

try:
    import renpy

    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

config_file =os.path.join(game_directory,"config.json")
def getjson_outline(input_string):
    """
    从字符串中提取 JSON 对象。

    Args:
        input_string: 要从中提取 JSON 对象的字符串。

    Returns:
        提取的 JSON 对象，如果找不到 JSON 对象，则返回 None。
    """
    try:
        start_index = input_string.find('{')
        end_index = input_string.rfind('}')

        if start_index == -1 or end_index == -1 or start_index >= end_index:
            return None  # No valid JSON found

        json_string = input_string[start_index:end_index + 1]
        return json_string
    except Exception as e:  # Catch potential errors during the extraction process
        print(f"An error occurred: {e}")
        return None

def clean_filename(filename):
    """清理文件名，替换或移除Windows不允许的字符."""
    replacements = {
        "\\": "、",
        "/": "、",
        ":": "：",
        "*": "＊",
        "?": "？",
        "\"": "“",
        "<": "＜",
        ">": "＞",
        "|": "｜",
    }
    for char, replacement in replacements.items():
        filename = filename.replace(char, replacement)

    # 删除 replacements 里没有的特殊字符
    filename = re.sub(r'[\\/:*?"<>|]', '', filename)
    return filename

def getoutline():
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Config file not found.")
        return "error"
    except json.JSONDecodeError:
        print("Error decoding config.json.")
        return "error"

    theme = config["剧情"].get("outline_content_entry", "")
    prompt, userinput = process_prompt('大纲')

    # 生成随机id
    id = random.randint(1, 100000)  # 生成一个1到100000之间的随机正整数
    while True:
        try:
            gpt_response = gpt(prompt, userinput, '大纲', id)
            if gpt_response == "error":
                print(f"尝试失败，失败原因：GPT函数返回错误。")
                continue
            elif gpt_response == "over_times":
                print("gpt 调用超出最大重试次数")
                return "error"

            extracted_json = getjson_outline(gpt_response)

            if extracted_json is None:
                print(f"尝试失败，失败原因：未提取到有效的JSON对象。")
                continue

            try:
                json_object = json.loads(extracted_json)
                if not all(key in json_object for key in ("title", "outline", "character")):
                    print(f"尝试失败，失败原因：JSON对象不包含必要的键 (title, outline, character)。")
                    continue
            except json.JSONDecodeError as e:
                print(f"尝试失败，失败原因：JSON解码错误：{e}")
                continue
            try:
                title = json_object["title"]
                cleaned_title = clean_filename(title)
                json_object["title"] = cleaned_title  # 更新json中的title

                data_dir = os.path.join(game_directory, "data")
                os.makedirs(data_dir, exist_ok=True)  # 确保data目录存在
                dir_name = cleaned_title
                dir_path = os.path.join(data_dir, dir_name)

                # 检查目录是否存在，如果存在则添加序号
                if os.path.exists(dir_path):
                    index = 1
                    while True:
                        new_dir_name = f"{cleaned_title}-{index}"
                        new_dir_path = os.path.join(data_dir, new_dir_name)
                        if not os.path.exists(new_dir_path):
                            dir_name = new_dir_name
                            dir_path = new_dir_path
                            break
                        index += 1

                os.makedirs(dir_path, exist_ok=True)

                file_path = os.path.join(dir_path, "character.json")
                with open(file_path, "w", encoding='utf-8') as f:
                    json.dump(json_object['character'], f, ensure_ascii=False, indent=4)

                del json_object['character']

                file_path = os.path.join(dir_path, "outline.json")
                with open(file_path, "w", encoding='utf-8') as f:
                    json.dump(json_object, f, ensure_ascii=False, indent=4)

                try:
                    config["剧情"]["story_title"] = dir_name
                    with open(config_file, "w", encoding="utf-8") as configfile:
                        json.dump(config,configfile,indent=4,ensure_ascii=False)
                    print("获取大纲成功")
                    gpt_destroy(id)
                    return "success"
                except Exception as e:
                    print(f"写入配置文件失败: {e}")
            except Exception as e:
                print(f"尝试失败，失败原因：处理JSON或创建文件夹时发生错误：{e}")
                continue
        except Exception as e:
            print(f"尝试失败，失败原因：发生内部错误：{e}")
            continue

if __name__ == "__main__":
    getoutline()
