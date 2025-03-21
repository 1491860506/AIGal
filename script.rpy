init python:
    import json
    import os
    import string
    import threading
    from main import main,story_continue,end,generate_new_chapters_state
    import configparser

    def list_change(*args):
        original_list = list(args)
        choices = [*args,'继续推进剧情','user_input']
        original_list.append("继续推进剧情")
        original_list.append("让我自己输入")
        choices.append('user_input')
        transformed_list = [[item, choice] for item, choice in zip(original_list, choices)]
        return transformed_list
    def create_thread(arg):
        thread = threading.Thread(target=story_continue, args=(arg,), daemon=True)
        thread.start()
        return thread
    def end_thread():
        thread = threading.Thread(target=end, daemon=True)
        thread.start()
        return thread
    def load_dialogues(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data["conversations"]
    def load_choice(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    def read(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            data = f.read()
        return data
    def getconfig(a,b):
        config = configparser.ConfigParser()
        config.read(rf"{game_directory}/config.ini", encoding='utf-8')
        return config.get(a, b)
    def get_next_dialogue():
        global current_dialogue_index
        if current_dialogue_index < len(dialogues):
            dialogue = dialogues[current_dialogue_index]
            current_dialogue_index += 1
            return dialogue
        else:
            return None
    current_dialogue_index = 0
    dialogues = []
    characters = {}
    game_directory = (renpy.config.gamedir).replace("\\","/")
    title=getconfig("剧情","story_title")
image loading movie = Movie(play="loading.webm")
define small_center = Transform(xalign=0.5, yalign=1.0, xpos=0.5, ypos=1.0, xzoom=0.7, yzoom=0.7)
label splashscreen:
    scene black
    with Pause(1)
    show text "Made By TamikiP" with dissolve
    with Pause(2)
    hide text with dissolve
    with Pause(1)
    return

label start:
    if title=="":
        $ t = threading.Thread(target=main,daemon = True)
        show loading movie
        $ t.start()
        while not generate_new_chapters_state:
            $ renpy.pause(1, hard=True)
            $ from main import generate_new_chapters_state
        scene black
        "资源加载完成,单击开始游戏"
    $ music_status=0
    if os.path.exists(rf"{game_directory}/data/{title}/music/background.mp3"):
        $ music_status=1
        play music [ rf"{game_directory}/data/{title}/music/background.mp3", rf"{game_directory}/data/{title}/music/background2.mp3" ] fadeout 2.0 fadein 2.0
    $ title=getconfig("剧情","story_title")
    if title!="":
        $ config.window_title = title
    while True:
        $ dialogues = load_dialogues(rf"{game_directory}/data/{title}/story.json")
        $ dialogue = get_next_dialogue()
        if dialogue is None:
            $ choice = load_choice(rf"{game_directory}/data/{title}/choice.json")
            $ choice1, choice2, choice3=choice['choice1'].replace("%", "%%").replace("[", "[[").replace("【", "【【").replace("{","{{"),choice['choice2'].replace("%", "%%").replace("[", "[[").replace("【", "【【").replace("{","{{"),choice['choice3'].replace("%", "%%").replace("[", "[[").replace("【", "【【").replace("{","{{")
            $ choice_list=list_change(choice1,choice2,choice3)
            $ answer = renpy.display_menu(choice_list, interact=True, screen='choice')
            if answer == "user_input":
                $ answer = renpy.input("请输入你接下来的选择:")
            if answer == "结束游戏":
                $end_thread()
                "正在生成结束剧情及音乐...(请点一下鼠标)"
                $ renpy.pause(0.5, hard=True)
                $ from main import generate_new_chapters_state
                while generate_new_chapters_state:
                    $ renpy.pause(1, hard=True)
                    $ from main import generate_new_chapters_state
                if os.path.exists(f"{game_directory}/data/{title}/music/end.mp3"):
                    $renpy.music.play([rf"{game_directory}/data/{title}/music/end.mp3",rf"{game_directory}/data/{title}/music/end1.mp3"], channel='music', loop=True, fadeout=None, synchro_start=False, fadein=0, tight=None, if_changed=False)
                $ current_dialogue_index = 0
                while True:
                    $ dialogues = load_dialogues(f"{game_directory}/data/{title}/end.json")
                    $ dialogue = get_next_dialogue()
                    if dialogue is None:
                        "游戏结束..."
                        return
                    $ character_name = dialogue["character"]
                    $ text = dialogue["text"].replace("%", "%%").replace("[", "[[").replace("【", "【【").replace("{","{{")
                    if os.path.exists(rf"{game_directory}/data/{title}/images/{dialogue['place']}.png".replace("%", "%%").replace("[", "[[").replace("【", "【【").replace("{","{{")):
                        $ background_image = rf"{game_directory}/data/{title}/images/{dialogue['place']}.png".replace("%", "%%").replace("[", "[[").replace("【", "【【").replace("{","{{")
                    else:
                        $ background_image = ""
                    $ audio = rf"{game_directory}/data/{title}/audio/end_{dialogue['id']}.wav"
                    if os.path.exists(rf"{game_directory}/data/{title}/images/{dialogue['character']}.png"):
                        $ character_image = rf"{game_directory}/data/{title}/images/{dialogue['character']}.png"
                    else:
                        $ character_image = ""
                    if character_name not in characters:
                        $ characters[character_name] = Character(character_name)
                    if character_name:
                        $ renpy.sound.play(audio, channel='sound')
                    if background_image:
                        scene expression background_image with fade
                    if character_image:
                        show expression character_image at small_center with dissolve
                    $ renpy.say(characters[character_name], f"『{text}』"if character_name != "" else text)
            $ create_thread(answer)
            "剧情生成中...(请点击一下鼠标)"
            $ renpy.pause(0.5, hard=True)
            $ from main import generate_new_chapters_state
            while generate_new_chapters_state:
                $ renpy.pause(1, hard=True)
                $ from main import generate_new_chapters_state
            $ dialogues = load_dialogues(rf"{game_directory}/data/{title}/story.json")
            $ dialogue = get_next_dialogue()
        $ character_name = dialogue["character"]
        $ text = dialogue["text"].replace("%", "%%").replace("[", "[[").replace("【", "【【").replace("{","{{")
        if os.path.exists(rf"{game_directory}/data/{title}/images/{dialogue['place']}.png".replace("%", "%%").replace("[", "[[").replace("【", "【【").replace("{","{{")):
            $ background_image =rf"{game_directory}/data/{title}/images/{dialogue['place']}.png".replace("%", "%%").replace("[", "[[").replace("【", "【【").replace("{","{{")
        else:
            $ background_image = ""
        $ audio = rf"{game_directory}/data/{title}/audio/{dialogue['id']}.wav"
        if os.path.exists(rf"{game_directory}/data/{title}/images/{dialogue['character']}.png"):
            $ character_image = rf"{game_directory}/data/{title}/images/{dialogue['character']}.png"
        else:
            $ character_image = ""
        if character_name not in characters:
            $ characters[character_name] = Character(character_name)
        if character_name:
            $ renpy.sound.play(audio, channel='sound')
        if background_image:
            scene expression background_image with fade
        if character_image:
            show expression character_image at small_center with dissolve
        $ renpy.say(characters[character_name], f"『{text}』"if character_name != "" else text)
        if os.path.exists(rf"{game_directory}/data/{title}/music/background.mp3") and music_status==0:
            $ music_status=1
            $renpy.music.play([rf"{game_directory}/data/{title}/music/background.mp3",rf"{game_directory}/data/{title}/music/background1.mp3"], channel='music', loop=True, fadeout=None, synchro_start=False, fadein=0, tight=None, if_changed=False)
    return
