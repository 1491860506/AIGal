import json
import os
import random
from GPT import gpt, gpt_destroy
from handle_prompt import process_prompt
from typing import Union
try:
    import renpy
    game_directory = renpy.config.gamedir
except ImportError: 
    game_directory = os.getcwd()
def getchoice(target_id: str): # 参数名改为 target_id，并明确类型为 str
    """
    从大模型的输出中提取JSON，验证其有效性，并保存为指定格式的JSON文件。
    支持非连续的 target_id 值. 使用自增ID.
    同时保证新生成的ID不与 target_id 重复

    Args:
        target_id: 用于在最终JSON中作为主键的ID。 可以是非连续的值.

    Returns:
        "success" 如果JSON提取、验证和保存成功。
        "error" 如果提取、验证或保存失败。
    """

    config_file = os.path.join(game_directory, "config.json") # 使用 os.path.join 更可靠
    filename = "choice.json" # 去掉末尾的逗号

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error Config file not found at: {config_file}")
        return "error"
    except json.JSONDecodeError:
        print(f"Error decoding config.json at: {config_file}")
        return "error"
    except Exception as e: # 捕获其他可能的读取错误
        print(f"Error reading config file {config_file}: {e}")
        return "error"

    # story_title 的获取应在 try 块内或确保 config 已成功加载
    story_title = config.get("剧情", {}).get('story_title') # 使用 .get 防止KeyError
    if not story_title:
        print("Error: 'story_title' not found in config['剧情']")
        return "error"

    # 构建保存路径
    save_directory = os.path.join(game_directory, "data", story_title)
    os.makedirs(save_directory, exist_ok=True)  # 确保目录存在
    save_path = os.path.join(save_directory, filename)

    # 构建 prompt2
    try:
        prompt1, prompt2 = process_prompt('选项')
    except Exception as e:
        print(f"Error processing prompt: {e}")
        return "error"

    # 生成用于 GPT 调用的随机 request_id
    request_id = random.randint(1, 100000)

    while True:
        try:
            #print(f"Calling GPT with request_id: {request_id}") 
            output = gpt(prompt1, prompt2, 'option', request_id)  # 使用 request_id 调用 gpt

            if output == "error":
                print(f"gpt() returned 'error' for request_id: {request_id}")
                # 可以在这里添加重试逻辑或直接返回错误
                # return "error" # 如果不希望重试循环，则取消注释
                continue # 继续尝试下一次循环获取
            elif output == "over_times":
                print(f"Error GPT call exceeded maximum retries for request_id: {request_id}")
                return "error" # 超过重试次数，返回错误

            #print(f"GPT output received for request_id {request_id}: {output[:200]}...") # 打印部分输出

            # 尝试从输出中提取 JSON
            start_index = output.find('{')
            end_index = output.rfind('}')

            if start_index != -1 and end_index != -1 and start_index < end_index:
                json_string = output[start_index:end_index + 1]
                #print(f"Extracted JSON string: {json_string}") # 打印提取的字符串
            else:
                print(f"Error Could not find JSON start and end markers in GPT output for request_id: {request_id}")
                # 增加日志，可以选择重试或返回错误
                continue # 继续尝试

            try:
                # 尝试将提取的字符串解析为JSON
                parsed_data = json.loads(json_string)

                # 验证JSON是否包含指定的键
                if "choice1" in parsed_data and "choice2" in parsed_data and "choice3" in parsed_data:

                    # 获取 choice 值
                    choice1_val = parsed_data["choice1"]
                    choice2_val = parsed_data["choice2"]
                    choice3_val = parsed_data["choice3"]

                    # 读取现有文件内容，如果文件不存在或内容为空，则创建一个新的字典
                    try:
                        with open(save_path, 'r', encoding='utf-8') as f:
                            final_data = json.load(f)
                    except (FileNotFoundError, json.JSONDecodeError):
                        final_data = {}

                    # 找到 existing_id 和 target_id 中最大的一个
                    max_id = -1

                   # 循环遍历所有键和列表
                    for key, value in final_data.items():
                        if isinstance(value, list):
                            for item in value:
                                if isinstance(item, dict) and "id" in item:
                                    try:
                                        current_id = int(item["id"]) # 尝试将 ID 转换为整数
                                        max_id = max(max_id, current_id) # 更新 max_id

                                    except ValueError:
                                        print(f"Warning: Invalid ID format found: {item['id']}, skipping.")

                    # 尝试把 target_id 也转成 int， 并且更新 max_id
                    try:
                        target_id_int = int(target_id)
                        max_id = max(max_id, target_id_int)
                    except ValueError:
                        print(f"Warning: Invalid target_id format: {target_id}, will not be considered when generating new IDs. ")

                    # 生成新的ID
                    new_id_1 = str(max_id + 1)
                    new_id_2 = str(max_id + 2)
                    new_id_3 = str(max_id + 3)

                     # 创建包含 choice 和新 id 的字典列表
                    choice_list = [
                        {"choice1": choice1_val, "id": new_id_1},
                        {"choice2": choice2_val, "id": new_id_2},
                        {"choice3": choice3_val, "id": new_id_3}
                    ]

                    # 使用 target_id 作为键，并将结果保存到 final_data
                    final_data[target_id] = choice_list

                    # 将最终构建的 JSON 保存到文件
                    print(f"Saving final JSON structure to: {save_path}")
                    with open(save_path, "w", encoding="utf-8") as f:
                        json.dump(final_data, f, ensure_ascii=False, indent=4)

                    print(f"Successfully saved choices for target_id '{target_id}' to {save_path}")
                    gpt_destroy(request_id) # 成功后销毁 GPT 实例
                    return "success"
                else:
                    print(f"Parsed JSON does not contain required keys ('choice1', 'choice2', 'choice3'): {parsed_data}")
                    # 增加日志，可以选择重试或返回错误
                    continue # 继续尝试

            except json.JSONDecodeError as e:
                print(f"JSON parsing error for request_id {request_id}: {e}")
                print(f"Problematic JSON string: {json_string}")
                # 增加日志，可以选择重试或返回错误
                continue # 继续尝试

        except Exception as e:
            # 捕获更广泛的循环内错误
            import traceback
            print(f"An unexpected error occurred inside the loop for request_id {request_id}: {e}")
            traceback.print_exc() # 打印详细的错误堆栈
            # 考虑是否需要销毁 gpt 实例
            # gpt_destroy(request_id) # 可能需要根据错误类型决定是否销毁
            # return "error" # 或者可以选择继续循环
            continue # 继续尝试 (或者根据需要返回 "error")




def trace_id_chain(start_id: str) -> list:
    """
    追溯给定 id 的链，直到到达起始 id "0"。输出从小到大的id

    Args:
        start_id: 开始追溯的 id（字符串）。

    Returns:
        包含追溯路径中所有 id 的列表，如果追溯失败，则返回空列表。
    """
    config_file = os.path.join(game_directory, "config.json")
    filename = "choice.json"
    story_title = None # 初始化 story_title 以便在 try 块外访问
    save_path = None  # 初始化 save_path，以避免在 try 块外访问它
    
    if start_id == "0":
        return ["0"]  # 如果 start_id 是 "0"，则直接返回 ["0"]
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        story_title = config.get("剧情", {}).get('story_title') # 使用 .get 防止KeyError
        if not story_title:
            print("Error: 'story_title' not found in config['剧情']")
            return []  # 返回空列表表示失败

        # 构建保存路径
        save_directory = os.path.join(game_directory, "data", story_title)
        save_path = os.path.join(save_directory, filename) # save_path 现在可以被赋值

    except FileNotFoundError:
        print(f"Config file not found at: {config_file}")
        return []  # 返回空列表表示失败
    except json.JSONDecodeError:
        print(f"Error decoding config.json at: {config_file}")
        return []  # 返回空列表表示失败
    except Exception as e:
        print(f"Error reading config file {config_file}: {e}")
        return [] # 返回空列表表示失败

    # 确保如果 config 加载失败，我们仍然会返回空列表
    if not story_title or not save_path:  # 检查 save_path 是否被正确赋值
        return []

    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            final_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Choice file not found or is invalid JSON: {save_path}")
        return []  # 找不到选择文件或文件包含无效的 JSON，返回空列表

    chain = [start_id]
    current_id = start_id

    while current_id != "0":
        found = False
        for target_id, choices in final_data.items():
            # 确保 choices 是列表，并遍历列表中的每个选项字典
            if isinstance(choices, list):
                for choice in choices:
                    # 确保 choice 是字典，且包含 "id" 键
                    if isinstance(choice, dict) and "id" in choice:
                        if choice["id"] == current_id:
                            chain.append(target_id)
                            current_id = target_id
                            found = True
                            break
                if found:
                    break # 如果在当前 target_id 下找到，跳出外层循环
        if not found:  # 如果在任何 target_id 中都没有找到当前 ID
            print(f"Could not trace id: {current_id}. Returning empty List.")
            return []  # 无法追溯，返回空列表

    # 将 id 从小到大排序
    chain = sorted(chain, key=lambda x: int(x))
    return chain



def merge_story(target_id: str) -> int:
    """
    根据 ID 链合并故事情节，并保存到 output.json, output.txt 和 place.json。

    Args:
        target_id:  目标 ID（字符串）。

    Returns:
         1:  目标 ID 文件存在并成功合并和保存 all files.
         0:  目标ID文件不存在，成功合并和保存output.json, output.txt
        -1: 合并过程中有除目标ID文件外的 文件缺失，或者 config 文件问题
    """
    config_file = os.path.join(game_directory, "config.json")
    story_directory = None        # 故事文件目录
    output_json_path = None       # 合并后的 json 文件
    output_txt_path = None        # 合并后的 txt 文件  # 定义输出文件
    place_json_path = None
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        story_title = config.get("剧情", {}).get('story_title') # 使用 .get 防止KeyError
        if not story_title:
            print("Error: 'story_title' not found in config['剧情']")
            return -1  # 返回表示失败

        story_directory = os.path.join(game_directory, "data", story_title, "story")
        output_json_path = os.path.join(story_directory, "story.json")
        output_txt_path = os.path.join(story_directory, "story.txt") # 保存成txt
        place_json_path = os.path.join(story_directory, "place.json")

    except FileNotFoundError:
        print(f"Error Config file not found at: {config_file}")
        return -1  # 返回表示失败
    except json.JSONDecodeError:
        print(f"Error decoding config.json at: {config_file}")
        return -1  # 返回表示失败
    except Exception as e:
        print(f"Error reading config file {config_file}: {e}")
        return -1 # 返回表示失败

    # 安全检查
    if not story_directory or not output_json_path or not output_txt_path:
       return -1

    # 获取 id 链
    id_chain = trace_id_chain(target_id)  # 调用trace_id_chain函数
    if not id_chain: # 如果id链为空， 也就是追溯失败， 则返回 -1
        return -1

    merged_conversations = []          # 条目容器
    is_target_file_exist = 0  #Flag 指示目标 id 是否存在, 控制 place.json 的生成

    # 用于追踪上一个非空 place 的值， 辅助处理 place 字段
    last_valid_place = ""

    total_places = set()       # 用于排重, 获取所有非重复值
    new_places_in_target_id = []

    try:
        for id in id_chain:
            file_path = os.path.join(story_directory, f"{id}.json")

            if id == target_id:                              # 如果和目标ID相等
                if os.path.exists(file_path):                # 判断目标文件是否存在
                    is_target_file_exist = 1  #修改标识为存在
                    with open(file_path, 'r', encoding='utf-8') as f:
                         data = json.load(f)
                         conversations = data.get("conversations", [])
                         # 获取目标ID的place， 需要排除之前已经出现过的
                         for conv in conversations:
                             place = conv.get("place", "")
                             if place and place not in total_places: # 如果place存在，且没出现过
                                 new_places_in_target_id.append(place) # 保存到列表
                                 total_places.add(place)   # 添加到存储所有出现过的列表

                         merged_conversations.extend(conversations)

                else:    # 目标JSON文件不存在时 is_target_file_exist = 0
                   is_target_file_exist = 0
                continue

            if not os.path.exists(file_path):    # 判断文件是否存在
                print(f"Error Required file does not exist: {file_path}")
                return -1                                      # 如果文件不存在，返回-1

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                conversations = data.get("conversations", [])
                merged_conversations.extend(conversations)

                for conv in conversations:
                    place = conv.get("place", "")
                    if place:                    # 记录以及出现过的地点
                        total_places.add(place)

        # 合并完成后, 进行 place 字段的清洗, 注意要从头开始清理
        for i in range(len(merged_conversations)):
           if 'id' in merged_conversations[i]:
                del merged_conversations[i]['id']
           current_place = merged_conversations[i].get("place", "") # 取出当前 place

           if current_place != last_valid_place and current_place != "":  #如果有效,  和之前place不同
                last_valid_place = current_place       # 记录这一次的有效 place
           elif current_place == last_valid_place and current_place != "":
                merged_conversations[i]["place"] = ""  # 当前 place 和上次一样,  置空
           elif current_place == "":             # 如果当前 place 为空,  跳过
               continue

    except FileNotFoundError as e:
        print(f"FileNotFoundError: {e}")
        return -1  # 如果任何文件丢失, 返回-1
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        return -1   # 如果JSON解析失败, 返回-1
    except Exception as e:                  # 其他异常
        print(f"Exception: {e}")
        return -1

    # 保存合并后的数据到 output.json 文件
    try:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump({"conversations": merged_conversations}, f, ensure_ascii=False, indent=4)
        print(f"Successfully merged conversations and saved to: {output_json_path}")

    except Exception as e:
        print(f"Error saving to output.json: {e}")
        return -1  # 保存失败，返回-1

    # 保存为 TXT
    try:
        with open(output_txt_path, "w", encoding="utf-8") as f:
            for conv in merged_conversations:
                character = conv.get("character", "")
                text = conv.get("text", "")
                place = conv.get("place", "")

                if character: # 输出角色、文本
                    line = f"{character}：{text}"
                else:  # 旁白
                    line = f"旁白：{text}" # 旁白

                if place: # 如果有 place 就添加
                    line += f"[{place}]" # place属性

                f.write(line + "\n") # 写txt文件

        print(f"Successfully saved conversations to: {output_txt_path}")

    except Exception as e:
        print(f"Error saving to output.txt: {e}")
        return -1  # 保存失败，返回-1

    # 处理 place.json (只有目标文件存在的时候才处理)
    if is_target_file_exist:
        try:
            with open(place_json_path, "w", encoding="utf-8") as f:
                json.dump(new_places_in_target_id, f, ensure_ascii=False, indent=4)
            print(f"Successfully saved new places to: {place_json_path}")
        except Exception as e: # place json 写失败，不影响整个流程
             print(f"Error saving to place.json: {e}")

    if is_target_file_exist:
        return 1       # 表示目标ID文件存在, 也就是 返回1
    else:
        return 0       # 表示目标ID文件不存在, 则返回0


def get_choice_id(target_id: str, choice_text: str) -> Union[str, int]:
    config_file = os.path.join(game_directory, "config.json")
    filename = "choice.json" # 选择文件
    story_title = None       # 故事名字
    save_path = None
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        story_title = config.get("剧情", {}).get('story_title') # 使用 .get 防止KeyError
        if not story_title:
            print("Error: 'story_title' not found in config['剧情']")
            return -1  # 返回表示失败

        # 构建保存路径
        save_directory = os.path.join(game_directory, "data", story_title)
        save_path = os.path.join(save_directory, filename)  # 选择文件路径

    except FileNotFoundError:
        print(f"Error Config file not found at: {config_file}")
        return -1  # 返回表示失败
    except json.JSONDecodeError:
        print(f"Error decoding config.json at: {config_file}")
        return -1  # 返回表示失败
    except Exception as e:
        print(f"Error reading config file {config_file}: {e}")
        return -1 # 返回错误代码

    # 安全检查， 如果依赖值为空， 返回错误
    if not story_title or not save_path:
        return -1

    try:
        with open(save_path, 'r', encoding='utf-8') as f: # 打开选择文件
            final_data = json.load(f) # 加载
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Error Choice file not found or is invalid JSON: {save_path}")
        final_data = {}      # 如果文件不存在， 创建一个空字典

    # 尝试查找现有选项
    if target_id in final_data:
        for choice in final_data[target_id]:   # 访问目标ID下面的所有条目
            # 如果存在这个条目
            if choice_text in choice.values(): #在value中进行查找
                return str(choice.get("id"))   # 找到了直接将ID返回
    else:
        print(f"Error Target ID '{target_id}' not found in choice file.")

    # 如果target_id存在，文本没有找到，则添加新的 Choice
    if target_id in final_data:
        # 添加的代码是参照之前 生成新的ID 代码
        max_id = -1

        # 循环遍历所有键和列表
        for key, value in final_data.items():    # 首先找到最大的ID

            if isinstance(value, list):  #  然后找到类型是list的values
                for item in value:       #   然后进行遍历
                    if isinstance(item, dict) and "id" in item:    #   然后判断当前的item是否是字典, 并且key中要包含id的
                        try:
                            current_id = int(item["id"])            # 尝试将 ID 转换为整数
                            max_id = max(max_id, current_id)        # 更新 max_id 的值

                        except ValueError as e:
                            print(f"Warning: Invalid ID format found: {item['id']}, skipping.: {e}")

        new_id = str(max_id + 1)    # 新ID
        new_choice = {"choice": choice_text, "id": new_id}  # 构建新的对象
        final_data[target_id].append(new_choice)   # final_data 尾部增加
        print(f"Created new choice with id '{new_id}' under target_id '{target_id}'.")

        # 保存修改后的数据到文件
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=4)

            return new_id   # 返回新id
        except Exception as e:   # 异常
            print(f"Error saving to choice file: {e}")
            return -1 # 还是返回错误

    else:
        print(f"Error Target id not exist: {target_id}")  # id 不存在
        return -1  # 如果target_id不存在，返回-1










# 主程序入口示例
if __name__=="__main__":
    #print("Starting getchoice function directly...")
    # 示例调用，传入目标 ID "0"
    #result = getchoice("0")
    #print(f"getchoice('0') result: {result}")
    #generate_choice_tree_html()
    # 可以测试其他 ID, 非连续的 id
    #result = getchoice("2")
    #print(f"getchoice('2') result: {result}")

    #result = getchoice("5")
    #print(f"getchoice('5') result: {result}")


    # 假设从 id "9" 开始追溯
    #result = trace_id_chain("9") # 假设id 9 存在
    #print(f"trace_id_chain('9') result: {result}")
    # 预计输出: ['9', '5', '2', '0']

    #result = trace_id_chain("5")  #假设追溯 id "5"
    #print(f"trace_id_chain('5') result: {result}") # 预计输出 ['5', '2', '0']

    #result = trace_id_chain("2") # 从 "0" 开始
    #print(f"trace_id_chain('2') result: {result}") # 预计输出 ['0#result = trace_id_chain("100")  # 假设 id "100" 不存在
    #print(f"trace_id_chain('100') result: {result}") # 预计输出 []

    pass
    
    #test_target_id = "9"
    #result = merge_story("4")
    #print(result)


    #print(get_choice_id("5","仔细询问优子关于“守夜人”的事情，或许她知道更多。"))
