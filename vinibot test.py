import time
import re
import traceback
import threading
import random
import string
import pygame
from collections import deque
from openai import OpenAI
from pathlib import Path
from queue import Queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

ai_model = None

SHUTDOWN_PASSWORD = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
print(f"Shutdown password: {SHUTDOWN_PASSWORD}")

MAX_TOKENS = 100
CONTEXT_LINES_COUNT = 10
MULTILINE_DELAY = 1

LOG_PATH = r'C:\Users\vini2\AppData\Roaming\Mindustry\last_log.txt'
WELCOME_PLAYERS_PATH = r'welcome_players.txt'
INSTRUCTIONS_PATH = r'C:\Users\vini2\PycharmProjects\vinibot\instructions.txt'
API_KEY_PATH = r'C:\Users\vini2\OneDrive\Dokumente\API_KEY.txt'
RESPONSES_FILE = r'C:\Users\vini2\PycharmProjects\vinibot\response_log.txt'
WINDOWS_STARTUP = r'windows-xp-startup.mp3'

context_lines = deque(maxlen=CONTEXT_LINES_COUNT)

pygame.mixer.init()

class CustomAIModel:
    def __init__(self, api_key, instructions_path):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-4o-mini"
        self.base_instructions = self.load_instructions(instructions_path)

    def load_instructions(self, instructions_path):
        try:
            with open(instructions_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except (FileNotFoundError, Exception):
            return ""

    def get_response(self, question, context=None):
        if context is None:
            context = []
        messages = [
            {"role": "system", "content": self.base_instructions},
            {"role": "user", "content": question}
        ]

        if context:
            context_message = {"role": "system", "content": "\n".join(context)}
            messages.insert(1, context_message)

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error getting response: {e}")
            return ""

def initialize_ai_model():
    global ai_model
    with open(API_KEY_PATH, 'r', encoding='utf-8') as file:
        api_key = file.read().strip()
    ai_model = CustomAIModel(api_key, INSTRUCTIONS_PATH)

def send_instructions():
    if not ai_model.base_instructions:
        print("No instructions loaded.")
        return

last_response = None

def send_message_to_chatgpt(question, context):
    global last_response
    assistant_response = ai_model.get_response(question, context)

    if assistant_response.lower().startswith("vinibot:"):
        assistant_response = assistant_response[len("vinibot:"):].strip()

    if assistant_response == last_response:
        assistant_response += "‌"

    last_response = assistant_response

    prefix = ("[#40FD40]")  # Prefix toggle

    print("R:", assistant_response)

    patterns_to_scrub = ["<> Vinibot: ", "<> Vinibot: ", "<> Vinibot: "]
    cleaned_response = assistant_response
    for pattern in patterns_to_scrub:
        cleaned_response = cleaned_response.replace(pattern, "")
    cleaned_response = cleaned_response.strip()

    response_lines = cleaned_response.split('\n')
    for i, line in enumerate(response_lines):
        if line.strip():
            log_message_to_file(f"{prefix}{line.strip()}")
            if i < len(response_lines) - 1:
                time.sleep(MULTILINE_DELAY)

def log_message_to_file(message):
    try:
        patterns_to_scrub = ["<> Vinibot: ", "<> Vinibot: ", "<> Vinibot: "]
        cleaned_message = message
        for pattern in patterns_to_scrub:
            cleaned_message = cleaned_message.replace(pattern, "")
        cleaned_message = cleaned_message.strip()

        if cleaned_message:
            with open(RESPONSES_FILE, 'a', encoding='utf-8') as file:
                file.write(cleaned_message + "\n")
    except Exception as e:
        print(f"Error logging message: {e}")

def clean_chat_log(line):
    return line.replace("[I] [Chat] ", "").strip()

shutting_off_message = "[#f]Shutting off"

def detect_vinibot_questions(file_path):
    global running
    running = True
    vinibot_pattern = re.compile(r'^hey vinibot\b', re.IGNORECASE)
    connected_pattern = re.compile(r'has connected', re.IGNORECASE)
    received_world_data_pattern = re.compile(r'Received world data', re.IGNORECASE)

    with open(file_path, 'r', encoding='utf-8') as file:
        file.seek(0, 2)

        while running:
            line = file.readline()
            if not line:
                time.sleep(0.1)
                continue

            if '[Chat]' in line:
                cleaned_line = clean_chat_log(line.strip())
                context_lines.append(cleaned_line)

                parts = line.split(":", 1)
                if len(parts) > 1:
                    username_part = parts[0].strip()
                    message_part = parts[1].strip()

                    if (
                        vinibot_pattern.match(message_part)
                        and 'vinibot' not in username_part.lower()
                    ):
                        question = line.replace("[I] [Chat] ", "").strip()
                        print(f"Q: {question}")
                        send_message_to_chatgpt(message_part, list(context_lines))

                if connected_pattern.search(line):
                    for welcome_player in load_list_from_file(WELCOME_PLAYERS_PATH):
                        if welcome_player.lower() in line.lower():
                            welcome_message = f"[gold]Hello, {welcome_player}!"
                            log_message_to_file(welcome_message)
                            break

            elif received_world_data_pattern.search(line):
                log_message_to_file("[gold]Hello there")

def load_list_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file if line.strip()]
    except (FileNotFoundError, Exception):
        return []

def startup():
    online_message = ("[#40FD40]ViniBot is online")
    initialize_ai_model()
    send_instructions()
    pygame.mixer.music.set_volume(0.2)
    pygame.mixer.music.load(WINDOWS_STARTUP)
    pygame.mixer.music.play()
    time.sleep(1)
    print(online_message)
    log_message_to_file(online_message)

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if event.src_path.endswith("welcome_players.txt") or event.src_path.endswith("instructions.txt"):
            self.callback()

def monitor_file_changes(callback):
    event_handler = FileChangeHandler(callback)
    observer = Observer()
    observer.schedule(event_handler, path=Path(WELCOME_PLAYERS_PATH).parent, recursive=False)
    observer.start()
    return observer

def reload_files():
    global ai_model
    print("Reloading files...")
    ai_model.base_instructions = ai_model.load_instructions(INSTRUCTIONS_PATH)
    print("Files reloaded.")

def main():
    try:
        startup()
        observer = monitor_file_changes(reload_files)
        detect_vinibot_questions(LOG_PATH)
    except KeyboardInterrupt:
        print("Script stopped by user.")
        log_message_to_file(shutting_off_message)
    finally:
        observer.stop()
        observer.join()
        with open(RESPONSES_FILE, 'w', encoding='utf-8') as file:
            file.write('')

if __name__ == "__main__":
    main()
