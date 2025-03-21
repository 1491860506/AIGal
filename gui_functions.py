import re
import requests
import configparser
import json
import os
import urllib3
import time
import zipfile
import subprocess
from datetime import datetime
from getimage import get_single_person_image,generate
from getchoice import getchoice
from getvoice import getvoice
from getstory import convert_story_into_text
from getmusic import generate_background_music
try:
    import renpy
    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

config = configparser.ConfigParser()
config.read(rf"{game_directory}/config.ini", encoding='utf-8')
current_working_directory = os.getcwd()
parent_directory_of_cwd = os.path.dirname(current_working_directory)
aigal_exe_path = os.path.join(parent_directory_of_cwd, "AIGAL.exe")
aigal_log_path = os.path.join(parent_directory_of_cwd, "log.txt")



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
    config.read(rf"{game_directory}/config.ini", encoding='utf-8')
    filename=config["剧情"]["story_title"]
    items = [
        f'{game_directory}/data/{filename}/outline.json', 
        f'{game_directory}/data/{filename}/character.json',  
        f"{game_directory}/data/{filename}/story.json",
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
    getchoice()
def generate_voice():
    getvoice()
def generate_storytext():
    convert_story_into_text()
def test_ai_draw(model,kind):
    config.read(rf"{game_directory}/config.ini", encoding='utf-8')
    os.makedirs(f"{game_directory}/test", exist_ok=True)
    if kind=='character':
        result=generate(config,f'{game_directory}/test','1girl of anime style','test_character_'+model,model)
    else:
        result=generate(config,f'{game_directory}/test','1house of anime style','test_background_'+model,model)
    return result
def check_web_port(url):
    """使用requests库检查Web端口是否有响应"""
    try:
        requests.get(url, timeout=0.5)
        return True
    except:
        return False

def start():
    sovits_url = "http://localhost:9880/"
    rembg_url = "http://localhost:7000/"
    if check_web_port(sovits_url):
        pass
    else:
        return "语音未开启"
    if check_web_port(rembg_url):
        pass
    else:
        return "rembg未开启"
    #os.system(aigal_exe_path)
    subprocess.run(aigal_exe_path)
    return 1
