import json
import random
import requests
import os
import re
from typing import Dict, List, Set

# 全局状态存储
gpt_model_list: Dict[int, List[Dict]] = {}
pending_destruction: Set[int] = set()

def map_kind(kind: str) -> str:
    """扩展后的kind映射关系"""
    kind_mappings = [
        {"大纲": ["outline", "纲要", "目录生成", "章节规划"]},
        {"正文": ["plot", "文本生成", "故事发展", "剧情推进"]},
        {"选项": ["choice", "choose","option", "分支选择", "用户决策"]},
        {"人物": ["character","character_ai_draw","角色设计", "人物设定", "NPC生成", "角色对话"]},
        {"背景": ["background","background_ai_draw","世界观", "场景描述", "环境设定", "地点生成"]},
        {"音乐": ["music","music_prompt","BGM推荐", "音效建议", "氛围音乐","background_music"]},
        {"总结" :["summary", "要点归纳", "内容摘要"]},
    ]

    for mapping in kind_mappings:
        for config_kind, aliases in mapping.items():
            if kind.lower() in [a.lower() for a in aliases]:
                return config_kind
    return kind

# 路径获取和配置初始化
try:
    import renpy
    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()

config_file = os.path.join(game_directory, "config.json")

def load_config():
    """Loads the configuration from the config.json file."""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        return config_data
    except FileNotFoundError:
        print("Config file not found.")
        return {}
    except json.JSONDecodeError:
        print("Error decoding config.json.")
        return {}

config = load_config()


def initialize_models(id: int, kind_config: List[Dict]):
    """带状态验证的模型初始化"""
    models = []
    for item in kind_config:
        config_name = item["config"]
        model_name = item["model"]
        
        try:
            config_list = config["模型"]["configs"] #json.loads(config.get("模型", f"config_{config_name}_models"))
            #print(config_list.keys())
            #print(model_name)
            #print(config_name)
            model_list=config_list[config_name]["models"]
            model_info = next((m for m in model_list if m["name"] == model_name), None)
            if not model_info:
                continue
        except:
            continue
        
        models.append({
            "config": config_name,
            "model": model_name,
            "weigh": int(item["weigh"]),
            "priority": int(item["priority"]),
            "max_retry": int(model_info.get("max_retry", 3)),
            "temperature": model_info.get("temperature", ""),
            "top_p": model_info.get("top_p", ""),
            "penalty": model_info.get("frequency_penalty", ""),
            "max_tokens": model_info.get("max_tokens", "")
        })
    
    # 直接处理空模型列表的情况
    if not models:
        pending_destruction.add(id)
        return
    
    gpt_model_list[id] = models

def select_model(current_models: List[Dict]) -> Dict:
    """带空值保护的模型选择"""
    if not current_models:
        return None
    
    priority_groups = {}
    for model in current_models:
        priority = model["priority"]
        priority_groups.setdefault(priority, []).append(model)
    
    if not priority_groups:
        return None
    
    max_priority = max(priority_groups.keys())
    candidates = priority_groups[max_priority]
    
    total_weight = sum(m["weigh"] for m in candidates)
    if total_weight <= 0:
        return None
    
    return random.choices(candidates, weights=[m["weigh"] for m in candidates], k=1)[0]

def gpt(system: str, prompt: str, kind: str, id: int) -> str:
    """带即时销毁机制的主函数"""
    # 优先处理待销毁状态
    if id in pending_destruction:
        pending_destruction.discard(id)
        gpt_destroy(id)
        return "over_times"
    
    # 检查已销毁状态
    if id not in gpt_model_list and id in pending_destruction:
        return "over_times"
    
    # Kind映射处理
    mapped_kind = map_kind(kind)
    
    # 配置获取
    kind_config = None
    for check_kind in [mapped_kind, "默认"]:
        kind_config_key = f"{check_kind}_setting"
        if kind_config_key in config["模型"] and config["模型"][kind_config_key]:
            kind_config = config["模型"][kind_config_key] 
            break
    
    if not kind_config:
        print("未在接入模型配置中配置模型")
        return "over_times"
    
    # 初始化检测
    if id not in gpt_model_list:
        initialize_models(id, kind_config)
        if id in pending_destruction:
            return "over_times"
    
    current_models = gpt_model_list.get(id, [])
    if not current_models:
        pending_destruction.add(id)
        return "over_times"
    
    # 模型选择
    selected_model = select_model(current_models)
    if not selected_model:
        pending_destruction.add(id)
        return "over_times"
    
    # API准备
    try:
        baseurl = config["模型"]["configs"][selected_model['config']]["model_baseurl"] 
        apikey = config["模型"]["configs"][selected_model['config']]["api_key"]
    except KeyError:#configparser.NoOptionError:
        pending_destruction.add(id)
        return "error"
    
    # 构建请求
    data = {
        "model": selected_model["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
    }
    
    # 参数处理
    for param in ["temperature", "top_p", "penalty"]:
        param_value = selected_model[param].strip()
        if param_value:
            try:
                data[param] = float(param_value)
            except:
                pass
    
    # 请求执行
    try:
        response = requests.post(baseurl+'/chat/completions', headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {apikey}",
            "Content-Type": "application/json"
        }, json=data)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
        result = content
    except Exception as e:
        result = "error"
    
    # 状态更新
    selected_model["max_retry"] -= 1
    if selected_model["max_retry"] <= 0:
        gpt_model_list[id] = [m for m in current_models if m != selected_model]
    
    # 即时销毁检测
    if not gpt_model_list.get(id, []):
        pending_destruction.add(id)
    
    return result

def gpt_destroy(id: int):
    """增强的销毁函数"""
    pending_destruction.discard(id)
    if id in gpt_model_list:
        del gpt_model_list[id]

if __name__ == "__main__":
    # 强化测试案例
    test_id = 2023
    print("=== 极限压力测试 ===")
    
    for i in range(1, 29):
        print(f"\n第{i}次调用:")
        result = gpt(
            system="你好",
            prompt="你好，你是谁",
            kind="大纲",  # 测试kind映射
            id=test_id
        )
        
        # 显示状态信息
        models = gpt_model_list.get(test_id, [])
        status = f"剩余模型: {len(models)}个"
        if models:
            status += f" | 最高优先级: {max(m['priority'] for m in models)}"
        
        print(f"状态: {status}")
        print(f"返回: {result[:30]}...")  # 截断长文本
        
        # 最后一次调用后显示最终状态
        if i == 29:
            print("\n最终模型池状态:", 
                json.dumps(gpt_model_list.get(test_id), indent=2, ensure_ascii=False))
