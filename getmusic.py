import requests
import json
import os
import urllib3
import random
from handle_prompt import process_prompt
from GPT import gpt,gpt_destroy
urllib3.disable_warnings()
try:
    import renpy
    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

#config = configparser.ConfigParser()
config_file = os.path.join(game_directory,"config.json")

def load_config():
    global config  # Declare it's the global config variable
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)  # Read config as JSON
    except FileNotFoundError:
        print("Config file not found.")
        config={}
    except json.JSONDecodeError:
        print("Error decoding config.json.")
        config={}

def extract_json(text):
    start_index = text.find('{')
    end_index = text.rfind('}')

    if start_index == -1 or end_index == -1 or start_index >= end_index:
        return "error"

    json_string = text[start_index:end_index + 1]

    try:
        json_object = json.loads(json_string)
        return json_object
    except json.JSONDecodeError:
        return "error"

def generate_background_music():
    music_name="background"
    load_config()
    story_title=config["剧情"].get("story_title", "")
    os.makedirs(os.path.join(game_directory,"data",story_title,"music"), exist_ok=True)
    music_url = config["AI音乐"].get("base_url")
    key = config["AI音乐"].get("api_key")
    headers = {
        'Authorization': f'Bearer {key}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    prompt1,prompt2=process_prompt('背景音乐生成')
    id = random.randint(1, 100000)

    while True:
        try:
            json_string = gpt(prompt1, prompt2, 'background_music', id)
            if json_string == "error":
                continue
            elif json_string == "over_times":
                print("生成音乐失败，原因：LLM调用达到最大尝试次数")
                return f"生成音乐失败，原因：LLM调用达到最大尝试次数"

            try:
                data = extract_json(json_string)
                if extract_json=="error":
                    continue
                if isinstance(data, dict) and "title" in data and "prompt" in data:
                    result=data
                else:
                    result="error"
            except json.JSONDecodeError:
                result="error"

            if result == "error":
                continue
            else:
                gpt_destroy(id)
                title=result["title"]
                prompt=result["prompt"]
                break
        except Exception as e:
            print("LLM调用失败，生成音乐失败")

    payload = {
    "action": "generate",
    "model": "chirp-v4",
    "instrumental": True,
    "custom": False,
    "prompt": prompt,
    "title": title
    }
    print("开始生成背景音乐")
    try:
        response = requests.post(music_url, headers=headers, json=payload)
        data=json.loads(response.text)["data"]
        with requests.get(data[0]["audio_url"], stream=True) as r:
            with open(os.path.join(game_directory,"data",story_title,"music",f"{music_name}.mp3"), 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        with requests.get(data[1]["audio_url"], stream=True) as r:
            with open(os.path.join(game_directory,"data",story_title,"music",f"{music_name}1.mp3"), 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        with requests.get(data[0]["video_url"], stream=True) as r:
            with open(os.path.join(game_directory,"data",story_title,"music",f"{music_name}.mp4"), 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        with requests.get(data[1]["video_url"], stream=True) as r:
            with open(os.path.join(game_directory,"data",story_title,"music",f"{music_name}1.mp4"), 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f"音乐{music_name} {music_name}1已下载。")
    except:
        print("音乐生成失败，检查apikey是否有效")
        return "error"

def generate_end_music(story_id):
    music_name=f"end_{story_id}"
    load_config()
    story_title=config["剧情"].get("story_title", "")
    os.makedirs(os.path.join(game_directory,"data",story_title,"music"), exist_ok=True)
    music_url = config["AI音乐"].get("base_url")
    key = config["AI音乐"].get("api_key")
    lang=config["剧情"].get("language")
    headers = {
        'Authorization': f'Bearer {key}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    prompt1,prompt2=process_prompt('结尾音乐生成')
    id = random.randint(1, 100000)

    while True:
        try:
            json_string = gpt(prompt1, prompt2, '音乐', id)
            if json_string == "error":
                continue
            elif json_string == "over_times":
                print("生成音乐失败，原因：LLM调用达到最大尝试次数")
                return f"生成音乐失败，原因：LLM调用达到最大尝试次数"

            try:
                data = extract_json(json_string)
                if extract_json=="error":
                    continue
                if isinstance(data, dict) and "title" in data and "style" in data and "lyrics" in data:
                    result=data
                else:
                    result="error"
            except json.JSONDecodeError:
                result="error"

            if result == "error":
                continue
            else:
                gpt_destroy(id)
                title=result["title"]
                style=result["style"]
                lyrics=result["lyrics"]
                break
        except Exception as e:
            print("LLM调用失败，生成音乐失败")

    payload = {
    "action": "generate",
    "model": "chirp-v4",
    "instrumental": False,
    "custom": True,
    "lyric": lyrics,
    "style": style,
    "title": title
    }
    print("开始生成结尾音乐")
    try:
        response = requests.post(music_url, headers=headers, json=payload)
        print(response.text)
        data=json.loads(response.text)["data"]
        with open(rf"{game_directory}\data\{story_title}\end_{story_id}_music.json", 'w') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        with requests.get(data[0]["audio_url"], stream=True) as r:
            with open(os.path.join(game_directory,"data",story_title,"music",f"{music_name}.mp3"), 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        with requests.get(data[1]["audio_url"], stream=True) as r:
            with open(os.path.join(game_directory,"data",story_title,"music",f"{music_name}1.mp3"), 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        with requests.get(data[0]["video_url"], stream=True) as r:
            with open(os.path.join(game_directory,"data",story_title,"music",f"{music_name}.mp4"), 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        with requests.get(data[1]["video_url"], stream=True) as r:
            with open(os.path.join(game_directory,"data",story_title,"music",f"{music_name}1.mp4"), 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f"音乐{music_name} {music_name}1已下载。")
    except:
        print("音乐生成失败，检查token是否有效")
        return "error"
