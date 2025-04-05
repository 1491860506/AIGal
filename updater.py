import os
import sys
import zipfile
import shutil
import subprocess
import time
import psutil

def kill_processes(process_name,app_dir):
    """Kills all processes with the given name that are in given app"""
    count = 0
    for proc in psutil.process_iter(['pid', 'name','exe']):
      # Get full path, also compare path for the applications
        if proc.info['name'] == process_name and os.path.dirname(proc.info['exe'])==app_dir:  # Compare name and folder
            try:
                p = psutil.Process(proc.info['pid'])

                #Different Method to kill: first SIGTERM, then SIGKILL
                p.kill()
                p.wait(2) #wait 5 sec for it to close
                if p.is_running():
                  p.kill()
                  p.wait(2)

                print(f"Killed process: {process_name} (PID: {proc.info['pid']})")
                count+=1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.Error) as e:
                print(f"Could not kill process {process_name} (PID: {proc.info['pid']}). Error: {e}")
    return count

def extract_and_restart(zip_file_path, game_directory):
    """Extracts zip and restarts the application"""
    try:
        app_dir = game_directory
        dest_dir = os.path.dirname(app_dir)
        extract_dir = dest_dir

        # Preservation list
        app_name = os.path.basename(app_dir+".exe").replace(".exe","")#to name.exe
        count = kill_processes(app_name,app_dir)  # or use a constant
        print(f"killed {count} main app processes" )
        
        preserve_files = ["config.json", "data","saves","snap","test"]

        # Build absolute preserve paths
        abs_preserve_paths = [os.path.join(app_dir, file) for file in preserve_files if os.path.exists(os.path.join(app_dir, file))]

         # Handle preservation files
        for item in preserve_files:
            item_path = os.path.join(app_dir, item)
            if os.path.isdir(item_path):
                path_list = [os.path.join(root, file)
                        for root, _, files in os.walk(item_path)
                        for file in files]
                abs_preserve_paths.extend(path_list)

        print("app directory", app_dir)
        print("destination directory", dest_dir)
        print("These absolute path should be kept", abs_preserve_paths)
                 # Kill main app processes (before extraction)
        app_name = os.path.basename(app_dir)
        count = kill_processes(app_name)  # or use a constant
        print(f"killed {count} main app processes")

        # Extract all and skip preserve
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                extracted_path = os.path.join(extract_dir, member.filename)
                if os.path.isdir(extracted_path): continue
                if extracted_path in abs_preserve_paths:
                     print(f"Skipping extraction (preserve):  {extracted_path}")
                else:
                    try:
                        zip_ref.extract(member,  extract_dir)   # extracts members on root level # does not protect agains deletion
                        print(f"extraction success:  {extracted_path}")

                    except Exception as ex:
                        print("extraction error")
                        print(ex)
        #Remove
        os.remove(zip_file_path)
        print("completed extraction")

        # Start game
        python = sys.executable # Get new value
        os.chdir(app_dir)
        os.execl(python, python, *sys.argv)

    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to exit...") # Pause to allow user to see the error
if __name__ == "__main__":

    # Argument Parsing
    if len(sys.argv) != 3:
        print("Usage: updater.exe <zip_file_path> <game_directory>")
        input("Press Enter to exit...")
        sys.exit(1)

    zip_file_path = sys.argv[1]
    game_directory = sys.argv[2]
    # Wait for main program to close

    print(f"Start process..")
    extract_and_restart(zip_file_path, game_directory)
