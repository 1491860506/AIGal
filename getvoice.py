import json
import re
import requests
import os

try:
    import renpy

    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

def generate_single_audio(name_id, text, status, output_name, config, audio_directory):  # Added config and audio_directory
    """
    Generates a single audio file using SOVITS.
    """
    model_name = config['SOVITS'].get(f'model{name_id}')
    path = config['SOVITS'].get(f'path{name_id}')
    prompt_text = config['SOVITS'].get(f'text{name_id}')
    if status == 0:
        requests.get(
            f"http://127.0.0.1:9880/set_gpt_weights?weights_path=GPT_weights_v2/{model_name}.ckpt")
        requests.get(
            f"http://127.0.0.1:9880/set_sovits_weights?weights_path=SoVITS_weights_v2/{model_name}.pth")
    Lang = "zh"
    Theme_Language = config['剧情'].get('language') #Read from the config at the time it's used
    if Theme_Language == "中文":
        Lang = "zh"
    elif Theme_Language == "英文":
        Lang = "en"
    else:
        Lang = "ja"
    new_url = f'http://127.0.0.1:9880/tts?text={text}&text_lang={Lang}&ref_audio_path={path}&prompt_lang=zh&prompt_text={prompt_text}&text_split_method=cut5&batch_size=1&media_type=wav&streaming_mode=false'
    try:
        response = requests.get(new_url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        with open(os.path.join(audio_directory, f'{output_name}.wav'), 'wb') as file:
            file.write(response.content)
        return "ok"

    except requests.exceptions.RequestException as e:
        print("Request error:", e)
        return "error"
    except Exception as e:
        print("Other error:", e)
        return "error"

def getvoice(story_id):
    """
    Reads story and character data from JSON files, processes the story from a given start_id.
    If start_id is None, it finds the largest ID in the audio directory and continues from there.
    story.json and character.json are assumed to reside in {game_directory}/data/{story_title}/
    """
    start_id=1
    # Define game_directory for testing purposes, replace with your actual game directory.
    config_file = os.path.join(game_directory, "config.json")
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    #config = configparser.ConfigParser()  # Read it first thing
    #config.read(os.path.join(game_directory, "config.ini"), encoding='utf-8')

    story_title = config["剧情"].get("story_title", "")
    audio_directory = os.path.join(game_directory, "data", story_title, "audio")
    os.makedirs(audio_directory, exist_ok=True)
    audio_directory=os.path.join(audio_directory,story_id)
    os.makedirs(audio_directory, exist_ok=True)


    story_file = os.path.join(game_directory, "data", story_title,"story", f"{story_id}.json")
    character_file = os.path.join(game_directory, "data", story_title, "character.json")

    # Determine the starting ID
    if start_id is None:
        # Find the largest ID in the audio directory
        start_id = 1
        try:
            audio_files = [f for f in os.listdir(audio_directory) if f.endswith(".wav")]
            if audio_files:
                # Extract IDs from filenames and find the maximum
                ids = [int(f.replace(".wav", "")) for f in audio_files if
                       f.replace(".wav", "").isdigit()]  # Only consider filenames that are purely digits
                if ids:
                    start_id = max(ids)
                else:
                    print("No valid audio files found in the folder")
        except FileNotFoundError:
            print(f"Error: Audio directory '{audio_directory}' not found.")
            return
        except ValueError:
            print(f"Error: Some files in '{audio_directory}' are not in correct format(integer).wav")

    try:
        with open(story_file, 'r', encoding='utf-8') as f:
            story_data = json.load(f)
        conversations = story_data["conversations"]  # Access conversations list
    except FileNotFoundError:
        print(f"Error: Story file '{story_file}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON in '{story_file}'.")
        return
    except KeyError:
        print(f"Error: The story data has no 'conversations' key.")
        return

    try:
        with open(character_file, 'r', encoding='utf-8') as f:
            character_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Character file '{character_file}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON in '{character_file}'.")
        return

    start_index = -1
    for i, conversation in enumerate(conversations):
        if conversation["id"] == start_id:
            start_index = i
            break
    if start_index == -1:
        # If the existing start_id is not fount increment to the next id and continue.
        start_id = start_id + 1
        print(f"start_id '{start_id - 1}' not found, resuming from {start_id}")
        start_index = 0  # Start from conversations[0] as new audio files will start from next id and also the files are reprocessed.

    previous_model_name = None
    status = 0  # Initialize status for the first call
    for i in range(start_index, len(conversations)):
        conversation = conversations[i]
        character_name = conversation["character"]
        story_text = conversation["text"]  # get text
        conversation_id = conversation["id"]  # Get converation id to use as output name

        # Check if the audio file already exists
        output_file_path = os.path.join(audio_directory, f"{conversation_id}.wav")
        if os.path.exists(output_file_path):
            #print(f"Audio file already exists for conversation ID: {conversation_id}. Skipping.")
            continue

        if not character_name:
            continue  # Skip if character is empty

        # Remove parentheses and their contents
        text_without_parentheses = re.sub(r'[\(（].*?[\)）]', '', story_text)

        # Replace space with chinese comma and newline with chinese period.
        text_replaced = text_without_parentheses.replace(" ", "，").replace("\n", "。")

        # Remove leading commas and periods.
        while text_replaced.startswith("，") or text_replaced.startswith("。"):
            text_replaced = text_replaced[1:]

        # Skip if the text is empty after processing
        if not text_replaced.strip():  # .strip() removes leading/trailing whitespace
            continue

        place_id = 6  # Default value if character not found

        for j, character in enumerate(character_data):
            if character["name"] == character_name:
                place_id = j + 1  # JSON indices start from 1 according to your request
                break

        model_name = config['SOVITS'].get(f'model{place_id}')  # Get model_name here

        if previous_model_name is not None:  # not the first time
            if model_name == previous_model_name:
                status = 1
            else:
                status = 0

        generate_single_audio(place_id, text_replaced, status=status, output_name=str(conversation_id), config=config,
                              audio_directory=audio_directory)

        previous_model_name = model_name  # store model_name for the next loop



