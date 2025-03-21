import json
import os
from GPT import gpt, gpt_destroy
import configparser
import random
from handle_prompt import process_prompt

try:
    import renpy

    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

config = configparser.ConfigParser()

def generatejson(prompt1, prompt2, story_title, id):
    failures = []
    while True:
        try:
            json_string = gpt(prompt1, prompt2, 'plot', id)
            if json_string == "error":
                failures.append(f"GPT返回错误")
                continue
            elif json_string == "over_times":
                print("gpt 调用超出最大重试次数")
                return f"达到最大尝试次数，失败原因：{failures}"

            result = process_json_data(json_string,
                                       rf"{game_directory}\data\{story_title}\story.json", story_title)

            if result == "success":
                gpt_destroy(id)
                return "成功生成对话"
            failures.append("无效的JSON数据")
        except Exception as e:
            failures.append(f"异常：{str(e)}")

def process_json_data(json_str, filepath, story_title):
    # 初始化或加载现有数据
    try:
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            with open(filepath, 'r+', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    existing = data.get("conversations", [])
                except:
                    f.seek(0)
                    existing = extract_valid_objects(f.read())
        else:
            existing = []
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
    except:
        return "error"

    # 处理新数据
    new_objects = extract_valid_objects(json_str)
    if not new_objects:
        return "error"

    # 合并数据并处理place
    last_id = existing[-1]["id"] if existing else 0
    for i, obj in enumerate(new_objects, last_id + 1):
        obj["id"] = i
    all_data = existing + new_objects

    previous_place = None
    for conv in all_data:
        current = conv["place"]
        if current == previous_place:
            conv["place"] = ""
        elif current!="":
            previous_place = current

    # 保存主数据
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"conversations": all_data}, f, ensure_ascii=False, indent=4)
    except:
        return "error"

    # 保存地点信息
    if story_title:
        places = list({conv["place"] for conv in all_data if conv["place"]})
        image_dir = rf"{game_directory}\data\{story_title}\images"
        valid_places = [p for p in places if not os.path.exists(f"{image_dir}/{p}.png")]

        try:
            place_path = rf"{game_directory}\data\{story_title}\place.json"
            with open(place_path, 'w', encoding='utf-8') as f:
                json.dump(valid_places, f, ensure_ascii=False, indent=4)
            return "success"
        except:
            return "error"
    return "error"

def extract_valid_objects(json_str):
    objects = []
    start = json_str.find('[') + 1
    brace_level = 0
    buffer = []

    for char in json_str[start:]:
        if char == '{':
            brace_level += 1
            buffer.append(char)
        elif char == '}':
            brace_level -= 1
            buffer.append(char)
            if brace_level == 0:
                try:
                    obj = json.loads(''.join(buffer))
                    if all(key in obj for key in ["place", "character", "text"]):
                        objects.append(obj)
                    buffer = []
                except:
                    break
        elif buffer:
            buffer.append(char)
    return objects

def convert_story_into_text(filename='story'):
    #将故事json转化为txt文本
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    story_title = config.get('剧情', 'story_title')

    json_file_path = os.path.join(game_directory, "data", story_title, f'{filename}.json')
    txt_file_path = os.path.join(game_directory, "data", story_title, f'{filename}.txt')

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        with open(txt_file_path, 'w', encoding='utf-8') as outfile:
            for conversation in data.get('conversations', []):
                place = conversation.get('place', '')
                character = conversation.get('character', '')
                text = conversation.get('text', '')

                char_segment = f"{character}：" if character else "旁白："
                place_segment = f"[{place}]" if place else ""

                line = f"{char_segment}{text}{place_segment}\n"
                outfile.write(line)

    except FileNotFoundError:
        print(f"Error: File not found at {json_file_path}")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON at {json_file_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def begin_story():
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    story_title = config["剧情"].get("story_title", "")
    prompt1,prompt2=process_prompt('故事开头')
    id = random.randint(1, 100000)
    result = generatejson(prompt1, prompt2, story_title, id)
    print(result)
    convert_story_into_text()

def continue_story(answer):
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    story_title = config["剧情"].get("story_title", "")
    with open(rf"{game_directory}\data\{story_title}\story.json", 'r', encoding='utf-8') as f:
        story = json.load(f)
    conversations = story['conversations']
    for conversation in conversations:
        if 'id' in conversation:
            del conversation['id']
    with open(rf"{game_directory}\data\{story_title}\story_noid.json", "w", encoding='utf-8') as f:
        json.dump(story, f, ensure_ascii=False, indent=4)
    with open(rf"{game_directory}\data\{story_title}\answer.txt", 'w', encoding='utf-8') as outfile:
        outfile.write(answer)
    prompt1,prompt2=process_prompt('故事继续')
    os.remove(rf"{game_directory}\data\{story_title}\story_noid.json")
    os.remove(rf"{game_directory}\data\{story_title}\answer.txt")
    id = random.randint(1, 100000)
    result = generatejson(prompt1, prompt2, story_title, id)
    print(result)
    convert_story_into_text()

def end_story():
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    story_title = config["剧情"].get("story_title", "")
    with open(rf"{game_directory}\data\{story_title}\story.json", 'r', encoding='utf-8') as f:
        story = json.load(f)
    conversations = story['conversations']
    for conversation in conversations:
        if 'id' in conversation:
            del conversation['id']
    with open(rf"{game_directory}\data\{story_title}\story_noid.json", "w", encoding='utf-8') as f:
        json.dump(story, f, ensure_ascii=False, indent=4)
    prompt1,prompt2=process_prompt('故事结尾')
    os.remove(rf"{game_directory}\data\{story_title}\story_noid.json")
    failures = []
    id = random.randint(1, 100000)
    while True:
        try:
            json_string = gpt(prompt1, prompt2, 'plot', id)
            if json_string == "error":
                failures.append(f"GPT返回错误")
                continue
            elif json_string == "over_times":
                print("gpt 调用超出最大重试次数")
                return f"达到最大尝试次数，失败原因：{failures}"

            result = process_json_data(json_string,
                                       rf"{game_directory}\data\{story_title}\end.json", story_title)

            if result == "success":
                gpt_destroy(id)
                convert_story_into_text('end')
                return "成功生成end"
            failures.append("无效的JSON数据")
        except Exception as e:
            failures.append(f"异常：{str(e)}")

if __name__ == "__main__":
    #continue_story("继续剧情")
    #begin_story()
    #convert_story_into_text('end')
    end_story()
