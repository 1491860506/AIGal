import requests
import json
import time
import os
import urllib3
import threading
import random
import re
import queue
import subprocess
import copy # Needed for deep copying model lists
from handle_prompt import process_prompt
from GPT import gpt, gpt_destroy

urllib3.disable_warnings()

try:
    import renpy
    game_directory = renpy.config.gamedir
except:
    game_directory = os.getcwd()


config_file = os.path.join(game_directory,"config.json")
_EVAL_FAILED = object()

def load_config():
    """Loads the configuration from the config.json file."""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Config file not found.")
        return {}
    except json.JSONDecodeError:
        print("Error decoding config.json.")
        return {}

# --- Placeholder Functions ---
def func1(status):
    """
    Placeholder function called after a failed generation attempt.
    Returns 1 to trigger prompt modification and task splitting,
    otherwise returns 0 to continue with normal retry logic.
    """
    if status!='error':
        return 1
    print("DEBUG: func1() called. Returning 0 (no split).") # Default behavior
    # import random
    # choice = random.choice([0, 1])
    # print(f"DEBUG: func1() returning {choice}.")
    # return choice
    return 0

def func2(original_prompt, image_name, model_name, attempt_number,kind):
    """
    Placeholder function called if func1 returns 1.
    Should return a new prompt string, or 'error' if modification fails.
    """
    prompt1,prompt2=process_prompt('重写提示词')
    prompt2=original_prompt
    id = random.randint(1, 100000)
    while True:
        try:
            gpt_response = gpt(prompt1, prompt2, kind,id)
            if gpt_response=='over_times':
                print("gpt 调用超出最大重试次数，生成失败")
                return "error"
            elif gpt_response and gpt_response != 'error':
                try:
                    match = re.search(r'"prompt":\s*"([^"]*)"', gpt_response)
                    if match:
                        gpt_destroy(id)
                        print(f"DEBUG: func2() called for {image_name} (attempt {attempt_number+1} with {model_name}) prompt:{match.group(1)}.")
                        return match.group(1)
                except:
                    pass
        except Exception as e:
            print(f"GPT call failed: {e}")
    return "error" # Default behavior


class ModelManager:
    """
    Manages AI drawing models with priority loading and CENTRALIZED concurrency tracking.
    """
    # Class variable to hold the global usage state, shared if needed, but instance is safer
    # Let's make it instance-based, assuming main_model_manager holds the true global state.
    # Sub-managers won't use their own global_model_usage directly for checks.

    def __init__(self, config, kind, total_tasks, main_manager_instance=None, is_sub_manager=False):
        self.config = config
        self.kind = kind
        self.all_priorities = None
        self.models = [] # List of model dicts for the CURRENT priority level {'name': str, 'weigh': float, 'priority': int}
        self.current_priority_index = 0
        self.terminate_flag = False # Flag to signal no more models available AT ALL
        self.lock = threading.RLock() # Lock for instance-specific state (models list, priority index)
        self.is_sub_manager = is_sub_manager
        self.total_tasks = total_tasks # Primarily for context

        # --- Central Concurrency State ---
        # The MAIN manager initializes this. Sub-managers will reference the main manager's state.
        self.main_manager_ref = main_manager_instance # Reference to the main manager (None if this IS the main manager)
        self._global_model_usage = {} # Only populated and directly used by the MAIN manager
        self._global_lock = threading.RLock() # Separate lock for the global usage dict

        if not self.is_sub_manager:
            # This is the main manager, initialize global state
            self._initialize_global_usage()
            self.main_manager_ref = self # Main manager references itself for consistency

        # Load models for the highest priority
        self.load_models_by_highest_priority()

    def _initialize_global_usage(self):
        """(Called only by Main Manager) Populates the global usage tracker."""
        print("Initializing Global Model Usage Tracker...")
        with self._global_lock:
            self._global_model_usage = {}
            all_model_configs = self.config.get("AI_draw", {}).get("configs", {})
            if not all_model_configs:
                 print("Warning: No 'configs' section found in AI_draw config for global usage tracking.")
                 return

            for model_name, model_conf in all_model_configs.items():
                max_c = 1 # Default concurrency
                try:
                    raw_max_c = model_conf.get("maxconcurrency")
                    if raw_max_c is not None and str(raw_max_c).strip():
                        max_c = int(raw_max_c)
                        if max_c < 0: max_c = 0 # Ensure non-negative
                except (ValueError, TypeError):
                    print(f"Warning: Invalid maxconcurrency '{raw_max_c}' for model '{model_name}'. Using default 1.")
                    max_c = 1

                self._global_model_usage[model_name] = {'max': max_c, 'current': 0}
            #print(f"Global Usage Initialized: {self._global_model_usage}")


    def load_models_by_highest_priority(self):
        """Load models with the highest priority available for this manager's kind."""
        with self.lock: # Lock instance state
            if self.all_priorities is None:
                # Determine available priorities for this 'kind'
                models_config_key = f'{self.kind}_config'
                models_config_list = self.config["AI_draw"].get(models_config_key)
                if not models_config_list:
                    print(f"Warning: No configuration found for key '{models_config_key}'")
                    self.terminate_flag = True
                    return False
                valid_models = [model for model in models_config_list if isinstance(model.get("priority"), int)]
                if not valid_models:
                     print(f"Warning: No models with valid integer priorities found in '{models_config_key}'")
                     self.terminate_flag = True
                     return False
                self.all_priorities = sorted(list(set(model["priority"] for model in valid_models)), reverse=True)

            if self.current_priority_index >= len(self.all_priorities):
                prefix = "Sub-Manager" if self.is_sub_manager else "Main Manager"
                print(f"{prefix}: No more priorities left to load.")
                self.terminate_flag = True
                return False

            target_priority = self.all_priorities[self.current_priority_index]

            # Filter models for the current target priority AND kind
            models_config_list = self.config["AI_draw"].get(f'{self.kind}_config', [])
            models_to_load_configs = [
                model_config for model_config in models_config_list
                if model_config.get("priority") == target_priority
            ]

            if not models_to_load_configs:
                # This priority level has no models for this 'kind'
                print(f"Manager ({'Sub' if self.is_sub_manager else 'Main'}): No models configured for priority {target_priority} and kind '{self.kind}'. Moving to next priority.")
                self.current_priority_index += 1
                return self.load_models_by_highest_priority() # Recursive call

            # Load the models for this priority (without instance-level concurrency)
            self.models = []
            for model_config in models_to_load_configs:
                model_name = model_config["config"]
                # Check if model exists in global config (it should)
                if self.main_manager_ref and model_name not in self.main_manager_ref._global_model_usage:
                     print(f"Warning: Model '{model_name}' listed in '{self.kind}_config' but not found in global configs. Skipping.")
                     continue

                model_data = {
                    'name': model_name,
                    'weigh': model_config.get("weigh", 1), # Default weight to 1
                    'priority': target_priority,
                }
                self.models.append(model_data)

            prefix = "Sub-Manager" if self.is_sub_manager else "Main Manager"
            if not self.models:
                print(f"{prefix}: No valid models found for priority {target_priority} after checks. Moving to next.")
                self.current_priority_index += 1
                return self.load_models_by_highest_priority() # Recursive call
            else:
                print(f"{prefix}: Loaded models for priority {target_priority}: {[model['name'] for model in self.models]}")
                return True

    def get_current_priority_value(self):
        """Returns the integer value of the current priority level, or None if invalid."""
        with self.lock:
            if self.all_priorities and 0 <= self.current_priority_index < len(self.all_priorities):
                return self.all_priorities[self.current_priority_index]
            return None

    def get_model(self):
        """
        Selects a model from the current priority based on weight,
        then checks global concurrency and acquires a slot if available.
        Moves to next priority ONLY if the current one has no models left AT ALL.
        """
        if self.is_sub_manager:
             # Sub-managers should not directly call this version; use can_split_task_use_model
             print("ERROR: Sub-manager attempted to call get_model directly. Use permission check flow.")
             return None

        # Only the main manager uses this method directly
        with self.lock: # Lock instance state (priority list)
            while not self.terminate_flag:
                if not self.models:
                    # Current priority level is empty, try loading next
                    print(f"Main Manager: No models left at priority {self.get_current_priority_value()}. Loading next...")
                    self.current_priority_index += 1
                    if not self.load_models_by_highest_priority():
                        return None # terminate_flag is now True
                    else:
                        continue # Loop again to check the newly loaded priority

                # --- Models exist at current priority, check global concurrency ---
                globally_available_models = []
                with self._global_lock: # Lock global state for checking
                    for model in self.models:
                        model_name = model['name']
                        usage = self._global_model_usage.get(model_name)
                        if usage and usage['current'] < usage['max']:
                            globally_available_models.append(model)

                if not globally_available_models:
                    # Models exist at this priority, but ALL are globally busy. Wait.
                    # print(f"DEBUG Main get_model: Models at prio {self.get_current_priority_value()} exist but globally busy. Waiting.")
                    return None # Signal wait to worker

                # --- Models available globally at this priority ---
                # Select based on weight among the available ones
                total_weight = sum(m.get('weigh', 1) for m in globally_available_models)
                selected_model_data = None

                if total_weight > 0:
                    probabilities = [(m.get('weigh', 1) / total_weight) for m in globally_available_models]
                    try:
                        selected_model_data = random.choices(globally_available_models, weights=probabilities, k=1)[0]
                    except (ValueError, IndexError) as e:
                         print(f"ERROR selecting weighted model: {e}. Available: {globally_available_models}, Probs: {probabilities}. Falling back.")
                         # Fallback to random choice among available
                         if globally_available_models:
                             selected_model_data = random.choice(globally_available_models)
                         else: # Should not happen if list wasn't empty, but check
                              return None # Cannot select
                elif globally_available_models: # Total weight 0 but models exist? Use random choice
                    print(f"WARN: Globally available models found, but total weight is 0. Using random choice. Models: {[m['name'] for m in globally_available_models]}")
                    selected_model_data = random.choice(globally_available_models)
                else: # No models were actually available
                    return None # Cannot select


                # --- Acquire global concurrency slot ---
                selected_name = selected_model_data['name']
                acquired = False
                with self._global_lock:
                    usage = self._global_model_usage.get(selected_name)
                    # Double-check concurrency as state might have changed between check and acquire
                    if usage and usage['current'] < usage['max']:
                        usage['current'] += 1
                        acquired = True
                        print(f"Main Manager Acquired: {selected_name} (Global Usage: {usage['current']}/{usage['max']})")
                    # else: Concurrency filled up between check and acquire - very unlikely but possible

                if acquired:
                    # Return a copy of the selected model's data (name, weight, priority)
                    return selected_model_data.copy()
                else:
                    # Failed to acquire slot (race condition?). Signal wait and retry.
                    print(f"WARN: Failed acquire lock for {selected_name} (race condition?). Retrying.")
                    # Don't advance priority, just let worker retry get_model
                    return None # Signal wait

            # End of while loop: terminate_flag is True
            return None


    def release_model(self, model_name, status):
        """
        (Called by Main Worker) Releases a model slot in the global tracker.
        Removes model from instance list ONLY if status indicates permanent failure.
        """
        if self.is_sub_manager:
             print("ERROR: Sub-manager called release_model. Use release_split_task_model.")
             return

        # --- Release global concurrency ---
        released_globally = False
        with self._global_lock:
            usage = self._global_model_usage.get(model_name)
            if usage:
                 if usage['current'] > 0:
                     usage['current'] -= 1
                     released_globally = True
                     print(f"Main Manager Released: {model_name} (Global Usage: {usage['current']}/{usage['max']})")
                 else:
                      print(f"WARN: Attempted to release {model_name} globally, but current usage was already 0.")
            # else: Model not in global tracker? Should not happen if initialized correctly.

        # --- Update instance model list if needed ---
        with self.lock:
            model_found_in_instance = False
            for i, model in enumerate(self.models):
                if model['name'] == model_name:
                    model_found_in_instance = True
                    if status == 'retry_over_times':
                        # Model failed all retries, remove it from this instance's current priority list
                        print(f"Main Manager: Model {model_name} removed from priority {model['priority']} due to exceeding retry limits.")
                        self.models.pop(i)
                        # No need to update possibilities as they are calculated on-the-fly in get_model
                    # else: status is 'success' or other, just keep the model in the list
                    break # Exit loop once model is found and handled

            if not model_found_in_instance and status == 'retry_over_times':
                 print(f"Warning: Main Manager tried to remove {model_name} on failure, but it wasn't found in current priority list (maybe already removed or priority changed).")

            # Check if the current priority level is now empty AFTER potential removal
            if not self.models:
                if self.current_priority_index < len(self.all_priorities):
                    print(f"Main Manager: All models from priority {self.all_priorities[self.current_priority_index]} exhausted or removed. Will load next on next get_model().")
                    # Let get_model handle loading next time it's called
                else:
                    # This case should be covered by get_model advancing index, but double-check
                    if not self.terminate_flag:
                         print(f"Main Manager: All models exhausted, setting terminate flag.")
                         self.terminate_flag = True


    def can_split_task_use_model(self, model_name_to_check, sub_manager_priority_value):
        """
        Checks if a split task is allowed to use a specific model based on main manager state
        AND global concurrency. Acquires global slot if permitted.

        Args:
            model_name_to_check: The name of the model the split task wants to use.
            sub_manager_priority_value: The current priority value of the requesting sub-manager.
            (Implicitly uses self.main_manager_ref for main manager state/locks)

        Returns:
            bool: True if the model can be used (and global concurrency was acquired), False otherwise.
        """
        if not self.main_manager_ref:
             print("ERROR: Main manager reference not set in can_split_task_use_model.")
             return False

        # Lock the MAIN manager's instance lock first to check its current models/priority
        with self.main_manager_ref.lock:
            main_model_info = None # Refers to model dict in main manager's self.models list
            for model in self.main_manager_ref.models:
                if model['name'] == model_name_to_check:
                    main_model_info = model
                    break

            main_current_priority_value = self.main_manager_ref.get_current_priority_value()

            # --- Perform Priority Check (Rule ①) ---
            if main_model_info is None:
                # Model NOT FOUND in main manager's CURRENT priority list
                if main_current_priority_value is None or sub_manager_priority_value is None:
                     print(f"Split Check Denied: Cannot compare priorities (None) for {model_name_to_check}.")
                     return False # Cannot proceed without priorities

                if sub_manager_priority_value < main_current_priority_value:
                    # Allowed based on priority rule, but MUST still check GLOBAL concurrency
                    print(f"Split Check Info: Priority check passed for {model_name_to_check} (SubPrio {sub_manager_priority_value} < MainPrio {main_current_priority_value}). Checking global concurrency...")
                    # Proceed to global concurrency check outside this lock block
                else:
                    # Denied by priority rule (Sub >= Main, model not in main's current list)
                    print(f"Split Check Denied: Priority condition unmet for {model_name_to_check} (SubPrio {sub_manager_priority_value} >= MainPrio {main_current_priority_value}, not in main list).")
                    return False # DENIED
            # else: Model FOUND in main manager's current list. Proceed to global concurrency check.

        # --- Perform Global Concurrency Check & Acquire ---
        # Lock the GLOBAL usage dict (part of main manager)
        with self.main_manager_ref._global_lock:
            usage = self.main_manager_ref._global_model_usage.get(model_name_to_check)
            if usage and usage['current'] < usage['max']:
                # Concurrency available! Acquire slot.
                usage['current'] += 1
                print(f"Split Task Acquired: {model_name_to_check} (Global Usage: {usage['current']}/{usage['max']})")
                return True # GRANTED
            else:
                # No global concurrency, even if priority check passed or model was in main list
                if usage:
                     print(f"Split Check Denied: Global concurrency full for {model_name_to_check} ({usage['current']}/{usage['max']}).")
                else:
                     print(f"Split Check Denied: Model {model_name_to_check} not found in global usage tracker.")
                return False # DENIED


    def release_split_task_model(self, model_name_released):
        """
        Releases a slot in the global concurrency tracker for a split task.

         Args:
            model_name_released: The name of the model being released.
            (Implicitly uses self.main_manager_ref for main manager state/locks)
        """
        if not self.main_manager_ref: return

        released_globally = False
        with self.main_manager_ref._global_lock:
            usage = self.main_manager_ref._global_model_usage.get(model_name_released)
            if usage:
                 if usage['current'] > 0:
                     usage['current'] -= 1
                     released_globally = True
                     print(f"Split Task Released: {model_name_released} (Global Usage: {usage['current']}/{usage['max']})")
                 else:
                      print(f"WARN: Split task attempted to release {model_name_released} globally, but usage was already 0.")
            # else: Model not in global tracker? Should not happen.


    def remove_current_priority_models(self, reason=""):
        """(Called by Sub-Manager usually) Removes all models from its own current priority list."""
        with self.lock: # Lock instance state
             current_priority = self.get_current_priority_value()
             if current_priority is not None:
                 print(f"Manager ({'Sub' if self.is_sub_manager else 'Main'}): Removing all models for its priority {current_priority}. Reason: {reason}")
                 self.models = [] # Clear the list for the current priority
                 # Immediately try to load the next priority for this instance
                 print(f"Manager ({'Sub' if self.is_sub_manager else 'Main'}): Attempting to load its next priority...")
                 self.current_priority_index += 1
                 self.load_models_by_highest_priority() # Will update instance terminate_flag if needed
             else:
                  print(f"Manager ({'Sub' if self.is_sub_manager else 'Main'}): Cannot remove models, no valid current priority.")


    def copy(self, main_manager_instance):
        """Creates a copy of this ModelManager for a split-off task."""
        with self.lock: # Ensure consistent state during copy
            print(f"DEBUG: Copying ModelManager state (current priority index: {self.current_priority_index}) for sub-task")
            # Create a new instance, passing reference to main manager
            new_manager = ModelManager(
                self.config,
                self.kind,
                1, # total_tasks = 1 for sub-manager context
                main_manager_instance=main_manager_instance,
                is_sub_manager=True
            )

            # Copy priority list if initialized
            new_manager.all_priorities = copy.deepcopy(self.all_priorities)

            # Deep copy the current list of model definitions (name, weigh, priority)
            new_manager.models = copy.deepcopy(self.models)

            # Copy the current priority index
            new_manager.current_priority_index = self.current_priority_index

            # Sub-manager starts active unless original is already terminated
            new_manager.terminate_flag = self.terminate_flag

            # No need to update possibilities as they are calculated on-the-fly
            # No need to set concurrency to 1 anymore

            print(f"DEBUG: Copied Sub-Manager created. Models: {[m['name'] for m in new_manager.models]}, Priority Index: {new_manager.current_priority_index}, Terminated: {new_manager.terminate_flag}")
            return new_manager






def getparams(config, model):
    """Retrieves parameters for a given model from the configuration."""
    model_config = config["AI_draw"]["configs"].get(model, {})
    if not model_config:
        print(f"Error: Configuration for model '{model}' not found.")
        # Return default/empty values to avoid crashing downstream
        return ("", "", {}, "", "", "", "", False, "", "", {}, "", "", "", "", 30, 15)

    def parse_headers(headers_list):
        try:
            headers_dict={}
            for header in headers_list:
                headers_dict[header[0]] = header[1]
            return headers_dict
        except Exception as e:
            print(f"Error gettinging headers string for {model}: {headers_list}. Error: {e}")
            return {}

    url1 = model_config.get("request_url", "")
    method1 = model_config.get("request_method", "GET")
    headers1 = parse_headers(model_config.get("headers", "{}"))
    body1 = model_config.get("request_body", "")
    path1 = model_config.get("json_path", "")
    success1 = model_config.get("success_condition", "")
    fail1 = model_config.get("fail_condition", "")
    forbid1=model_config.get("forbid_condition", "")
    userdefine1=model_config.get("userdefine", "")
    second_request = model_config.get("second_request", False)
    url2 = model_config.get("second_request_url", "")
    method2 = model_config.get("second_request_method", "GET")
    headers2 = parse_headers(model_config.get("second_headers", "{}"))
    body2 = model_config.get("second_request_body", "")
    path2 = model_config.get("second_json_path", "")
    success2 = model_config.get("second_success_condition", "")
    fail2 = model_config.get("second_fail_condition", "")
    forbid2 = model_config.get("second_forbid_condition", "")
    userdefine2=model_config.get("second_userdefine", "")

    # Get timeout parameters with defaults
    request_timeout = 30
    try:
        rt = model_config.get("request_timeout")
        if rt and str(rt).strip():
            request_timeout = int(rt)
    except (ValueError, TypeError):
        pass # Keep default

    second_request_timeout = 15
    try:
        srt = model_config.get("second_request_timeout")
        if srt and str(srt).strip():
            second_request_timeout = int(srt)
    except (ValueError, TypeError):
        pass # Keep default

    return (url1, method1, headers1, body1, path1, success1, fail1,forbid1,userdefine1,
            second_request, url2, method2, headers2, body2, path2, success2, fail2,forbid2,userdefine2,
            request_timeout, second_request_timeout)


def writefile(path, content):
    """Writes content to a file."""
    try:
        with open(path, 'wb') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing file {path}: {e}")
        return False

def getfile(path, url):
    """Downloads a file from a URL and saves it to a path."""
    try:
        response = requests.get(url, stream=True, timeout=60) # Add timeout and stream
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                 f.write(chunk)
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file from {url} to {path}: {e}")
        return False
    except Exception as e:
         print(f"Error saving downloaded file to {path}: {e}")
         return False

def safe_get_path(data, path_str):
    """
    Safely retrieves a value from nested data using a path string.

    Args:
        data: The dictionary or list to navigate.
        path_str: The path string, e.g., "['images'][0]['url']".

    Returns:
        The value found at the path, or None if the path is invalid,
        a key/index is missing, or the data structure is incompatible.
    """
    if not path_str or data is None:
        return None

    current_data = data
    try:
        # Regex to find content within [], handling single quotes, double quotes, or numbers
        # Example matches for "['images'][0]['url']": ('images', '', ''), ('', '', '0'), ('url', '', '')
        matches = re.findall(r"\[\s*(?:'([^']*)'|\"([^\"]*)\"|(\d+))\s*\]", path_str)
        if not matches:
            # Handle case where path_str might be a simple top-level key (though unlikely given user format)
            # If path_str is just 'key', not "['key']", this regex won't match.
            # If the user guarantees format is always [...]... then this isn't needed.
            # For now, assume the specified format is strict.
             print(f"Warning: Path '{path_str}' doesn't match expected format ['key'][index]...")
             return None


        keys = []
        for match in matches:
            # match is a tuple like ('key', '', '') or ('', "key", '') or ('', '', '0')
            key_or_index_str = next((item for item in match if item), None) # Find the non-empty group
            if key_or_index_str is None:
                print(f"Error: Could not parse key/index from match {match} in path {path_str}")
                return None # Path parsing failed

            try:
                # Try converting to int if it looks like a number (list index)
                keys.append(int(key_or_index_str))
            except ValueError:
                # Otherwise, it's a string key (dict key)
                keys.append(key_or_index_str)

        # Navigate the data structure
        for key in keys:
            if isinstance(key, int): # List index access
                if not isinstance(current_data, list) or not (0 <= key < len(current_data)):
                     # print(f"Debug safe_get_path: Index {key} out of bounds or not a list at path step.")
                     return None # Index out of bounds or not a list
                current_data = current_data[key]
            else: # Dictionary key access
                if not isinstance(current_data, dict) or key not in current_data:
                    # print(f"Debug safe_get_path: Key '{key}' not found or not a dict at path step.")
                    return None # Key not found or not a dict
                current_data = current_data[key]

        return current_data

    except Exception as e:
        # Catch any unexpected errors during parsing or access
        print(f"Error accessing path '{path_str}': {e}")
        return None
    

    
def evaluate_condition_safe(condition_str, response, result):
    if not condition_str:
        return False # Empty condition is considered false

    # Regex to parse "operand1 op operand2"
    match = re.match(r"^\s*(.+?)\s*(==|!=)\s*(.+?)\s*$", condition_str)
    if not match:
        print(f"Warning: Could not parse condition string: '{condition_str}'")
        return None # Cannot evaluate malformed condition

    left_str, op, right_str = match.groups()

    # --- Helper to evaluate a single operand string ---
    def evaluate_operand(operand_str):
        stripped = operand_str.strip()

        # 1. Check for response.status_code
        if stripped == 'response.status_code':
            return response.status_code if response is not None else _EVAL_FAILED

        # 2. Check for JSON path (starts with result[...], assuming result is the root)
        if stripped.startswith('result['): # Basic check, relies on safe_get_path robustness
            # Extract the path part, e.g., ['images'][0]['url'] from result['images'][0]['url']
            path = stripped[len('result'):]
            value = safe_get_path(result, path)
            return value if value is not None else _EVAL_FAILED # Return marker if path failed

        # 3. Check for literal string (quoted)
        if (stripped.startswith("'") and stripped.endswith("'")) or \
           (stripped.startswith('"') and stripped.endswith('"')):
            return stripped[1:-1] # Return content without quotes

        # 4. Check for literal number (int or float)
        try:
            return int(stripped)
        except ValueError:
            try:
                return float(stripped)
            except ValueError:
                pass # Not a number

        # 5. Check for literal boolean/None (optional, add if needed)
        # if stripped.lower() == 'true': return True
        # if stripped.lower() == 'false': return False
        # if stripped.lower() == 'none': return None

        # 6. If none of the above, treat as a plain literal string? Or error?
        # For safety, let's assume unquoted, non-numeric tokens might be errors unless specifically allowed.
        # However, the user spec implies literals or paths, so this case might indicate an issue.
        # Let's return _EVAL_FAILED for unknown operand types for now.
        print(f"Warning: Unrecognized operand format: '{stripped}' in condition '{condition_str}'")
        return _EVAL_FAILED

    # --- Evaluate both operands ---
    left_val = evaluate_operand(left_str)
    right_val = evaluate_operand(right_str)

    # --- Check if evaluation failed ---
    if left_val is _EVAL_FAILED or right_val is _EVAL_FAILED:
        # print(f"Debug: Condition '{condition_str}' failed evaluation due to operand issue.")
        return None # Cannot evaluate if path/operand failed

    # --- Perform comparison ---
    try:
        if op == '==':
            # print(f"Debug: Evaluating {left_val} == {right_val}")
            return left_val == right_val
        elif op == '!=':
            # print(f"Debug: Evaluating {left_val} != {right_val}")
            return left_val != right_val
        else:
            # Should not happen due to regex match
            return None
    except TypeError as e:
        # Handle comparison errors between incompatible types if necessary
        print(f"Warning: Type error during comparison in condition '{condition_str}': {e}. Operands: {type(left_val)}, {type(right_val)}")
        return None # Treat comparison type errors as unevaluable


def safe_b64decode(data):
    import base64
    import binascii
    """Safely decodes base64 data."""
    if data is None: return "error"
    try:
        # Ensure data is bytes or encode if string
        data_bytes = data if isinstance(data, bytes) else str(data).encode('utf-8')
        # Add padding if needed (common issue)
        missing_padding = len(data_bytes) % 4
        if missing_padding:
            data_bytes += b'='* (4 - missing_padding)
        return base64.b64decode(data_bytes)
    except (binascii.Error, TypeError, ValueError) as e:
        print(f"Error decoding base64: {e}")
        return "error"

def direct(data):
    if data!="":
        return data
    return "error"
USERDEFINE_FUNCTION_MAP = {
    "b64decode": safe_b64decode,
    "direct": direct,
    # "anotherName": another_function,
}

# --- Userdefine Processor ---
def process_userdefine(userdefine_str, response, parsed_result, extracted_result):
    """
    Processes the userdefine string using function mapping.

    Args:
        userdefine_str: The string from config (e.g., "b64decode(result['path'])").
        response: The relevant requests.Response object.
        parsed_result: The parsed JSON dictionary/list from the response.
        extracted_result: The result obtained by applying the regular path (path1/path2)
                          before userdefine was called (can be None).

    Returns:
        Processed data or the string "error".
    """
    if not userdefine_str or not isinstance(userdefine_str, str):
        return "error" # Invalid input

    # Regex to parse "function_name(argument_str)"
    match = re.match(r"^\s*(\w+)\s*\(\s*(.+)\s*\)\s*$", userdefine_str)
    if not match:
        print(f"Error: Could not parse userdefine string format: '{userdefine_str}'")
        return "error"

    func_name, arg_str = match.groups()
    arg_str = arg_str.strip() # Clean argument string

    # --- Evaluate Argument ---
    argument_value = None
    if arg_str == 'result':
        # Use the pre-extracted result (from path1 or path2)
        argument_value = extracted_result # Might be None if path failed
    elif arg_str.startswith('result['):
        # Extract path using safe_get_path from the parsed JSON
        path_part = arg_str[len('result'):]
        argument_value = safe_get_path(parsed_result, path_part) # Handles None parsed_result
    elif arg_str == 'response.text' or arg_str == 'text':
        # Use the raw response text
        argument_value = response.text if response is not None else None
    elif arg_str == 'response.content' or arg_str == 'content':
        argument_value = response.content if response is not None else None
    else:
        # Argument is not a recognized keyword/pattern
        print(f"Error: Unrecognized argument '{arg_str}' in userdefine string.")
        return "error"

    # Check if argument evaluation failed
    if argument_value is None:
         print(f"Error: Failed to evaluate argument '{arg_str}' (value is None).")
         return "error"

    # --- Look up and Call Function ---
    if func_name in USERDEFINE_FUNCTION_MAP:
        target_function = USERDEFINE_FUNCTION_MAP[func_name]
        try:
            print(f"DEBUG: Calling userdefine function '{func_name}'...")
            processed_data = target_function(argument_value)
            # Check if the mapped function itself returned an error signal
            if processed_data == "error":
                 print(f"Error: Mapped function '{func_name}' signalled an internal error.")
                 return "error"
            return processed_data
        except Exception as e:
            print(f"Error executing mapped function '{func_name}': {e}")
            return "error"
    else:
        print(f"Error: Function name '{func_name}' not found in USERDEFINE_FUNCTION_MAP.")
        return "error"



def generate(config, images_directory, prompt, image_name, model):
    """Generates an image based on the given prompt and model. Returns 'success' or 'error'."""
    randomseed = str(random.randint(1, 100000000))
    params = getparams(config, model)
    if not params[0]: # Check if URL1 is empty (indicates config loading error)
         return "error"

    url1, method1, headers1, body1, path1, success1, fail1, forbid1,userdefine, second_request, url2, method2, headers2, body2, path2, success2, fail2,forbid2,second_userdefine, request_timeout, second_request_timeout = params
    file_path = os.path.join(images_directory, f"{image_name}.png")

    # Prepare request 1 payload (same as before)
    prompt_placeholder = "{prompt}"; random_placeholder = "{random}"
    url1 = url1.replace(prompt_placeholder, prompt).replace(random_placeholder, randomseed)
    body1_str = str(body1).replace(prompt_placeholder, prompt).replace(random_placeholder, randomseed)
    body1_encoded = body1_str.encode('utf-8') if isinstance(body1, str) and 'json' not in headers1.get('Content-Type','').lower() else body1_str

    # --- First request --- (same logic)
    response = None
    try:
        print(f"DEBUG: Request 1 for {image_name} ({model}) - {method1} {url1}")
        if method1 == 'POST':
            # Decide encoding based on headers (crude check)
            if 'application/json' in headers1.get('Content-Type', '').lower():
                 response = requests.post(url1, headers=headers1, data=body1_encoded, timeout=request_timeout, verify=False)
            else:
                 # Assume form data or other; Requests handles dict data correctly for forms
                 # If body1 was originally a dict, eval might be needed, but getparams handles str -> dict for headers only
                 # Let's assume body1 from config is intended as raw string or JSON string
                 response = requests.post(url1, headers=headers1, data=body1_encoded, timeout=request_timeout, verify=False)
        elif method1 == 'GET':
            response = requests.get(url1, headers=headers1, timeout=request_timeout, verify=False)
        else:
            print(f"Error: Unsupported method {method1} for model {model}")
            return "error"
        response.raise_for_status()
    except requests.exceptions.Timeout: return "error" # Simplified error returns
    except requests.exceptions.RequestException as e: print(f"Req1 Err: {e}"); return "error"
    except Exception as e: print(f"Req1 Unexpected Err: {e}"); return "error"

    # --- Process response 1 ---
    result1 = None; response_text = response.text
    try: result1 = json.loads(response_text)
    except json.JSONDecodeError: result1 = None # Continue, maybe userdefine uses text

    # Evaluate fail condition 1
    fail1_met = evaluate_condition_safe(fail1, response, result1)
    if fail1_met is True: print(f"Req1 FailCond: {fail1}"); return "error"

    forbid1_met = evaluate_condition_safe(forbid1, response, result1)
    if forbid1 and forbid1_met is True: # If condition exists and is explicitly False
        print(f"提示词违禁")
        return "forbid"


    intermediate_result = None
    if path1: 
        intermediate_result = safe_get_path(result1, path1)

    # --- Process First Userdefine ---
    userdefine_processed_output = None
    if userdefine and userdefine.strip():
        print(f"DEBUG: Processing userdefine: {userdefine}")
        userdefine_processed_output = process_userdefine(
            userdefine, response, result1, intermediate_result
        )
        if userdefine_processed_output == "error":
            print(f"Error processing userdefine '{userdefine}'. Task failed.")
            return "error"

        # Use the output based on second_request flag
        if not second_request:
            # Save output directly
            print("DEBUG: Saving output from userdefine (no second request).")
            if isinstance(userdefine_processed_output, bytes):
                if writefile(file_path, userdefine_processed_output):
                    return "success"
                else:
                    print("Write userdefine output err"); return "error"
            else:
                print("Error: userdefine output for direct save was not bytes.")
                return "error"
        else:
            # Output modifies the intermediate result for request 2 formatting
            print("DEBUG: Using userdefine output as intermediate result for request 2.")
            intermediate_result = userdefine_processed_output # Overwrite intermediate_result
            # Continue to Request 2 setup

    # --- Handle case with NO second request (and no userdefine processed its output) ---
    elif not second_request:
        # This block runs only if userdefine didn't run OR if it ran but second_request was True
        # We need the original logic if no userdefine ran and second_request is False
        success1_met = evaluate_condition_safe(success1, response, result1)
        if success1 and success1_met is False: print(f"Req1 SuccCond Fail (JSON): {success1}"); return "error"

        if intermediate_result is None and path1 != "direct":
            print(f"Error: Path1 '{path1}' failed, cannot get image URL.")
            return "error"

        if isinstance(intermediate_result, str) and intermediate_result.startswith(('http://', 'https://')):
            if getfile(file_path, intermediate_result): return "success"
            else: print("Download fail"); return "error"
        else:
            # Only applicable if path1 wasn't 'direct' and didn't yield a URL
            if path1 != "direct":
                print(f"Error: Path1 '{path1}' did not yield URL. Result: {intermediate_result}")
                return "error"
            # If path1 was 'direct', it should have been handled earlier (unless userdefine ran)
            # If userdefine ran and second_request was False, it was handled above.
            # This path seems less likely now, but keep for robustness? Maybe just log warning.
            print(f"Warning: Unexpected state in no-second-request block after path1='{path1}'.")
            return "error" # Assume error if logic reaches here unexpectedly


    # --- Prepare for second request (if second_request is True) ---
    if intermediate_result is None and not (userdefine and userdefine.strip()):
        # If userdefine didn't run and path1 failed
        print(f"Error evaluating intermediate path '{path1}' for Request 2. Check JSON structure and path.")
        return "error"

    # Format Request 2 URL and Body using the potentially modified intermediate_result
    result_placeholder = "{result}"
    # Ensure intermediate_result is string for replacements
    intermediate_result_str = str(intermediate_result) if intermediate_result is not None else ""
    url2_formatted = str(url2).replace(result_placeholder, intermediate_result_str)
    body2_str = str(body2).replace(result_placeholder, intermediate_result_str)
    body2_encoded = body2_str.encode('utf-8') if isinstance(body2, str) and 'json' not in headers2.get('Content-Type','').lower() else body2_str

    # --- Second request loop ---
    max_poll_attempts = 60; poll_interval = 1
    for attempt in range(max_poll_attempts):
        response2 = None
        try:
            # print(f"DEBUG: Request 2 for {image_name}, attempt {attempt+1} - {method2} {url2_formatted}")
            if method2 == 'GET':
                response2 = requests.get(url2_formatted, headers=headers2, timeout=second_request_timeout, verify=False)
            elif method2 == 'POST':
                 if 'application/json' in headers2.get('Content-Type', '').lower():
                     response2 = requests.post(url2_formatted, headers=headers2, data=body2_encoded, timeout=second_request_timeout, verify=False)
                 else:
                     response2 = requests.post(url2_formatted, headers=headers2, data=body2_encoded, timeout=second_request_timeout, verify=False)
            else:
                print(f"Error: Unsupported method {method2} for second request (model {model})")
                return "error"

            response2.raise_for_status()
        except requests.exceptions.Timeout:
            if attempt == max_poll_attempts - 1: print("Req2 Timeout"); return "error"
            time.sleep(poll_interval); continue
        except requests.exceptions.RequestException as e: print(f"Req2 Err: {e}"); return "error"
        except Exception as e: print(f"Req2 Unexpected Err: {e}"); return "error"

        # --- Process response 2 ---
        result2 = None; response_text2 = response2.text
        try: result2 = json.loads(response_text2)
        except json.JSONDecodeError: result2 = None # Continue, maybe userdefine uses text

        # Evaluate fail condition 2
        fail2_met = evaluate_condition_safe(fail2, response2, result2)
        if fail2_met is True: print(f"Req2 FailCond: {fail2}"); return "error"

        forbid2_met = evaluate_condition_safe(forbid2, response, result1)
        if forbid2 and forbid2_met is True: # If condition exists and is explicitly False
            print(f"提示词违禁")
            return "forbid"

        # --- Process Second Userdefine ---
        second_userdefine_processed_output = None
        final_extracted_result = None # Extract path2 result first in case userdefine needs it
        if path2:
             final_extracted_result = safe_get_path(result2, path2)

        if second_userdefine and second_userdefine.strip():
            print(f"DEBUG: Processing second_userdefine: {second_userdefine}")
            second_userdefine_processed_output = process_userdefine(
                second_userdefine, response2, result2, final_extracted_result
            )
            if second_userdefine_processed_output == "error":
                print(f"Error processing second_userdefine '{second_userdefine}'. Task failed.")
                return "error"

            # Save output directly
            print("DEBUG: Saving output from second_userdefine.")
            if isinstance(second_userdefine_processed_output, bytes):
                if writefile(file_path, second_userdefine_processed_output): return "success"
                else: print("Write second_userdefine output err"); return "error"
            else:
                print("Error: second_userdefine output was not bytes.")
                return "error"
            # If second_userdefine runs, it's the end of the process for this request cycle


        # Check success condition 2 (for JSON path result)
        success2_met = evaluate_condition_safe(success2, response2, result2)
        if success2 and success2_met is True: # Only proceed if condition exists AND is True
             if final_extracted_result is None:
                 print(f"Error: Path2 '{path2}' failed, cannot get image URL.")
                 return "error"

             if isinstance(final_extracted_result, str) and final_extracted_result.startswith(('http://', 'https://')):
                 if getfile(file_path, final_extracted_result): return "success"
                 else: print("Download fail (Req2)"); return "error"
             else:
                 print(f"Error: Path2 '{path2}' did not yield URL. Result: {final_extracted_result}")
                 return "error"

        # If not failed and success condition not met/doesn't exist, continue polling
        time.sleep(poll_interval)
        # Loop continues

    # If loop finishes without returning success or error
    print(f"Error: Req2 polling failed after {max_poll_attempts} attempts.")
    return "error"


def generate_debug(config, images_directory, prompt, image_name, model):
    # This function remains largely the same, just ensure it calls the updated generate()
    # Or copy the detailed print statements from the original generate_debug if needed.
    # For simplicity now, let's assume generate() has enough debug prints.
    print(f"--- Starting DEBUG Generation for {image_name} using {model} ---")
    status = generate(config, images_directory, prompt, image_name, model)
    print(f"--- Finished DEBUG Generation for {image_name} using {model} - Status: {status} ---")
    return status

def rembg(config, images_directory, image_name, kind,model):
    """Removes the background from an image with timeout and retry."""
    if kind != 'character':
        return "pass" # Only process characters

    file_path = os.path.join(images_directory, f"{image_name}.png")
    if not os.path.exists(file_path):
        print(f"Error: Cannot rembg {image_name}, file not found.")
        return "error"

    processing_config = config["AI_draw"].get("processing_config", {})
    rembg_enabled = config["AI_draw"]["configs"].get(model, {}).get("use_rembg", False) # Check model specific override (Need model name here - refactor needed)
    # *** Problem: rembg function doesn't know which model generated the image ***
    # *** Quick Fix: Assume if processing_config["use_rembg"] is true, we should run it. ***
    # *** Better Fix: Pass model name to rembg, or check file metadata, or restructure flow. ***
    # For now, use the global flag:
    if not rembg_enabled:
         #print(f"DEBUG: Rembg skipped for {image_name} (globally disabled).")
         return "pass"


    rembg_url = processing_config.get("rembg_location", "http://localhost:7000/api/remove")
    rembg_model = processing_config.get("rembg_model", "isnet-anime")

    data = {
        "model": rembg_model,
        "a": "true",
        "af": 240 # Ensure af is also a string
    }

    rembg_timeout = processing_config.get("rembg_timeout", 15) 


    try:
        print(f"DEBUG: Attempting rembg for {image_name} ...")
        with open(file_path, 'rb') as file:
            files = {'file': (f"{image_name}.png", file)}
            response = requests.post(rembg_url, files=files, data=data, timeout=rembg_timeout, verify=False)

        if response.status_code == 200:
            # Overwrite the original file with the rembg result
            if writefile(file_path, response.content):
                print(f"DEBUG: rembg successful for {image_name}.")
                return "success"
            else:
                print(f"Error: Failed to write rembg result for {image_name}.")
                # Treat write failure as an error for this attempt
        else:
            print(f"Error: rembg request failed for {image_name}, status code: {response.status_code}. Response: {response.text[:200]}")

    except requests.exceptions.Timeout:
        print(f"Error: rembg timed out for {image_name}  after {rembg_timeout}s.")
    except requests.exceptions.RequestException as e:
        print(f"Error: rembg connection error for {image_name}: {e}")
    except Exception as e:
        print(f"Error: rembg unexpected error for {image_name}: {e}")


    print(f"Error: rembg processing failed for {image_name}")
    return "error"


def check_image_size(config, images_directory, image_name, kind):
    """Checks if the generated image meets basic quality/size criteria."""
    file_path = os.path.join(images_directory, f"{image_name}.png")
    if not os.path.exists(file_path):
        print(f"Warning: Quality check skipped for {image_name}, file not found.")
        return False # Cannot check non-existent file


    if config["AI_draw"]["judging_config"].get(f"{kind}_quality_judgment", False):
        print(f"DEBUG: Performing external quality judgment for {image_name} ({kind})...")
        method = config["AI_draw"]["judging_config"].get("selected_method", "a")
        methods_config = config["AI_draw"]["judging_config"].get("methods", {})
        method_params = methods_config.get(method, {})
        threshold_str = method_params.get(f"{kind}_quality_threshold", "10") # Default threshold as string

        try:
            threshold = float(threshold_str)
        except ValueError:
            print(f"Warning: Invalid quality threshold '{threshold_str}' for {kind}, using default 10.")
            threshold = 10.0

        # Define target dimensions based on kind (could also be configurable)
        width = 1024 if kind == "character" else 1920
        height = 1024 if kind == "character" else 1080

        resize_exe_path = os.path.join(game_directory, "resize.exe")
        if not os.path.exists(resize_exe_path):
             print(f"Error: resize.exe not found at {resize_exe_path}. Skipping external quality check.")
             return True # Skip check if tool is missing


        command = [
            resize_exe_path,
            f"method_{method}", # Function name in resize.exe
            file_path,
            str(width),
            str(height),
            method # Pass method name as parameter if needed by the exe
        ]

        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            timeout_seconds = config["AI_draw"]["judging_config"].get("judgment_timeout", 60)

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False, # Don't raise exception for non-zero exit code (score)
                creationflags=creationflags,
                timeout=timeout_seconds
            )

            # Assume the score is returned as the exit code
            score = float(result.returncode)
            print(f"DEBUG: Quality score for {image_name} ({kind}, method {method}): {score}")

            if score < threshold:
                print(f"Quality Check Failed: {image_name} ({kind}) score {score} is below threshold {threshold}.")
                # os.remove(file_path) # Optionally remove low-quality files
                return False
            else:
                print(f"DEBUG: Quality check passed for {image_name}.")

        except subprocess.TimeoutExpired:
            print(f"Error: Quality judgment timed out for {image_name} after {timeout_seconds}s.")
            return False # Treat timeout as failure
        except ValueError:
            print(f"Error: Quality judgment for {image_name} returned non-numeric exit code: {result.returncode}")
            return False # Treat invalid score as failure
        except Exception as e:
            print(f"Error running quality judgment tool for {image_name}: {e}")
            # Decide whether to treat tool error as pass or fail. Let's be strict: fail.
            return False

    # If all checks passed or were skipped
    return True


def resize_image_strategy(image_path,target_width,target_height,strategy):
    command = [
        os.path.join(game_directory,"resize.exe"),
        "resize_image_strategy",  # The function name
        image_path,
        str(target_width),      # Convert numbers to strings
        str(target_height),     # Convert numbers to strings
        strategy
    ]
    creationflags = subprocess.CREATE_NO_WINDOW
    result = subprocess.run(
        command,
        capture_output=False,
        text=False, # Decode output as text (strings)
        check=False,   # Raise exception if return code is non-zero
        creationflags=creationflags
    )


    return True  # Successfully executed


def generate_image_thread(config, images_directory, prompt, image_name, model_name, kind, allow_split=True):
    """
    Thread function to generate a single image using a specific model, with retries and conditional splitting.

    Args:
        config: Configuration dictionary.
        images_directory: Path to save images.
        prompt: The generation prompt.
        image_name: The base name for the output image file.
        model_name: The name of the model config to use.
        kind: 'character' or 'background'.
        allow_split: Boolean indicating if this attempt is allowed to trigger a split.

    Returns:
        'success': Image generated, processed, and passed checks.
        'failed_model': All retries with *this model* failed.
        ('split', new_prompt): Task should be split off (new_prompt can be original or modified).
    """
    model_config = config["AI_draw"]["configs"].get(model_name, {})
    retry_count = 1
    try:
        rc = model_config.get("max_attempts", 1)
        if rc and str(rc).strip():
            retry_count = int(rc)
    except (ValueError, TypeError): pass # Keep default

    delay_time = 1
    try:
        dt = model_config.get("delay_time", 1)
        if dt and str(dt).strip():
             delay_time = int(dt)
    except (ValueError, TypeError): pass # Keep default

    check_image_times=0
    current_prompt = prompt # Keep track of potentially modified prompt

    for i in range(retry_count):
        print(f"Attempt {i+1}/{retry_count} for {image_name} using model {model_name}...")
        status = generate(config, images_directory, current_prompt, image_name, model_name)

        if status == 'success':
            # --- Post-generation processing ---
            # 1. Rembg (only for characters and if enabled)
            rembg_status = "pass"

            if kind == 'character':
                rembg_status = rembg(config, images_directory, image_name, kind,model_name)

            if rembg_status == "error":
                print(f'rembg failed for {image_name} on attempt {i+1}. Treating as generation failure.')
                status = "rembg_error" # Mark generation as failed if rembg failed
            else:
                if check_image_size(config, images_directory, image_name, kind):
                    resize_success = True
                    try:
                        processing_conf = config["AI_draw"].get("processing_config", {})
                        resize_strategy = processing_conf.get(f"{kind}_resize")
                        target_resolution=processing_conf.get(f"{kind}_resolution")

                        if target_resolution and resize_strategy:
                            if kind =="background":
                                target_width= 1920
                                target_height= 1080
                            else:
                                target_width=int(1024*int(config["AI_draw"]["processing_config"]["character_width"])/int(config["AI_draw"]["processing_config"]["character_height"]))
                                target_height = 1024
                            # Map strategy names
                            strategy_map = {"裁剪": "crop", "填充": "pad", "拉伸": "stretch"}
                            strategy_en = strategy_map.get(resize_strategy, resize_strategy) # Use English if mapped, else original

                            image_path = os.path.join(images_directory, f"{image_name}.png")
                            if not resize_image_strategy(image_path, target_width, target_height, strategy_en):
                                print(f"Warning: Resizing failed for {image_name}. Keeping original.")
                                resize_success = False # Indicate resize failure if needed downstream
                                # Decide if resize failure should fail the whole process. Currently, it doesn't.

                    except Exception as e:
                        print(f"Error during resize step for {image_name}: {e}")
                        resize_success = False # Indicate resize failure

                    # If resize was successful (or not needed) -> Final Success
                    print(f'{image_name} successfully generated and processed with model {model_name}.')
                    return 'success'
                else:
                    check_image_times=check_image_times+1
                    if check_image_times==2:
                        status='cheak_error'
                        
                    else:
                        print(f'{image_name} failed quality check on attempt {i+1}.')
                        status = 'error' # Mark as error if quality check fails

        # --- Handle Failure ---
        if status!= 'success':
            print(f'Failed attempt {i+1}/{retry_count} for {image_name} with model {model_name}.')

            # --- Check for Split Condition ---
            if allow_split:
                # print(f"DEBUG: Checking func1 for {image_name} after failed attempt {i+1}")
                split_trigger = func1(status)
                if split_trigger == 1:
                    print(f"DEBUG: func1 returned 1 for {image_name}. Calling func2...")
                    new_prompt_or_error = func2(original_prompt=prompt, image_name=image_name, model_name=model_name, attempt_number=i,kind=kind)
                    if new_prompt_or_error != "error":
                        print(f"DEBUG: func2 provided new prompt for {image_name}. Triggering split.")
                        return ('split', new_prompt_or_error) # Return split signal with new prompt
                    else:
                        print(f"DEBUG: func2 returned 'error' for {image_name}. Triggering split with original prompt.")
                        return ('split', prompt) # Return split signal with original prompt
                # else:
                #     print(f"DEBUG: func1 returned 0. Continuing retry logic for {image_name}.")

            # If not splitting, wait before next retry (if any)
            if i < retry_count - 1:
                print(f"Waiting {delay_time}s before next attempt...")
                time.sleep(delay_time)
            # Continue to the next iteration of the retry loop

    # If loop completes without success or splitting
    print(f"All {retry_count} attempts failed for {image_name} with model {model_name}.")
    return 'failed_model' # Signal that this model failed all its attempts


def split_task_worker(config, images_directory, sub_model_manager, main_model_manager, initial_prompt, image_name, kind, split_task_results, split_management_lock):
    """
    Worker thread dedicated to a single split-off task.
    Uses sub_model_manager internally, checks permission & global concurrency via main_model_manager.
    """
    print(f"--- Starting Split Task Worker for: {image_name} ---")
    task_prompt = initial_prompt
    task_successful = False
    global_concurrency_acquired = False # Track if main concurrency was acquired for the *current* model attempt
    current_model_name = None      # Track name of model currently being processed

    while not sub_model_manager.terminate_flag:
        global_concurrency_acquired = False # Reset for each attempt to get a model
        current_model_name = None

        # 1. Get a candidate model from the SUB-manager's internal list/priority
        #    This get_model call inside sub-manager is now simplified - it just selects
        #    based on current priority/weight without internal concurrency check.
        #    We need a slightly different internal getter for sub-managers or adapt get_model.
        #    Let's adapt get_model temporarily for sub-managers - it shouldn't check global lock itself.
        #    --- Let's refine this: Sub-managers need a way to select a candidate. ---

        # --- Revised way for sub-manager to get a candidate ---
        candidate_model_data = None
        with sub_model_manager.lock: # Lock the sub-manager instance
             if not sub_model_manager.models:
                 # Sub-manager's current priority list is empty. Try loading next.
                 print(f"Sub-Manager ({image_name}): No models left at priority {sub_model_manager.get_current_priority_value()}. Loading next...")
                 sub_model_manager.current_priority_index += 1
                 if not sub_model_manager.load_models_by_highest_priority():
                      # Sub-manager has no more priorities, it's terminated
                      print(f"Sub-Manager ({image_name}): Terminated, no more models/priorities.")
                      break # Exit the while loop
                 else:
                      continue # Loop again to try the new priority

             # Models exist at current priority for sub-manager. Select based on weight.
             current_sub_models = sub_model_manager.models
             total_weight = sum(m.get('weigh', 1) for m in current_sub_models)
             if total_weight > 0:
                 probabilities = [(m.get('weigh', 1) / total_weight) for m in current_sub_models]
                 try:
                     candidate_model_data = random.choices(current_sub_models, weights=probabilities, k=1)[0]
                 except (ValueError, IndexError): # Fallback
                     if current_sub_models: candidate_model_data = random.choice(current_sub_models)
             elif current_sub_models: # Fallback if weight sum is 0
                  candidate_model_data = random.choice(current_sub_models)

             # If no candidate could be selected (list empty after all)
             if candidate_model_data is None:
                  print(f"Sub-Manager ({image_name}): Could not select candidate model from current list. Retrying.")
                  time.sleep(0.1) # Small delay
                  continue # Try again

        # --- End of revised candidate selection ---

        candidate_model_name = candidate_model_data['name']
        current_model_name = candidate_model_name # Track for release
        sub_prio_val = sub_model_manager.get_current_priority_value() # Get sub's current priority value

        # 2. Check permission and acquire GLOBAL concurrency via MAIN manager
        can_use = main_model_manager.can_split_task_use_model(
            candidate_model_name,
            sub_prio_val # Pass sub-manager's current priority value
        )
        global_concurrency_acquired = can_use # Track if permission involved taking main concurrency

        # 3. Handle Permission Result
        if can_use:
            # --- Permission Granted & Global Concurrency Acquired ---
            print(f"Split task {image_name}: Granted use of {candidate_model_name} (SubPrio: {sub_prio_val}). Proceeding.")

            # Call generate_image_thread
            status = generate_image_thread(config, images_directory, task_prompt, image_name, candidate_model_name, kind, allow_split=False)

            # Release GLOBAL concurrency back to MAIN manager
            # (release_split_task_model handles the check if it was acquired via global state)
            main_model_manager.release_split_task_model(candidate_model_name)
            global_concurrency_acquired = False # Mark as released

            # Update model state in SUB-manager (remove if failed permanently)
            sub_release_status = 'success' if status == 'success' else 'retry_over_times'
            # Need to lock sub-manager to modify its state safely
            with sub_model_manager.lock:
                model_found_in_sub = False
                for i, model in enumerate(sub_model_manager.models):
                     if model['name'] == candidate_model_name:
                          model_found_in_sub = True
                          if sub_release_status == 'retry_over_times':
                              print(f"Sub-Manager ({image_name}): Removing failed model {candidate_model_name} from its list.")
                              sub_model_manager.models.pop(i)
                          break # Found it
                if not model_found_in_sub and sub_release_status == 'retry_over_times':
                     print(f"WARN Sub-Manager ({image_name}): Tried to remove {candidate_model_name} on failure, but not found (priority likely changed).")
                # Check if sub-manager's current priority is now empty
                if not sub_model_manager.models:
                     print(f"Sub-Manager ({image_name}): Current priority list empty. Will load next on next attempt.")


            # Finalize task status
            if status == 'success':
                with split_management_lock:
                    split_task_results[image_name] = 'success'
                task_successful = True
                print(f"--- Split Task Worker SUCCESS for: {image_name} ---")
                break # Task completed successfully
            else: # status == 'failed_model'
                print(f"Split task {image_name}: Model {candidate_model_name} failed generation. Sub-manager updated. Trying next candidate.")
                # Loop continues to get next candidate from sub-manager
                continue

        else:
            # --- Permission Denied by main_manager.can_split_task_use_model ---
            print(f"Split task {image_name}: Denied use of {candidate_model_name} by main manager check (Priority or Global Concurrency).")

            # Determine reason for denial based on main manager state (for sub-manager actions)
            model_exists_in_main_list = False
            main_prio_val = None
            global_concurrency_available = False # Check explicitly

            # Check main manager state again (briefly locking)
            with main_model_manager.lock: # Lock main instance state
                main_prio_val = main_model_manager.get_current_priority_value()
                for m in main_model_manager.models:
                    if m['name'] == candidate_model_name:
                        model_exists_in_main_list = True
                        break
            with main_model_manager._global_lock: # Lock global state
                 usage = main_model_manager._global_model_usage.get(candidate_model_name)
                 if usage and usage['current'] < usage['max']:
                      global_concurrency_available = True

            # Apply removal logic to SUB-manager based on denial reason
            if not model_exists_in_main_list and not global_concurrency_available:
                 # Model not in main list AND global concurrency maybe full or model unknown globally
                 # Check priority rule (Rule ① denial reason)
                 if sub_prio_val is not None and main_prio_val is not None:
                     if sub_prio_val > main_prio_val:
                          print(f"Split task ({image_name}): Instructing sub-manager to remove its priority {sub_prio_val} (> main {main_prio_val}).")
                          sub_model_manager.remove_current_priority_models(reason=f"Priority {sub_prio_val} > Main Priority {main_prio_val}")
                     elif sub_prio_val == main_prio_val:
                          print(f"Split task ({image_name}): Instructing sub-manager to remove model {candidate_model_name} (== main prio, not in main list).")
                          # Lock sub-manager to remove model
                          with sub_model_manager.lock:
                              for i, m in enumerate(sub_model_manager.models):
                                   if m['name'] == candidate_model_name:
                                        sub_model_manager.models.pop(i)
                                        break
                     # else sub_prio < main_prio (This case should have passed permission check if global concurrency was available)
                     # If it failed here, it must be global concurrency issue. Fall through to wait.

                 else: # Cannot compare priorities
                      print(f"Split task ({image_name}): Cannot compare priorities (None). Waiting.")
                      time.sleep(0.5) # Wait

            elif model_exists_in_main_list and not global_concurrency_available:
                 # Reason: Model exists in main list, but global concurrency=0 (Rule ② denial)
                 print(f"Split task ({image_name}): Denial reason: Global concurrency=0 for {candidate_model_name}. Waiting.")
                 time.sleep(0.5) # Wait briefly for main manager state/global concurrency to potentially change
            elif not model_exists_in_main_list and global_concurrency_available:
                 # Reason: Priority rule ① denial (Sub >= Main, not in main list), even though global concurrency exists
                 print(f"Split task ({image_name}): Denial reason: Priority rule unmet for {candidate_model_name} (SubPrio {sub_prio_val} >= MainPrio {main_prio_val}, not in main list). Applying removal rules.")
                 if sub_prio_val is not None and main_prio_val is not None:
                     if sub_prio_val > main_prio_val:
                         sub_model_manager.remove_current_priority_models(reason=f"Priority {sub_prio_val} > Main Priority {main_prio_val}")
                     elif sub_prio_val == main_prio_val:
                         with sub_model_manager.lock:
                             for i, m in enumerate(sub_model_manager.models):
                                 if m['name'] == candidate_model_name:
                                     sub_model_manager.models.pop(i)
                                     break
                 else: # Cannot compare
                      time.sleep(0.5)
            else:
                 # Other unexpected denial reason?
                 print(f"Split task ({image_name}): Unexpected denial state for {candidate_model_name}. Waiting.")
                 time.sleep(0.5)


            # Loop continues to get next candidate from sub-manager
            continue

    # --- After the loop ---
    if not task_successful:
        with split_management_lock:
            if image_name not in split_task_results:
                split_task_results[image_name] = 'failed'
        print(f"--- Split Task Worker FAILED for: {image_name} (Sub-manager exhausted or could not get permission) ---")

    # Cleanup: Ensure main concurrency released if loop exited unexpectedly while holding it
    if global_concurrency_acquired and current_model_name:
        print(f"WARN: Split task {image_name} exiting loop unexpectedly while holding global concurrency for {current_model_name}. Releasing...")
        main_model_manager.release_split_task_model(current_model_name)

    # print(f"DEBUG: Split task worker for {image_name} finishing.")


def worker(config, images_directory, main_model_manager, task_queue, results, kind, completed_tasks, task_lock, total_tasks, active_managers, split_task_results, split_threads, split_management_lock):
    """Worker thread processing tasks from the main queue, using CENTRALIZED concurrency."""
    while True:
        current_task = None
        acquired_main_concurrency = False # Track if this worker holds main concurrency
        current_model_name = None      # Track model name for release

        try:
            # Get a task from the main queue
            prompt, image_name = task_queue.get(block=True, timeout=0.5)
            current_task = (prompt, image_name)

            file_path = os.path.join(images_directory, f"{image_name}.png")
            if os.path.exists(file_path) and not results.get('cover', False):
                # print(f"Skipping {image_name}: File already exists.") # Can be noisy
                with task_lock:
                    results[image_name] = 'skipped'
                    completed_tasks[0] += 1
                task_queue.task_done()
                continue

            # --- Task requires generation ---
            task_successful_or_split = False
            while not task_successful_or_split:
                acquired_main_concurrency = False # Reset for each model attempt
                current_model_name = None

                # Get an available model from the main manager (checks global concurrency)
                model_info = main_model_manager.get_model() # This now handles global check & acquire

                if model_info is None:
                    # Check if terminated or just waiting for global concurrency
                    if main_model_manager.terminate_flag:
                        print(f"Worker: Main model manager terminated. Cannot process task {image_name}.")
                        # Mark task done to avoid deadlock, main loop handles final failure assessment
                        task_queue.task_done()
                        # Ensure results dict reflects failure if not already set
                        with task_lock:
                             if results.get(image_name) not in ['success', 'skipped']:
                                  results[image_name] = 'failed_no_models'
                        break # Exit inner loop for this task
                    else:
                        # Waiting for global concurrency, sleep briefly
                        time.sleep(0.5)
                        continue # Retry getting a model

                # --- Model acquired from Main Manager ---
                current_model_name = model_info['name']
                acquired_main_concurrency = True # get_model already acquired it globally
                print(f"Worker: Processing {image_name} with acquired model {current_model_name} (Priority {model_info['priority']})")

                # Attempt to generate the image
                status = generate_image_thread(config, images_directory, prompt, image_name, current_model_name, kind, allow_split=True)

                if isinstance(status, tuple) and status[0] == 'split':
                    # --- Handle Split ---
                    split_prompt = status[1]
                    print(f"Worker: Splitting task {image_name} off...")
                    sub_model_manager = None # Define before with block
                    with split_management_lock:
                        # Create sub-manager (copy passes main manager ref implicitly via self)
                        sub_model_manager = main_model_manager.copy(main_model_manager)
                        if not sub_model_manager:
                             print(f"Error: Failed to copy ModelManager for split task {image_name}. Aborting split.")
                             # Release the model used by the *original* worker back to main manager
                             main_model_manager.release_model(current_model_name, 'failed_model') # Release original attempt
                             acquired_main_concurrency = False # Mark as released
                             continue # Continue trying other models for the original task

                        # REMOVED: No longer need to initialize sub-manager concurrency to 1

                        active_managers.append(sub_model_manager) # Add to list of managers to monitor

                        # Create and start the dedicated thread for the split task
                        split_thread = threading.Thread(
                            target=split_task_worker,
                            args=(config, images_directory, sub_model_manager, # Pass sub-manager
                                  main_model_manager, # Pass main manager
                                  split_prompt, image_name, kind,
                                  split_task_results, split_management_lock),
                            name=f"SplitWorker-{image_name}"
                        )
                        split_thread.daemon = True
                        split_threads.append(split_thread)
                        split_thread.start()

                    # Release the global concurrency used by the *original* worker thread's failed attempt
                    print(f"Worker: Releasing main concurrency for {current_model_name} after splitting off {image_name}.")
                    main_model_manager.release_model(current_model_name, 'success') # Release as success since split handles it now
                    acquired_main_concurrency = False # Mark as released

                    task_successful_or_split = True # Mark original task as handled (by splitting)
                    task_queue.task_done() # Mark the original task item from queue as done

                elif status == 'success':
                    # --- Handle Success ---
                    main_model_manager.release_model(current_model_name, 'success') # Release global concurrency
                    acquired_main_concurrency = False
                    with task_lock:
                        results[image_name] = 'success'
                        completed_tasks[0] += 1
                    task_successful_or_split = True
                    task_queue.task_done()

                elif status == 'failed_model':
                    # --- Handle Model Failure ---
                    print(f"Worker: Model {current_model_name} failed permanently for {image_name}. Trying next model.")
                    # Release the model, signaling it exhausted retries (removes from list, releases global concurrency)
                    main_model_manager.release_model(current_model_name, 'retry_over_times')
                    acquired_main_concurrency = False
                    # Loop continues within the `while not task_successful_or_split:` block
                    # to get the *next* available model from the main_model_manager for the *same* task.

            # End of inner while loop (task succeeded, split, or main manager terminated for task)

        except queue.Empty:
            # Queue is empty, check if we should terminate worker thread
            with split_management_lock:
                 all_terminated = all(m.terminate_flag for m in active_managers if m) # Check all active managers
            if all_terminated:
                 # print("DEBUG: Worker exiting - Queue empty and all managers terminated.")
                 break # Exit worker loop
            else:
                 # Keep worker alive to wait for split tasks or priority changes
                 continue

        except Exception as e:
            print(f"!!! Worker thread error: {e} !!!")
            # Release concurrency if held
            if acquired_main_concurrency and current_model_name:
                 print(f"Worker error: Releasing held concurrency for {current_model_name}")
                 main_model_manager.release_model(current_model_name, 'error') # Release concurrency on error
                 acquired_main_concurrency = False
            # Handle task outcome
            if current_task:
                 print(f"Error processing task {current_task}, marking as done/failed.")
                 task_queue.task_done() # Mark done to prevent block
                 with task_lock:
                      if results.get(current_task[1]) not in ['success', 'skipped']:
                          results[current_task[1]] = 'worker_error'
                      completed_tasks[0]+=1 # Count as handled for progress
            # Decide whether to break or continue worker thread
            # Let's continue for now, but might need review
            # break

    # print(f"DEBUG: Worker thread terminating.")


def parse_json_from_gpt_response(response):
    """Extract and parse the JSON array from GPT response"""
    if response == 'error' or not response:
        print("Error: GPT response is empty or error.")
        return None

    # Be more robust finding the JSON array
    match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
    if not match:
        print("Error: Could not find JSON array structure in GPT response.")
        print(f"GPT Response Snippet: {response[:500]}")
        return None

    json_str = match.group(0)

    try:
        data = json.loads(json_str)

        # Validate structure
        if not isinstance(data, list):
            print("Error: Parsed JSON is not a list.")
            return None
        if not data: # Handle empty list case
            print("Warning: GPT returned an empty list of tasks.")
            return []

        validated_data = []
        for item in data:
            if not isinstance(item, dict):
                print(f"Error: Item in JSON list is not a dictionary: {item}")
                return None
            if 'name' not in item or 'prompt' not in item:
                print(f"Error: Dictionary item missing 'name' or 'prompt': {item}")
                return None
            # Basic sanitization (optional, but good practice)
            item['name'] = str(item['name']).strip()
            item['prompt'] = str(item['prompt']).strip()
            if not item['name']:
                 print(f"Warning: Item has empty name, skipping: {item}")
                 continue
            validated_data.append(item)

        return validated_data
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from GPT response: {e}")
        print(f"Extracted JSON String: {json_str}")
        return None
    except Exception as e:
        # Catch other potential errors during validation/sanitization
        print(f"Error processing parsed JSON data: {e}")
        return None


def main(prompt1, prompt2, kind, cover=0):
    """Main function to process image generation with threading, load balancing, and task splitting."""
    config = load_config()
    if not config:
        print("Failed to load config. Exiting.")
        return {"error": "Config load failed"}

    story_title = config.get("剧情", {}).get("story_title", "default_story")
    images_directory = os.path.join(game_directory, "data", story_title, "images")
    os.makedirs(images_directory, exist_ok=True)

    # Shared state for main tasks
    results = {'cover': bool(cover)} # Tracks success/failure/skip for originally queued tasks
    completed_tasks = [0] # Counter for main tasks completed/skipped/split
    task_lock = threading.Lock() # Lock for completed_tasks counter and results dict

    # Shared state for split tasks and manager tracking
    active_managers = [] # List to hold the main manager and all sub-managers
    split_task_results = {} # Stores final status ('success'/'failed') of split tasks {image_name: status}
    split_threads = [] # Holds thread objects for split_task_worker
    split_management_lock = threading.Lock() # Lock for active_managers, split_task_results, split_threads

    print("--- Requesting Task List from GPT ---")
    gpt_response = None
    drawing_tasks = None


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
    print(drawing_tasks)



    # --- Deduplicate tasks by name (last occurrence wins if names collide) ---
    seen_names = {}
    for item in drawing_tasks:
        seen_names[item['name']] = item # Overwrite earlier items with the same name
    deduplicated_data = list(seen_names.values())
    print(f"Received {len(drawing_tasks)} tasks, {len(deduplicated_data)} unique tasks after deduplication.")
    drawing_tasks = deduplicated_data
    total_tasks = len(drawing_tasks)

    if total_tasks == 0:
        print("No unique tasks to process after deduplication.")
        return {"success": [], "failed": [], "skipped": []}


    print(f"--- Initializing Main Model Manager for {total_tasks} tasks ---")
    # Initialize the main ModelManager (it initializes global state)
    # Pass None for main_manager_instance as it IS the main one
    main_model_manager = ModelManager(config, kind, total_tasks, main_manager_instance=None, is_sub_manager=False)
    with split_management_lock:
        active_managers.append(main_model_manager)

    # Create the main task queue
    task_queue = queue.Queue()

    # Add tasks to the queue
    print("--- Adding Tasks to Queue ---")
    for task in drawing_tasks:
        # Sanitize prompt minimally (allow common punctuation)
        clean_prompt = re.sub(r"[^a-zA-Z,.\(\)\[\]\{\}: _\|]", "", task['prompt'])
        # Fallback name if needed
        task_name = task['name'] if task.get('name') else f"unnamed_task_{random.randint(1000,9999)}"
        task_queue.put((clean_prompt, task_name))
        # Initialize result status for tracking (important for skipped logic)
        results[task_name] = 'pending'


    # --- Start Worker Threads ---
    # Determine number of threads (e.g., based on total concurrency potential or a fixed cap)
    # Simple approach: Use a fixed cap or base it on initial queue size
    max_threads = config["AI_draw"].get("max_worker_threads", 10) # Configurable max threads
    num_threads = min(max_threads, task_queue.qsize())
    if num_threads <=0 : num_threads = 1 # Ensure at least one thread if tasks exist

    print(f"--- Starting {num_threads} Worker Threads ---")
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(
            target=worker,
            args=(config, images_directory, main_model_manager, task_queue, results, kind, completed_tasks, task_lock, total_tasks,
                  active_managers, split_task_results, split_threads, split_management_lock),
            name=f"Worker-{i+1}"
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)

    # --- Monitoring Loop ---
    print("--- Monitoring Progress ---")
    while True:
        with task_lock:
            main_completed_count = completed_tasks[0]
        with split_management_lock:
            split_results_count = len(split_task_results)
            tasks_accounted_for = main_completed_count + split_results_count # Includes main successes, skips, splits + split results

            # Check if all *potentially active* managers are terminated
            all_managers_terminated = all(m.terminate_flag for m in active_managers)
            active_split_threads = [t for t in split_threads if t.is_alive()]
            # print(f"DEBUG Loop: Main Completed: {main_completed_count}, Split Results: {split_results_count}, Accounted: {tasks_accounted_for}/{total_tasks}, All Mgrs Term: {all_managers_terminated}, Active Split Thr: {len(active_split_threads)}")


        # Condition 1: All tasks are accounted for (either succeeded, failed, or skipped)
        if tasks_accounted_for >= total_tasks:
            print("--- All tasks accounted for. Finishing up. ---")
            break

        # Condition 2: All managers are terminated *and* the main queue is empty *and* no split threads are running
        # This indicates that remaining tasks cannot be completed.
        if all_managers_terminated and task_queue.empty() and not active_split_threads:
             if tasks_accounted_for < total_tasks:
                  print("--- All models exhausted across all managers, queue empty, splits finished, but not all tasks accounted for. Assuming remaining failed. ---")
             else:
                  # This case should be caught by condition 1, but good to have
                  print("--- All models exhausted, queue empty, splits finished, and all tasks accounted for. ---")
             break # Exit monitoring loop


        time.sleep(2) # Check progress every 2 seconds


    # --- Cleanup and Final Summary ---
    print("--- Waiting for threads to complete ---")
    # Signal termination? Not strictly needed with daemon threads, but good practice?
    # main_model_manager.terminate_flag = True # Signal main manager? It might already be set.
    # How to signal sub-managers? They terminate naturally when out of models.

    # Wait for main worker threads to finish (they should exit when queue is empty and managers are done)
    # for thread in threads:
    #     thread.join(timeout=10) # Add timeout to join

    # Wait for split threads to finish
    # for thread in split_threads:
    #     thread.join(timeout=10)

    # Wait a bit longer for file operations etc.
    time.sleep(2)
    print("--- All threads should have completed. Compiling results. ---")


    # Consolidate results
    final_summary = {'success': [], 'failed': [], 'skipped': []}
    processed_names = set() # Keep track of names handled by split results

    # Add split results first
    with split_management_lock:
        for name, status in split_task_results.items():
            if status == 'success':
                final_summary['success'].append(name)
            else:
                final_summary['failed'].append(name)
            processed_names.add(name)

    # Add results from the main worker pool (only if not already handled by split)
    with task_lock:
        for name, status in results.items():
            if name == 'cover' or name in processed_names:
                continue # Skip cover flag and already processed split tasks

            if status == 'success':
                final_summary['success'].append(name)
            elif status == 'skipped':
                 final_summary['skipped'].append(name)
            elif status == 'pending' or status == 'worker_error' or status == 'failed_no_models':
                 # Tasks that never finished successfully or were skipped
                 final_summary['failed'].append(name)
            # Note: We don't have an explicit 'failed' status from the main results dict alone
            # Failure is inferred if it wasn't success/skipped and wasn't handled by a split task

    # Ensure all original task names are accounted for if they never reached success/skip/split failure
    all_original_names = {task['name'] for task in drawing_tasks}
    accounted_names = set(final_summary['success']) | set(final_summary['failed']) | set(final_summary['skipped'])
    missing_names = all_original_names - accounted_names
    if missing_names:
        print(f"Warning: The following tasks were never resolved: {missing_names}. Marking as failed.")
        final_summary['failed'].extend(list(missing_names))


    print("--- Final Summary ---")
    print(f"Successful: {len(final_summary['success'])}")
    if final_summary['success']: print(f"  {final_summary['success']}")
    print(f"Failed: {len(final_summary['failed'])}")
    if final_summary['failed']: print(f"  {final_summary['failed']}")
    print(f"Skipped: {len(final_summary['skipped'])}")
    if final_summary['skipped']: print(f"  {final_summary['skipped']}")

    return final_summary

def get_all_persons_images():
    config = load_config()
    prompt1,prompt2=process_prompt('全部人物绘画')
    result=main(prompt1,prompt2, 'character', 1)
    print(result)

def get_single_person_image(character):
    config = load_config()
    story_title = config["剧情"]["story_title"]
    with open(os.path.join(game_directory,"data",story_title,"temp_character.txt"), 'w', encoding='utf-8') as outfile:
        outfile.write(character)
    with open(os.path.join(game_directory,"data",story_title,"character.json"), 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        if item.get('name') == character:  
            prompt2=item
    with open(os.path.join(game_directory,"data",story_title,"temp_character_info.txt"), 'w', encoding='utf-8') as outfile:
        json.dump(prompt2, outfile, ensure_ascii=False, indent=4)
    prompt1,prompt2=process_prompt('单个人物绘画')
    os.remove(os.path.join(game_directory,"data",story_title,"temp_character.txt"))
    os.remove(os.path.join(game_directory,"data",story_title,"temp_character_info.txt"))
    result=main(prompt1,prompt2, 'character', 1)
    print(result)
def get_places_images(cover=0):
    config = load_config()
    story_title = config["剧情"]["story_title"]
    with open(os.path.join(game_directory,"data",story_title,"story","place.json"), 'r', encoding='utf-8') as f:
        place = f.read()
    if place=='[]':
        return
    prompt1,prompt2=process_prompt('故事地点绘画')
    result=main(prompt1,prompt2, 'background', cover)
    #os.remove(rf"{game_directory}\data\{story_title}\story\place.json")
    print(result)

if __name__=="__main__":
    get_single_person_image('夏小悠')
    #get_single_person_image('李明')
    #get_places_images()
    get_all_persons_images()
