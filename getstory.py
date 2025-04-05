import json
import os
from GPT import gpt, gpt_destroy
import random
from handle_prompt import process_prompt
from getchoice import get_choice_id,merge_story
try:
    import renpy

    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

config_file = os.path.join(game_directory,"config.json")

def load_config():
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except:
        return None

def generatejson(prompt1, prompt2, story_title, id, story_id):
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
                                       os.path.join(game_directory,"data",story_title,"story",f"{story_id}.json"))
            if result == "success":
                gpt_destroy(id)
                return "成功生成对话"
            failures.append("无效的JSON数据")
        except Exception as e:
            failures.append(f"异常：{str(e)}")

def process_json_data(json_str, filepath):
    try:
        # 提取有效的JSON对象
        new_objects = extract_valid_objects(json_str)
        if not new_objects:
            print("No valid JSON objects found.")
            return "error"

        # 更新对话ID，每次都从 1 开始
        for i, obj in enumerate(new_objects, 1):  # enumerate 起始索引设为 1
            obj["id"] = i

        # 保存数据，覆盖现有文件
        os.makedirs(os.path.dirname(filepath), exist_ok=True)  # 确保目录存在

        previous_place = None
        for conv in new_objects:
            current = conv["place"]
            if current == previous_place:
                conv["place"] = ""
            elif current!="":
                previous_place = current
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"conversations": new_objects}, f, ensure_ascii=False, indent=4)  # 直接覆盖

        print(f"Successfully saved conversations to: {filepath}")
        return "success"

    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        return "error"
    except Exception as e:
        print(f"Exception: {e}")
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



def begin_story():
    config_data = load_config() # Load config here
    story_title = config_data["剧情"].get("story_title", "") # Get from JSON
    os.makedirs(os.path.join(game_directory,"data",story_title,"story"), exist_ok=True)
    prompt1,prompt2=process_prompt('故事开头')
    id = random.randint(1, 100000)
    result = generatejson(prompt1, prompt2, story_title, id,"0")
    print(result)

def continue_story(answer,story_id):
    config_data = load_config() # Load config here
    story_title = config_data["剧情"].get("story_title", "") # Get from JSON
    with open(os.path.join(game_directory,"data",story_title,"answer.txt"), 'w', encoding='utf-8') as outfile:
        outfile.write(answer)
    prompt1,prompt2=process_prompt('故事继续')
    id = random.randint(1, 100000)
    result = generatejson(prompt1, prompt2, story_title, id,story_id)
    os.remove(os.path.join(game_directory,"data",story_title,"answer.txt"))
    print(result)

def end_story(story_id):
    print("开始end_story")
    config_data = load_config() # Load config here
    story_title = config_data["剧情"].get("story_title", "") # Get from JSON
    prompt1,prompt2=process_prompt('故事结尾')
    failures = []
    id = random.randint(1, 100000)
    result = generatejson(prompt1, prompt2, story_title, id,story_id)
            

if __name__ == "__main__":
    #continue_story("继续剧情")
    #begin_story()
    #convert_story_into_text('end')
    #end_story()
    print("1")
