import re
import os
import requests
import json
import configparser
import threading
import time
from getoutline import getoutline
from getstory import begin_story,continue_story,end_story
from getchoice import getchoice
from getvoice import getvoice,getendvoice
from getimage import get_all_persons_images,get_places_images,get_end_places_images
from getmusic import generate_background_music,generate_end_music
config = configparser.ConfigParser()
try:
    import renpy

    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()
threads = []
generate_new_chapters_state = False

def main():
    global generate_new_chapters_state
    start_time = time.time()
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    
    getoutline()
    
    thread = threading.Thread(target=get_all_persons_images)
    thread.start()
    threads.append(thread)

    if config.getboolean('AI音乐', 'if_on'):
        thread = threading.Thread(target=generate_background_music)
        thread.start()
    
    begin_story()
    
    thread = threading.Thread(target=getvoice)
    thread.start()


    thread = threading.Thread(target=getchoice)
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
def story_continue(answer):
    global generate_new_chapters_state
    start_time = time.time()
    generate_new_chapters_state = True
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    story_title=config.get('剧情', 'story_title')
    with open(rf"{game_directory}\data\{story_title}\story.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        conversations = data.get("conversations", [])
        last_id = 1 
        for conv in reversed(conversations):
            if 'id' in conv and conv['id'] is not None:
                last_id = conv['id']
                break
    continue_story(answer)
    thread = threading.Thread(target=getchoice)
    thread.start()
    threads.append(thread)
    thread = threading.Thread(target=getvoice, args=(last_id,))
    thread.start()
    get_places_images()
    for thread in threads:
        thread.join()
    end_time = time.time()
    execution_time = round(end_time - start_time,1)
    print(f"继续故事用时{execution_time}秒")
    generate_new_chapters_state = False

def end():
    global generate_new_chapters_state
    start_time = time.time()
    generate_new_chapters_state = True
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    story_title=config.get('剧情', 'story_title')

    if os.path.exists(rf"{game_directory}\data\{story_title}\music\end.mp3"):
        pass

    else:
        if config.getboolean('AI音乐', 'ending_if_on'):
            thread = threading.Thread(target=generate_end_music)
            thread.start()
            threads.append(thread)


    if os.path.exists(rf"{game_directory}\data\{story_title}\end.json"):
        pass

    else:

        end_story()

        thread = threading.Thread(target=get_end_places_images)
        thread.start()
        threads.append(thread)
            
        thread = threading.Thread(target=getendvoice)
        thread.start()


    for thread in threads:
        thread.join()
    end_time = time.time()
    execution_time = round(end_time - start_time,1)
    print(f"生成故事结尾用时{execution_time}秒")
    generate_new_chapters_state = False

