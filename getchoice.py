import json
import configparser
import os
from GPT import gpt, gpt_destroy  
import random
from handle_prompt import process_prompt

try:
    import renpy

    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

def getchoice(config_file=rf"{game_directory}\config.ini", filename="choice.json"):
    """
    从大模型的输出中提取JSON，验证其有效性，并保存到文件中。

    Args:
        config_file: 配置文件名。
        filename: 保存JSON的文件名（不包含路径）。

    Returns:
        "success" 如果JSON提取、验证和保存成功。
        "error" 如果提取、验证或保存失败。
    """

    config = configparser.ConfigParser()
    config.read(config_file, encoding="utf-8")

    try:
        import renpy

        game_directory = renpy.config.gamedir
    except:
        game_directory = os.getcwd()

    story_title = config.get('剧情', 'story_title')

    # 构建保存路径
    save_directory = os.path.join(game_directory, "data", story_title)
    os.makedirs(save_directory, exist_ok=True)  # 确保目录存在
    save_path = os.path.join(save_directory, filename)

    # 构建 prompt2
    prompt1,prompt2=process_prompt('选项')
    # 生成随机id
    id = random.randint(1, 100000)  # 生成一个1到100000之间的随机正整数

    while True:
        try:
            output = gpt(prompt1, prompt2, 'option', id)  # 获取大模型输出
            if output == "error":
                print(f"gpt() 返回 'error'")
                continue
            elif output == "over_times":
                print("gpt 调用超出最大重试次数")
                return "error"

            # 尝试从输出中提取 JSON
            start_index = output.find('{')
            end_index = output.rfind('}')

            if start_index != -1 and end_index != -1 and start_index < end_index:
                json_string = output[start_index:end_index + 1]
            else:
                print(f"未找到JSON的起始和结束标记")
                continue

            try:
                # 尝试将提取的字符串解析为JSON
                data = json.loads(json_string)

                # 验证JSON是否包含指定的键
                if "choice1" in data and "choice2" in data and "choice3" in data:
                    # 将JSON保存到文件
                    with open(save_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)  # 使用 ensure_ascii=False 和 indent=4 提高可读性
                    gpt_destroy(id)
                    return "success"
                else:
                    print(f"JSON 不包含 'choice1', 'choice2', 'choice3' 键")
                    continue

            except json.JSONDecodeError as e:
                print(f"JSON 解析错误: {e}")
                continue

        except Exception as e:
            print(f"发生内部错误: {e}")
            continue


if __name__=="__main__":
    getchoice()
