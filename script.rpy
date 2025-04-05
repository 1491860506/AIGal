init python:
    import json
    import os
    import string
    import threading
    try:
        from main import main,story_continue,end,localstory,generate_new_chapters_state
        from getchoice import get_choice_id
    except ImportError as e:
        renpy.error(f"Failed to import required modules: {e}. Make sure main.py and getchoice.py are accessible.")

    # --- Threading Functions ---
    def create_thread(arg1, arg2):
        thread = threading.Thread(target=story_continue, args=(arg1, arg2,), daemon=True)
        thread.start()

    def end_thread(arg):
        thread = threading.Thread(target=end, args=(arg,), daemon=True)
        thread.start()

    # --- Utility Functions ---
    def load_dialogues(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "conversations" not in data:
                print(f"Dialogue file {filename} is missing 'conversations' key or it's not a list.")
                return None
            return data["conversations"]
        except FileNotFoundError:
            print(f"Dialogue file not found: {filename}")
            return None
        except (json.JSONDecodeError) as e:
            print(f"Error loading dialogue file {filename}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error loading dialogue file {filename}: {e}")
            return None

    def load_choice(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            print(f"Choice file not found: {filename}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error loading choice file {filename}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error loading choice file {filename}: {e}")
            return None

    def read(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = f.read()
            return data
        except FileNotFoundError:
            print(f"File not found for reading: {filename}")
            return ""

    def getconfig(a, b):
        config_file = os.path.join(renpy.config.gamedir, "config.json")
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(a, {}).get(b, "")
        except FileNotFoundError:
            return ""
        except json.JSONDecodeError as e:
            print(f"Error reading config file {config_file}: {e}")
            return ""
        except Exception as e:
            print(f"Unexpected error reading config file {config_file}: {e}")
            return ""

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
    _exit_loop = False
    title = None
    if getconfig("剧情", "story_title"):
        title=getconfig("剧情", "story_title")
        config.window_title = title
        if os.path.exists(os.path.join(renpy.config.gamedir, "data", title, "images","main_menu.png").replace("\\","/")):
            renpy.image("main_menu_background",os.path.join(renpy.config.gamedir, "data", title, "images","main_menu.png").replace("\\","/"))
        else:
            renpy.image("main_menu_background",os.path.join(renpy.config.gamedir,"gui","main_menu.png").replace("\\","/"))
    else:
        renpy.image("main_menu_background",os.path.join(renpy.config.gamedir,"gui","main_menu.png").replace("\\","/"))

    game_directory = renpy.config.gamedir.replace("\\", "/")

# --- Renpy Definitions and Transforms ---
define small_center = Transform(xalign=0.5, yalign=1.0, xzoom=0.7, yzoom=0.7)
image load = os.path.join(renpy.config.gamedir,"gui","custom","load.png").replace("\\","/")
image loading_background = os.path.join(renpy.config.gamedir,"gui","custom","loading_background.png").replace("\\","/")


transform spin:
    xpos 0.05
    ypos 0.65
    rotate 0
    linear 1.0 rotate 360
    repeat

transform my_position:
    xalign 0.5
    yalign 0.8

# --- Labels ---

label start:
    $ title = getconfig("剧情", "story_title")

    # --- Initial Setup / Generation ---
    if not title:
        python:
            _main_thread_started = True
            threading.Thread(target=main, daemon=True).start()

        show loading_background
        show load at spin


        python hide:
            _exit_loop = False
            try: from main import generate_new_chapters_state
            except ImportError: renpy.error("Cannot import state variable")

            while generate_new_chapters_state is not True:
                current_state_text = "{color=#FF0000}{size=72}大纲生成中...{/size}{/color}"
                if generate_new_chapters_state == "story":
                    current_state_text = "{color=#FF0000}{size=72}故事生成中...{/size}{/color}"
                elif generate_new_chapters_state == "picture":
                    current_state_text = "{color=#FF0000}{size=72}图像生成中...{/size}{/color}"
                elif generate_new_chapters_state == "error":
                    renpy.hide("load")
                    renpy.hide("loading_text_widget")
                    renpy.show("text", what=Text("生成过程中发生错误，无法继续。"), at_list=[my_position])
                    renpy.pause(2.0)
                    renpy.return_statement()
                    _exit_loop = True
                    break

                

                props = renpy.get_widget_properties("loading_text_widget")
                if props and props.get('text') != current_state_text:
                    renpy.hide("loading_text_widget")
                    renpy.show("text", what=Text(current_state_text), tag="loading_text_widget", at_list=[my_position])
                elif not props:
                    renpy.show("text", what=Text(current_state_text), tag="loading_text_widget", at_list=[my_position])

                renpy.pause(1, hard=True)
                try: from main import generate_new_chapters_state
                except ImportError:
                    renpy.hide("load")
                    renpy.hide("loading_text_widget")
                    renpy.show("text", what=Text("无法重新导入状态变量，可能发生错误。"), at_list=[my_position])
                    renpy.pause(2.0)
                    renpy.return_statement()
                    _exit_loop = True
                    break
            # End of python hide block

        if not _exit_loop:
            hide load
            hide loading_text_widget # Hiding works with the tag defined by 'as'
            scene black with dissolve

        $ title = getconfig("剧情", "story_title")
        if not title:
            "未能成功生成或获取故事标题，无法开始游戏。"
            pause 2.0
            return

    # --- Local Story Image Generation (Optional) ---
    $ local_story_path = os.path.join(game_directory, "data", title, "zw").replace("\\","/")
    $ images_path = os.path.join(game_directory, "data", title, "images").replace("\\","/")
    if os.path.exists(local_story_path) and not os.path.isdir(images_path):
        python:
            threading.Thread(target=localstory, daemon=True).start()

        show loading_background
        show load at spin
        show text "{color=#FF0000}{size=72}本地导入图像生成中...{/size}{/color}" as loading_text_widget at my_position with dissolve

        python hide:
            _exit_loop = False
            try: from main import generate_new_chapters_state
            except ImportError: renpy.error("Cannot import state variable")

            while generate_new_chapters_state is not True:
                if generate_new_chapters_state == "error":
                    renpy.hide("load")
                    renpy.hide("loading_text_widget")
                    renpy.show("text", what=Text("本地图像生成过程中发生错误。"), at_list=[my_position])
                    renpy.pause(2.0)
                    renpy.return_statement()
                    _exit_loop = True
                    break

                renpy.pause(1, hard=True)
                try: from main import generate_new_chapters_state
                except ImportError:
                    renpy.hide("load")
                    renpy.hide("loading_text_widget")
                    renpy.show("text", what=Text("无法重新导入状态变量，可能发生错误。"), at_list=[my_position])
                    renpy.pause(2.0)
                    renpy.return_statement()
                    _exit_loop = True
                    break
            # End of python hide block

        if not _exit_loop:
            hide load
            hide loading_text_widget
            scene black with dissolve

    # --- Post Loading / Game Start Setup ---
    $ config.window_title = title
    $ music_status = 0
    $ background_music_file1 = os.path.join(game_directory, "data", title, "music", "background.mp3").replace("\\","/")
    $ background_music_file2 = os.path.join(game_directory, "data", title, "music", "background2.mp3").replace("\\","/")

    if os.path.exists(background_music_file1):
        $ music_status = 1
        play music [ background_music_file1, background_music_file2 ] fadeout 2.0 fadein 2.0

    $ story_id = "0"
    $ current_dialogue_index = 0
    $ dialogues = []
    $ characters = {}

    # --- Main Game Loop ---
    while True:
        if not dialogues:
            $ dialogues_path = os.path.join(game_directory, "data", title, "story", f"{story_id}.json").replace("\\","/")
            $ dialogues = load_dialogues(dialogues_path)

            if dialogues is None:
                "错误：无法加载当前剧情段落 ([story_id]). 可能文件不存在或格式错误。"
                "请检查路径：[dialogues_path]"
                pause 3.0
                return

            if not dialogues:
                "注意：当前剧情段落 ([story_id]) 为空。"

            $ current_dialogue_index = 0

        $ dialogue = get_next_dialogue()

        if dialogue is None:
            # --- End of dialogues -> Show Choices (using renpy.display_menu) ---
            $ choice_file_path = os.path.join(game_directory, "data", title, "choice.json").replace("\\","/")
            $ choice_data = load_choice(choice_file_path)

            if choice_data is None:
                "错误：无法加载选项文件。"
                "路径：[choice_file_path]"
                pause 3.0
                return

            if story_id not in choice_data:
                "错误：在选项文件中找不到当前剧情点 ([story_id]) 的选项数据。"
                "游戏无法继续。"
                pause 3.0
                return

            python:
                choices_for_id = choice_data.get(story_id, [])
                menu_choices = []
                choice_keys = ['choice1', 'choice2', 'choice3']
                for i, key in enumerate(choice_keys):
                    if i < len(choices_for_id) and key in choices_for_id[i]:
                        original_text = choices_for_id[i][key]
                        display_text = original_text.replace("%", "%%").replace("[", "[[").replace("【", "【【").replace("{","{{")
                        menu_choices.append((display_text, original_text))
                menu_choices.append(("继续推进剧情", "continue_action"))
                menu_choices.append(("让我自己输入", "user_input"))

            $ chosen_value = renpy.display_menu(menu_choices)

            if chosen_value == "user_input":
                $ player_choice_text = renpy.input("请输入你接下来的选择:", length=100).strip()
                if not player_choice_text:
                    $ player_choice_text = "..."
                if player_choice_text == "结束游戏":
                    jump game_ending
            elif chosen_value == "continue_action":
                $ player_choice_text = "继续推进剧情"
            else:
                $ player_choice_text = chosen_value
                if player_choice_text == "结束游戏":
                    jump game_ending

            python:
                create_thread(player_choice_text, story_id)

            $ renpy.pause(0.5, hard=True)
            python hide:
                _exit_loop = False
                try: from main import generate_new_chapters_state
                except ImportError: renpy.error("Cannot import state variable")

                while generate_new_chapters_state:
                    if generate_new_chapters_state == "error":
                        renpy.show("text", what=Text("生成后续剧情时发生错误。"), at_list=[my_position])
                        renpy.pause(2.0)
                        renpy.return_statement()
                        _exit_loop = True
                        break
                    renpy.pause(1, hard=True)
                    try: from main import generate_new_chapters_state
                    except ImportError:
                        renpy.show("text", what=Text("无法重新导入状态变量。"), at_list=[my_position])
                        renpy.pause(2.0)
                        renpy.return_statement()
                        _exit_loop = True
                        break
                # End python hide

            $ next_story_id = get_choice_id(story_id, player_choice_text)

            if next_story_id is None or next_story_id == story_id:
                "错误：无法确定下一段剧情ID (收到: [next_story_id])."
                "请检查 get_choice_id 函数或后台处理逻辑。"
                pause 3.0
                return

            $ story_id = next_story_id
            $ dialogues = []

        else:
            # --- Display Current Dialogue ---
            $ character_name = dialogue.get("character", "")
            $ text = dialogue.get("text", "").replace("%", "%%").replace("[", "[[").replace("【", "【【").replace("{","{{")
            $ place = dialogue.get("place", "")
            $ dialogue_id = dialogue.get("id", "")

            $ background_image_path = os.path.join(game_directory, "data", title, "images", f"{place}.png").replace("\\","/") if place else ""
            $ character_image_path = os.path.join(game_directory, "data", title, "images", f"{character_name}.png").replace("\\","/") if character_name else ""
            $ audio_path = os.path.join(game_directory, "data", title, "audio", str(story_id), f"{str(dialogue_id)}.wav").replace("\\","/") if dialogue_id else ""

            $ background_image = background_image_path if background_image_path and os.path.exists(background_image_path) else ""
            $ character_image = character_image_path if character_image_path and os.path.exists(character_image_path) else ""

            if character_name and character_name not in characters:
                $ characters[character_name] = Character(character_name)



            if background_image:
                scene expression background_image with fade

            if character_image:
                show expression character_image as character_sprite at small_center with dissolve
            elif character_name:
                hide character_sprite
                pass


            if character_name and audio_path and os.path.exists(audio_path):
                voice audio_path
            if character_name:
                $ characters[character_name](f"『{text}』")
            else:
                "[text]"


            if music_status == 0 and os.path.exists(background_music_file1):
                $ music_status = 1
                $ renpy.music.play([background_music_file1,background_music_file2], channel='music', loop=True, fadeout=None, synchro_start=False, fadein=0, tight=None, if_changed=False)
    return

# --- Game Ending Label ---
label game_ending:

    python:
        end_thread(story_id)

    "正在生成结束剧情及音乐...(请稍候)"
    $ renpy.pause(0.5, hard=True)
    python hide:
        _exit_loop = False
        try: from main import generate_new_chapters_state
        except ImportError: renpy.error("Cannot import state variable")

        while generate_new_chapters_state:
            if generate_new_chapters_state == "error":
                renpy.show("text", what=Text("生成结局时发生错误。"), at_list=[my_position])
                renpy.pause(2.0)
                renpy.return_statement()
                _exit_loop = True
                break
            renpy.pause(1, hard=True)
            try: from main import generate_new_chapters_state
            except ImportError:
                renpy.show("text", what=Text("无法重新导入状态变量。"), at_list=[my_position])
                renpy.pause(2.0)
                renpy.return_statement()
                _exit_loop = True
                break
        # End python hide block
    $ ending_story_id = get_choice_id(story_id, "结束游戏")
    $ ending_music_file1 = os.path.join(game_directory, "data", title, "music", f"end_{story_id}.mp3").replace("\\","/")
    $ ending_music_file2 = os.path.join(game_directory, "data", title, "music", f"end_{story_id}_1.mp3").replace("\\","/")

    if os.path.exists(ending_music_file1):
        stop music fadeout 2.0
        play music [ ending_music_file1, ending_music_file2 ] loop fadein 2.0

    $ current_dialogue_index = 0
    $ ending_dialogues_path = os.path.join(game_directory, "data", title, "story", f"{ending_story_id}.json").replace("\\","/")
    $ dialogues = load_dialogues(ending_dialogues_path)

    if dialogues is None:
        "错误：无法加载结局剧情 ([ending_story_id])。"
        "路径：[ending_dialogues_path]"
        pause 3.0
        return

    if not dialogues:
        "（结局剧情为空）"
        pause 2.0
        return

    # --- Ending Dialogue Loop ---
    while True:
        $ dialogue = get_next_dialogue()
        if dialogue is None:
            pause 3.0
            return

        $ character_name = dialogue.get("character", "")
        $ text = dialogue.get("text", "").replace("%", "%%").replace("[", "[[").replace("【", "【【").replace("{","{{")
        $ place = dialogue.get("place", "")
        $ dialogue_id = dialogue.get("id", "")

        $ background_image_path = os.path.join(game_directory, "data", title, "images", f"{place}.png").replace("\\","/") if place else ""
        $ character_image_path = os.path.join(game_directory, "data", title, "images", f"{character_name}.png").replace("\\","/") if character_name else ""
        $ audio_path = os.path.join(game_directory, "data", title, "audio", str(ending_story_id), f"{str(dialogue_id)}.wav").replace("\\","/") if dialogue_id else ""

        $ background_image = background_image_path if background_image_path and os.path.exists(background_image_path) else ""
        $ character_image = character_image_path if character_image_path and os.path.exists(character_image_path) else ""

        if character_name and character_name not in characters:
            $ characters[character_name] = Character(character_name)

        if character_name and audio_path and os.path.exists(audio_path):
            voice audio_path

        if background_image:
            scene expression background_image with fade

        if character_image:
            show expression character_image as character_sprite at small_center with dissolve
        elif character_name:
            hide character_sprite
            pass

        if character_name:
            $ characters[character_name](f"『{text}』")
        else:
            "[text]"

    return