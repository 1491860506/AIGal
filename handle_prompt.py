import json
import os
import re

# 初始变量（保持原样）
try:
    import renpy
    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

config_file = os.path.join(game_directory, "config.json")  # Consistent config file path

def process_prompt(kind):
    def load_config():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            print(f"Config file not found: {config_file}")
            return {}
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {config_file}")
            return {}

    config = load_config()  # Load config when needed

    lang = config.get("剧情", {}).get("language", '中文')
    story_title = config.get("剧情", {}).get("story_title", "")
    data_path = os.path.join(game_directory, "data", story_title, "")

    def get_nested_value(data, keys):
        """
        Recursively retrieves a value from a nested dictionary given a list of keys.
        Handles integer keys and string keys differently.
        """
        try:
            for key in keys:
                # Attempt to convert key to integer, but only if it's not a string representation of an integer
                if isinstance(key, str) and key.isdigit():
                    key = int(key)
                data = data[key]
            return data
        except (KeyError, TypeError, IndexError):
            return None

    def replace_config_match(match):
        try:
            group1 = match.group(1).strip()
            group2 = match.group(2).strip()
            group3 = match.group(3).strip()
            group4 = match.group(4).strip()

            # Process group4 to retrieve the config value
            if ',' not in group4:
                config_value = ""
            else:
                keys = [part.strip() for part in group4.split(',')]
                config_value = get_nested_value(config, keys) if keys else ""
                config_value = str(config_value) if config_value is not None else ""  # Convert to string

            if not group1:
                return f"{group3}{config_value}"
            else:
                # Process group1
                group1_keys = [part.strip() for part in group1.split(',')]
                group1_value = get_nested_value(config, group1_keys) if group1_keys else None

                # Process group2
                if group2.isdigit():
                    condition = int(group2) % 2 == 1
                    comparison_value = condition
                    group1_value = bool(group1_value) if group1_value is not None else False

                else:
                    # Group2 is a string or a reference to a config value
                    # If group2 contains a comma, treat it as a config path
                    if ',' in group2:
                        group2_keys = [part.strip() for part in group2.split(',')]
                        group2_value = get_nested_value(config, group2_keys) if group2_keys else None
                        comparison_value = str(group2_value) if group2_value is not None else ""
                    else:
                        if group2[:1]=='!' and str(group2[1:])!=str(group1_value):
                            return f"{group3}{config_value}"
                        comparison_value = group2

                    group1_value = str(group1_value) if group1_value is not None else ""

                if str(group1_value) == str(comparison_value):  # Compare as strings
                    return f"{group3}{config_value}"
                else:
                    return ''
        except Exception as e:
            print(f"配置替换错误: {str(e)}")
            return ''

    def replace_getfile(match):
        try:
            args_str = match.group(1).strip()
            args = [arg.strip() for arg in args_str.split(',')]
            path = args[0]
            full_path = os.path.join(game_directory, path)

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if len(args) == 2:
                try:
                    num_lines = int(args[1])
                    lines = content.splitlines()
                    if num_lines > 0:  # Read first N lines
                        return '\n'.join(lines[:num_lines])
                    else:  # Read last N lines
                        return '\n'.join(lines[num_lines:])
                except ValueError:
                    print(f"Invalid line count: {args[1]}")
                    return ''
            else:
                return content
        except Exception as e:
            print(f"文件读取失败: {str(e)}")
            return ''

    try:
        prompt_file = os.path.join(game_directory, 'config.json')  # Change to config.json
        with open(prompt_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)  # Load all json
            prompt_data = all_data.get("提示词", [])  # Extract "提示词" section
    except Exception as e:
        print(f"JSON读取失败: {str(e)}")
        return ("error", "error")

    # 查找目标kind
    target = next((item for item in prompt_data if item['kind'] == kind), None)
    if not target:
        return ("error", "error")

    # 构建内容字典
    content_dict = {item['id']: item.get('prompt', '') for item in target['content']}

    # 语言映射逻辑保持不变
    lang_map = {'中文': ('1', '2'), '英文': ('3', '4'), '日文': ('5', '6')}
    ids = lang_map.get(lang, ('1', '2'))
    p1, p2 = content_dict.get(ids[0], ''), content_dict.get(ids[1], '')

    # 回退逻辑保持不变
    if not (p1.strip() or p2.strip()):
        p1, p2 = content_dict.get('1', ''), content_dict.get('2', '')
        if not (p1.strip() or p2.strip()):
            print("没有设置提示词")
            return ("error", "error")

    def process(text):
        # 修改后的正则表达式匹配五竖线结构
        text = re.sub(r'\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|', replace_config_match, text)
        text = text.replace('{data_path}', data_path)
        text=text.replace(',}','}').replace(',]',']')
        return re.sub(r'\{getfile\((.*?)\)\}', replace_getfile, text)

    return (process(p1) if p1.strip() else '', process(p2) if p2.strip() else '')

if __name__ == "__main__":
    print(process_prompt('全部人物绘画'))
