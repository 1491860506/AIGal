import json
import os
import re
import configparser

# 初始变量（保持原样）
try:
    import renpy
    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()



def process_prompt(kind):
    config = configparser.ConfigParser()
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    lang = config.get("剧情", "language", fallback='中文')
    story_title = config["剧情"].get("story_title", "")
    data_path = os.path.join(game_directory, "data", story_title, "")
    def replace_config_match(match):
        try:
            # 解析四个组
            group1 = match.group(1).strip()
            group2 = match.group(2).strip()
            group3 = match.group(3).strip()
            group4 = match.group(4).strip()

            # 统一处理group4的配置项
            if ',' not in group4:
                config_value=""
            else:
                section, key = group4.split(',', 1)
                config_value = config.get(section, key)

            if not group1:
                # group1为空时直接返回文本+配置值
                return f"{group3}{config_value}"
            else:
                # 处理条件判断
                if ',' not in group1:
                    raise ValueError("无效的group1格式")
                cond_section, cond_key = group1.split(',', 1)
                cond_value = config.getboolean(cond_section, cond_key)
                
                # 校验条件值
                if not group2.isdigit():
                    raise ValueError("条件值必须是数字")
                condition = int(group2) % 2 == 1
                
                # 返回条件判断结果
                return f"{group3}{config_value}" if cond_value == condition else ''
        except Exception as e:
            print(f"配置替换错误: {str(e)}")
            return ''

    def replace_getfile(match):
        # 保持原有文件读取逻辑
        path = match.group(1).strip()
        full_path = os.path.join(game_directory, path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"文件读取失败: {str(e)}")
            return ''

    try:
        with open(os.path.join(game_directory, 'prompt.json'), 'r', encoding='utf-8') as f:
            prompt_data = json.load(f)
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
            return ("error", "error")

    def process(text):
        # 修改后的正则表达式匹配五竖线结构
        text = re.sub(r'\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|', replace_config_match, text)
        text = text.replace('{data_path}', data_path)
        return re.sub(r'\{getfile\((.*?)\)\}', replace_getfile, text)

    return (process(p1) if p1.strip() else '', process(p2) if p2.strip() else '')


