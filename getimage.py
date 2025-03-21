import configparser
import requests
import json
import time
import os
import urllib3
import threading
import random
import re
import random
import queue
from handle_prompt import process_prompt
from GPT import gpt, gpt_destroy

urllib3.disable_warnings()

try:
    import renpy
    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()


class ModelManager:
    """Manages AI drawing models with thread-safe operations"""
    def __init__(self, config, kind, total_tasks):
        self.config = config
        self.kind = kind
        self.all_priorities = None
        self.models = []
        self.current_priority_index = 0
        self.terminate_flag = False
        self.lock = threading.RLock()
        self.load_models_by_highest_priority()
        self.total_tasks = total_tasks

    def load_models_by_highest_priority(self):
        """Load models with the highest priority available"""
        with self.lock:
            if self.all_priorities is None:
                models_config = json.loads(self.config.get('AI_draw', f'{self.kind}_config'))
                self.all_priorities = sorted(set(model["priority"] for model in models_config), reverse=True)

            if self.current_priority_index >= len(self.all_priorities):
                print("No more priorities left to load. Setting terminate flag.")
                self.terminate_flag = True
                return False
            
            target_priority = self.all_priorities[self.current_priority_index]

            models_to_load = [
                model_config for model_config in json.loads(self.config.get('AI_draw', f'{self.kind}_config'))
                if model_config["priority"] == target_priority
            ]
            
            if not models_to_load:
                print(f"No models available for priority {target_priority}. Moving to next priority.")
                self.current_priority_index += 1
                return self.load_models_by_highest_priority()
            
            self.models = []
            for model_config in models_to_load:
                model_name = model_config["config"]
                max_concurrency = self.config.get('AI_draw', f'config_{model_name}_maxconcurrency')
                max_concurrency = int(max_concurrency) if max_concurrency else 1
                
                model = {
                    'name': model_name,
                    'weigh': model_config["weigh"],
                    'priority': target_priority,
                    'available_concurrency': max_concurrency,
                    'possibility': 0
                }
                self.models.append(model)
            
            self.update_possibilities()
            print(f"Loaded models with priority {target_priority}: {[model['name'] for model in self.models]}")
            return True

    def update_possibilities(self):
        """Update selection probabilities of models based on weights and available concurrency"""
        with self.lock:
            total_weight = sum(model['weigh'] for model in self.models if model['available_concurrency'] > 0)
            
            if total_weight == 0:
                for model in self.models:
                    model['possibility'] = 0
            else:
                for model in self.models:
                    if model['available_concurrency'] > 0:
                        model['possibility'] = model['weigh'] / total_weight
                    else:
                        model['possibility'] = 0

    def get_model(self):
        """Get an available model based on probabilities"""
        with self.lock:
            available_models = [model for model in self.models if model['possibility'] > 0]
            
            if not available_models:
                return None
            
            probabilities = [model['possibility'] for model in available_models]
            selected_model = random.choices(available_models, weights=probabilities, k=1)[0]
            
            selected_model['available_concurrency'] -= 1
            self.update_possibilities()
            
            return selected_model.copy()

    def release_model(self, model_name, status, completed_tasks, task_lock):
        """Release a model after use, potentially removing it if it failed."""
        with self.lock:
            for i, model in enumerate(self.models):
                if model['name'] == model_name:
                    if status == 'retry_over_times':
                        print(f"Model {model_name} removed due to exceeding retry limits")
                        self.models.pop(i)
                    else:
                        model['available_concurrency'] += 1
                    
                    self.update_possibilities()
                    break

            if not self.models:
                print(f"All models from priority {self.all_priorities[self.current_priority_index]} removed. Loading next priority...")
                self.current_priority_index += 1

                if not self.load_models_by_highest_priority():
                    self.terminate_flag = True

def getparams(config, model):
    """Retrieves parameters for a given model from the configuration."""
    url1 = config.get('AI_draw', f'config_{model}_request_url')
    method1 = config.get('AI_draw', f'config_{model}_request_method')
    headers1_str = (config.get('AI_draw', f'config_{model}_headers')).replace('\\n', '')
    headers1 = dict(eval(headers1_str))
    body1 = config.get('AI_draw', f'config_{model}_request_body')
    path1 = config.get('AI_draw', f'config_{model}_json_path')
    success1 = config.get('AI_draw', f'config_{model}_success_condition')
    fail1 = config.get('AI_draw', f'config_{model}_fail_condition')
    second_request = config.get('AI_draw', f'config_{model}_second_request')
    url2 = config.get('AI_draw', f'config_{model}_second_request_url')
    method2 = config.get('AI_draw', f'config_{model}_second_request_method')
    headers2_str = (config.get('AI_draw', f'config_{model}_second_headers')).replace('\\n', '')
    headers2 = dict(eval(headers2_str))
    body2 = config.get('AI_draw', f'config_{model}_second_request_body')
    path2 = config.get('AI_draw', f'config_{model}_second_json_path')
    success2 = config.get('AI_draw', f'config_{model}_second_success_condition')
    fail2 = config.get('AI_draw', f'config_{model}_second_fail_condition')
    
    # Get timeout parameters
    request_timeout = config.get('AI_draw', f'config_{model}_request_timeout')
    request_timeout = int(request_timeout) if request_timeout and request_timeout.strip() else 30
    
    second_request_timeout = config.get('AI_draw', f'config_{model}_second_request_timeout')
    second_request_timeout = int(second_request_timeout) if second_request_timeout and second_request_timeout.strip() else 15
    
    return (url1, method1, headers1, body1, path1, success1, fail1, 
            second_request, url2, method2, headers2, body2, path2, success2, fail2,
            request_timeout, second_request_timeout)

def writefile(path, content):
    """Writes content to a file."""
    with open(path, 'wb') as f:
        f.write(content)

def getfile(path, url):
    """Downloads a file from a URL and saves it to a path."""
    response = requests.get(url)
    with open(path, 'wb') as f:
        f.write(response.content)

def generate(config, images_directory, prompt, image_name, model):
    """Generates an image based on the given prompt and model."""
    params = getparams(config, model)
    url1, method1, headers1, body1, path1, success1, fail1, second_request, url2, method2, headers2, body2, path2, success2, fail2, request_timeout, second_request_timeout = params
    file_path = os.path.join(images_directory, f"{image_name}.png")
    url1 = url1.replace("{prompt}", f"{prompt}")
    body1 = body1.replace("{prompt}", f"{prompt}")
    
    # First request
    try:
        if method1 == 'POST':
            response = requests.post(url1, headers=headers1, data=body1, timeout=request_timeout)
        elif method1 == 'GET':
            response = requests.get(url1, headers=headers1, timeout=request_timeout)
        else:
            return "error"
    except (requests.exceptions.Timeout, Exception):
        return "error"

    if path1 == "direct":
        if fail1 and eval(fail1):
            return "error"
        if success1 and not eval(success1):
            return "error"
        try:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return "success"
        except:
            return "error"

    try:
        result = json.loads(response.text)
    except json.JSONDecodeError:
        return "error"
    
    if fail1 and eval(fail1):
        return "error"
    
    if second_request == 'False':
        if success1 and not eval(success1):
            return "error"
        try:
            getfile(file_path, eval(f"{result}{path1}"))
            return "success"
        except:
            return "error"

    result = eval(f"{result}{path1}")
    if url2 == 'userdefine':
        try:
            exec(body2.replace("writefile(", f"writefile('{file_path}',"))
            return "success"
        except:
            return "error"
    
    url2 = url2.replace("{result}", f"{result}")
    body2 = body2.replace("{result}", f"{result}")
    
    # Second request
    while True:
        try:
            if method2 == 'GET':
                response = requests.get(url2, headers=headers2, timeout=second_request_timeout)
            elif method2 == 'POST':
                response = requests.post(url2, headers=headers2, data=body2, timeout=second_request_timeout)
            else:
                return "error"
        except (requests.exceptions.Timeout, Exception):
            return "error"

        if path2 == "direct":
            if fail2 and eval(fail2):
                return "error"
            if success2 and not eval(success2):
                return "error"
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return "success"

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            return "error"
            
        if fail2 and eval(fail2):
            return "error"
        if success2 and eval(success2):
            try:
                getfile(file_path, eval(f"{result}{path2}"))
                return "success"
            except:
                return "error"
        time.sleep(1)

def rembg(config, images_directory, image_name, kind):
    """Removes the background from an image with a timeout and retry mechanism."""
    if kind == 'character':
        file_path = os.path.join(images_directory, f"{image_name}.png")
        rembg_url = "http://localhost:7000/api/remove"
        data = {
            "model": "isnet-anime",
            "a": "true",
            "af": 240
        }

        retries = 3  # Maximum retry attempts
        for attempt in range(1, retries + 1):
            try:
                with open(file_path, 'rb') as file:
                    response = requests.post(rembg_url, files={'file': file}, data=data, timeout=30)
                    if response.status_code == 200:
                        with open(file_path, 'wb') as output_file:
                            output_file.write(response.content)
                        return "success"
                    else:
                        print(f"rembg response failed, status code: {response.status_code}, attempt: {attempt}")
            except requests.exceptions.Timeout:
                print(f"rembg timeout, retry attempt {attempt}...")
            except Exception as e:
                print(f"rembg processing error, retry attempt {attempt}, reason: {e}")

        print("rembg processing failed, exceeded maximum retry attempts")
        return "error"

    return "pass"

def check_image_size(images_directory, image_name, kind):
    """Check if the generated image meets the minimum size requirements"""
    file_path = os.path.join(images_directory, f"{image_name}.png")
    if not os.path.exists(file_path):
        return False
    
    file_size = os.path.getsize(file_path) / 1024  # Size in KB
    
    if kind == 'character' and file_size < 500:
        return False
    elif kind == 'background' and file_size < 1024:  # 1MB = 1024KB
        return False
    
    return True

def generate_image_thread(config, images_directory, model_manager, task_queue, results, prompt, image_name, model, kind):
    """Thread function to generate images with a specific model"""
    retry = config.get('AI_draw', f'config_{model}_max_attempts')
    delay = config.get('AI_draw', f'config_{model}_delay_time')
    retry = int(retry) if retry else 1
    delay = int(delay) if delay else 1
    
    for i in range(retry):
        try:
            status = generate(config, images_directory, prompt, image_name, model)
            if status == 'success':
                # Process with rembg for character images
                rembg(config, images_directory, image_name, kind)
                
                # Check image size requirements
                size_check_attempts = 3
                size_ok = False
                
                for _ in range(size_check_attempts):
                    if check_image_size(images_directory, image_name, kind):
                        size_ok = True
                        break
                    # If size check fails, regenerate
                    status = generate(config, images_directory, prompt, image_name, model)
                    if status != 'success':
                        break
                    rembg(config, images_directory, image_name, kind)
                
                if size_ok:
                    print(f'{image_name} successfully generated')
                    results[image_name] = 'success'
                    return 'success'
                else:
                    print(f'{image_name} failed size check after multiple attempts')
                    status = 'error'
            
            if status == 'error':
                print(f'Failed to generate {image_name} on attempt {i+1}')
                time.sleep(delay)
                continue
            elif status == 'retry_over_times':
                print(f'Model {model} exceeded retry limit for {image_name}')
                # This model is not working, put the task back in the queue with a different model
                task_queue.put((prompt, image_name))
                return 'retry_over_times'
                
        except Exception as e:
            print(f'Error generating {image_name} on attempt {i+1}: {e}')
            time.sleep(delay)
    
    # If we get here, all attempts failed
    results[image_name] = 'failed'
    # Put the task back in the queue to try with another model
    task_queue.put((prompt, image_name))
    return 'retry_over_times'



def worker(config, images_directory, model_manager, task_queue, results, kind, completed_tasks, task_lock, total_tasks):
    """Worker thread that processes image generation tasks"""
    while not model_manager.terminate_flag:
        try:
            try:
                prompt, image_name = task_queue.get(block=True, timeout=0.1)
            except queue.Empty:
                if model_manager.terminate_flag:
                    break
                continue

            file_path = os.path.join(images_directory, f"{image_name}.png")
            if os.path.exists(file_path) and not results.get('cover', False):
                results[image_name] = 'skipped'
                with task_lock:
                    completed_tasks[0] += 1
                task_queue.task_done()
                continue

            model_info = None
            while model_info is None and not model_manager.terminate_flag:
                model_info = model_manager.get_model()
                if model_info is None:
                    time.sleep(0.5)

            if model_manager.terminate_flag:
                break

            model_name = model_info['name']
            status = generate_image_thread(config, images_directory, model_manager, task_queue, results, prompt, image_name, model_name, kind)

            model_manager.release_model(model_name, status, completed_tasks, task_lock)
            task_queue.task_done()

            if status == 'success':
                with task_lock:
                    completed_tasks[0] += 1

            #print(f"Completed tasks: {completed_tasks[0]} / {total_tasks}")

        except Exception as e:
            print(f"Worker thread error: {e}")
            break

def parse_json_from_gpt_response(response):
    """Extract and parse the JSON array from GPT response"""
    if response == 'error' or not response:
        return None

    start = response.find('[')
    end = response.rfind(']')

    if start == -1 or end == -1 or end <= start:
        return None

    json_str = response[start:end+1]

    try:
        data = json.loads(json_str)

        for item in data:
            if not isinstance(item, dict) or 'name' not in item or 'prompt' not in item:
                return None

        return data
    except json.JSONDecodeError:
        return None

def main(prompt1, prompt2, kind, cover=0):
    """Main function to process image generation with threading and load balancing"""
    config = configparser.ConfigParser()
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    story_title = config.get('剧情', 'story_title')
    images_directory = os.path.join(game_directory, "data", story_title, "images")
    os.makedirs(images_directory, exist_ok=True)

    results = {'cover': bool(cover)}

    gpt_response = None
    id = random.randint(1, 100000)
    while True:
        try:
            gpt_response = gpt(prompt1, prompt2, kind,id)
            if gpt_response=='over_times':
                print("gpt 调用超出最大重试次数，生成失败")
                return "error"
            elif gpt_response and gpt_response != 'error':
                drawing_tasks = parse_json_from_gpt_response(gpt_response)
                if drawing_tasks:
                    gpt_destroy(id)
                    break
        except Exception as e:
            print(f"GPT call failed: {e}")
    seen_names = set()
    deduplicated_data = []
    for item in drawing_tasks:
        if item['name'] not in seen_names:
            seen_names.add(item['name'])
            deduplicated_data.append(item)
    drawing_tasks=deduplicated_data
    total_tasks = len(drawing_tasks)

    # 初始化已完成任务计数和互斥锁
    completed_tasks = [0]
    task_lock = threading.Lock()

    # 初始化模型管理器，传入总任务数
    model_manager = ModelManager(config, kind, total_tasks)

    # 创建任务队列
    task_queue = queue.Queue()

    # 将任务添加到队列
    for task in drawing_tasks:
        task_queue.put((task['prompt'], task['name']))

    # 创建并启动 worker 线程
    num_threads = min(100, task_queue.qsize())
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(
            target=worker,
            args=(config, images_directory, model_manager, task_queue, results, kind, completed_tasks, task_lock, total_tasks)
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)

    # 监控完成任务数量，并设置终止标志
    while completed_tasks[0] < total_tasks and not model_manager.terminate_flag:
        time.sleep(1)  # 每隔一秒检查一次

    # 设置terminate_flag，通知所有线程退出
    model_manager.terminate_flag = True

    # 等待所有线程完成
    for thread in threads:
        thread.join()

    #print("All worker threads have completed.")

    # 准备结果概要
    success_images = [name for name, status in results.items() if status == 'success' and name != 'cover']
    failed_images = [name for name, status in results.items() if status == 'failed' and name != 'cover']
    skipped_images = [name for name, status in results.items() if status == 'skipped' and name != 'cover']

    summary = {}
    if success_images:
        summary['success'] = success_images
    if failed_images:
        summary['failed'] = failed_images
    if skipped_images:
        summary['skipped'] = skipped_images

    return summary

def get_all_persons_images():
    config = configparser.ConfigParser()
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    story_title = config.get('剧情', 'story_title')
    prompt1,prompt2=process_prompt('全部人物绘画')
    result=main(prompt1,prompt2, 'character', 1)
    print(result)

def get_single_person_image(character):
    config = configparser.ConfigParser()
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    story_title = config.get('剧情', 'story_title')
    with open(rf"{game_directory}\data\{story_title}\temp_character.txt", 'w', encoding='utf-8') as outfile:
        outfile.write(character)
    with open(rf"{game_directory}\data\{story_title}\character.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        if item.get('name') == character:  
            prompt2=item
    with open(rf"{game_directory}\data\{story_title}\temp_character_info.txt", 'w', encoding='utf-8') as outfile:
        json.dump(prompt2, outfile, ensure_ascii=False, indent=4)
    prompt1,prompt2=process_prompt('单个人物绘画')
    os.remove(rf"{game_directory}\data\{story_title}\temp_character.txt")
    os.remove(rf"{game_directory}\data\{story_title}\temp_character_info.txt")
    result=main(prompt1,prompt2, 'character', 1)
    print(result)
def get_places_images():
    config = configparser.ConfigParser()
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    story_title = config.get('剧情', 'story_title')
    with open(rf"{game_directory}\data\{story_title}\place.json", 'r', encoding='utf-8') as f:
        place = f.read()
    if place=='[]':
        #print('没有新地点待生成')
        return
    prompt1,prompt2=process_prompt('故事地点绘画')
    result=main(prompt1,prompt2, 'background', 0)
    os.remove(rf"{game_directory}\data\{story_title}\place.json")
    print(result)
def get_end_places_images():
    config = configparser.ConfigParser()
    config.read(rf"{game_directory}\config.ini", encoding='utf-8')
    story_title = config.get('剧情', 'story_title')
    with open(rf"{game_directory}\data\{story_title}\place.json", 'r', encoding='utf-8') as f:
        place = f.read()
    if place=='[]':
        #print('没有新地点待生成')
        return
    prompt1,prompt2=process_prompt('结尾地点绘画')
    result=main(prompt1,prompt2, 'background', 0)
    print(result)
if __name__=="__main__":
    get_single_person_image('夏小悠')
    #get_single_person_image('李明')
    #get_places_images()
    get_all_persons_images()
