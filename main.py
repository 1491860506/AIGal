import os
import json
import threading
import time
from getoutline import getoutline
from getstory import begin_story,continue_story,end_story
from getchoice import getchoice
from getvoice import getvoice
from getimage import get_all_persons_images,get_places_images
from getmusic import generate_background_music,generate_end_music
from getchoice import get_choice_id,merge_story
try:
    import renpy
    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

threads = []
generate_new_chapters_state = False
story_id="0"
config_file = os.path.join(game_directory,"config.json")

def load_config():
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

config = load_config()

def main():
    global generate_new_chapters_state, config
    start_time = time.time()
    try:
        config = load_config() # Load config at the start of the function
        getoutline()

        thread = threading.Thread(target=get_all_persons_images)
        thread.start()
        threads.append(thread)

        if config.get('AI音乐', {}).get('if_on', False):
            thread = threading.Thread(target=generate_background_music)
            thread.start()
        generate_new_chapters_state ='story'
        begin_story()
        
        merge_story("0")
        
        generate_new_chapters_state ='picture'

        
        thread = threading.Thread(target=getvoice,args=("0",))
        thread.start()

        thread = threading.Thread(target=getchoice,args=("0",))
        thread.start()
        threads.append(thread)

        thread = threading.Thread(target=get_places_images)
        thread.start()
        threads.append(thread)

        for thread in threads:
            thread.join()
        end_time = time.time()
        execution_time = round(end_time - start_time,1)
        print(f"故事开篇用时{execution_time}秒")
        generate_new_chapters_state = True
    except Exception as e:
        print(f"发生了一个错误： {type(e).__name__} - {e}")
        generate_new_chapters_state ="error"
def story_continue(answer,story_id):
    global generate_new_chapters_state, config
    generate_new_chapters_state = True
    try:
        story_id=get_choice_id(story_id,answer)
        start_time = time.time()
        config = load_config()
        story_title=config.get('剧情', {}).get('story_title','')
        if os.path.exists(rf"{game_directory}/data/{story_title}/story/{story_id}.json"):
            merge_story(story_id)
            generate_new_chapters_state = False
            return
        merge_story(story_id)
        continue_story(answer,story_id)
        merge_story(story_id)
        thread = threading.Thread(target=getchoice,args=(story_id,))
        thread.start()
        threads.append(thread)
        thread = threading.Thread(target=getvoice, args=(story_id,))
        thread.start()
        get_places_images()
        for thread in threads:
            thread.join()
        end_time = time.time()
        execution_time = round(end_time - start_time,1)
        print(f"继续故事用时{execution_time}秒")
        generate_new_chapters_state = False
    except Exception as e:
        print(f"发生了一个错误： {type(e).__name__} - {e}")
        generate_new_chapters_state ="error"
def end(story_id):
    global generate_new_chapters_state, config
    start_time = time.time()
    generate_new_chapters_state = True
    try:
        config = load_config()
        story_title=config.get('剧情',{}).get('story_title','')
        story_id=get_choice_id(story_id,"结束游戏")
        if os.path.exists(rf"{game_directory}/data/{story_title}/story/{story_id}.json"):
            generate_new_chapters_state = False
            return



        if config.get('AI音乐', {}).get('ending_if_on',False):
            thread = threading.Thread(target=generate_end_music,args=(story_id,))
            thread.start()
            threads.append(thread)

        merge_story(story_id)
        end_story(story_id)
        merge_story(story_id)
        thread = threading.Thread(target=get_places_images)
        thread.start()
        threads.append(thread)

        thread = threading.Thread(target=getvoice, args=(story_id,))
        thread.start()

        for thread in threads:
            thread.join()
        end_time = time.time()
        execution_time = round(end_time - start_time,1)
        print(f"生成故事结尾用时{execution_time}秒")
        generate_new_chapters_state = False
    except Exception as e:
        print(f"发生了一个错误： {type(e).__name__} - {e}")
        generate_new_chapters_state ="error"
        
def localstory():
    global generate_new_chapters_state, config
    try:
        config = load_config()
        story_title=config.get('剧情',{}).get('story_title','')
        with open(rf"{game_directory}/data/{story_title}/story/0.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        conversations=data['conversations']
        previous_place = None
        for conv in conversations:
            current = conv["place"]
            if current == previous_place:
                conv["place"] = ""
            elif current!="":
                previous_place = current
        for index, item in enumerate(conversations):
            item["id"] = index+1
        try:
            with open(rf"{game_directory}/data/{story_title}/story/0.json", 'w', encoding='utf-8') as f:
                json.dump({"conversations": conversations}, f, ensure_ascii=False, indent=4)
        except:
            return "error"
        merge_story("0")


        thread = threading.Thread(target=getvoice,args=("0",))
        thread.start()

        thread = threading.Thread(target=getchoice,args=("0",))
        thread.start()
        threads.append(thread)
        

        thread = threading.Thread(target=get_all_persons_images)
        thread.start()
        threads.append(thread)

        thread = threading.Thread(target=get_places_images)
        thread.start()
        threads.append(thread)

        for thread in threads:
            thread.join()
        os.remove(rf"{game_directory}/data/{story_title}/zw")
        generate_new_chapters_state = True
    except Exception as e:
        print(f"发生了一个错误： {type(e).__name__} - {e}")
        generate_new_chapters_state ="error"
