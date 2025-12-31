
import threading
from queue import Queue
from core.speech import jarvis_speak 
import random
import json
import logging
import datetime
from core.memory import retrieve_memory, store_memory, get_conversation_history, delete_memory, set_preference, get_preference, retrieve_all_memories
from services.weather import get_weather
from services.system import run_remote_command
from config.settings import MAIN_PC_USER, MAIN_PC_IP
from core.speech import get_available_microphones 
import sys
import subprocess
import socket
import sqlite3
import time
import speech_recognition as sr
import asyncio
import edge_tts
import tempfile
import os
from core.speech import recognizer
from core.scheduler import scheduler
from core.scheduler import add_reminder

speech_queue = Queue()

def speech_worker():
    while True:
        text = speech_queue.get()
        if text is None:
            break
        jarvis_speak(text, "info")
        speech_queue.task_done()

threading.Thread(target=speech_worker, daemon=True).start()

def check_context(command):
    if not command or command in ["exit", "quit", "power down", "shut down jarvis"]:
        return None
    history = get_conversation_history(limit=5)
    for entry in history:
        if entry["command"] and command == entry["command"]:
            if any(keyword in command for keyword in ["what is", "tell me about", "what's on my", "what do you know", "weather"]):
                return f"I noticed you recently asked about {command}."
    return None

def add_to_list(list_name, item):
    list_key = f"{list_name}_list"
    current_list = retrieve_memory(list_key)
    if current_list:
        try:
            current_list = json.loads(current_list)
        except json.JSONDecodeError:
            logging.error(f"Failed to parse list JSON for key={list_key}")
            current_list = {"type": "list", "items": [], "timestamp": datetime.datetime.now().isoformat()}
    else:
        current_list = {"type": "list", "items": [], "timestamp": datetime.datetime.now().isoformat()}
    if item not in current_list["items"]:
        current_list["items"].append(item)
        store_memory(list_key, json.dumps(current_list))
        jarvis_speak(f"{item} has been added to your {list_name} list.", "confirmation")
    else:
        jarvis_speak(f"{item} is already in your {list_name} list.", "info")

def read_list(list_name):
    list_key = f"{list_name}_list"
    current_list = retrieve_memory(list_key)
    if current_list:
        try:
            current_list = json.loads(current_list)
            items = ', '.join(current_list["items"])
            jarvis_speak(f"Your {list_name} list includes {items}.", "info")
        except json.JSONDecodeError:
            logging.error(f"Failed to parse list JSON for key={list_key}")
            jarvis_speak(f"I encountered an issue reading your {list_name} list, sir.", "error")
    else:
        jarvis_speak(f"You don't have a {list_name} list yet.", "info")

def list_memories():
    all_memories = retrieve_all_memories()
    if all_memories:
        response = "I have stored: "
        for key, value in all_memories.items():
            try:
                data = json.loads(value)
                if data["type"] == "simple":
                    response += f"{key.replace('my', 'your')} is {data['value']}, "
                elif data["type"] == "list":
                    items = ', '.join(data["items"])
                    response += f"your {key.replace('_list', '')} list includes {items}, "
                elif data["type"] == "reminders":
                    items = ', '.join([f"{item['task']} at {item['time']}" for item in data["items"]])
                    response += f"your reminders include {items}, "
            except json.JSONDecodeError:
                logging.error(f"Failed to parse memory JSON for key={key}")
                continue
        jarvis_speak(response.rstrip(', '), "info")
    else:
        jarvis_speak("I don't have any memories stored yet.", "info")

def forget_memory(key):
    if retrieve_memory(key):
        delete_memory(key)
        jarvis_speak(f"I have forgotten {key}.", "confirmation")
    else:
        jarvis_speak(f"I don't have any memory of {key}.", "error")

def check_system_status(phi2_service=None):
    status = []
    issues = []

    # Check audio input (microphone)
    try:
        mic_list = get_available_microphones()
        if mic_list:
            mic = sr.Microphone()
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
            status.append("Audio input is operational.")
        else:
            issues.append("No microphones detected.")
    except Exception as e:
        issues.append(f"Audio input failed: {str(e)}")
        logging.error(f"Audio input check failed: {str(e)}")

    # Check audio output (TTS)
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            communicate = edge_tts.Communicate("Test", "en-US-GuyNeural")
            asyncio.run(communicate.save(temp_audio.name))
            os.remove(temp_audio.name)
        status.append("Audio output is operational.")
    except Exception as e:
        issues.append(f"Audio output failed: {str(e)}")
        logging.error(f"Audio output check failed: {str(e)}")

    # Check network connectivity
    try:
        socket.create_connection(("www.google.com", 80), timeout=5)
        status.append("Network connectivity is established.")
    except OSError as e:
        issues.append(f"Network connectivity failed: {str(e)}")
        logging.error(f"Network check failed: {str(e)}")

    # Check database
    try:
        conn = sqlite3.connect('jarvis_memory.db')
        c = conn.cursor()
        c.execute("SELECT 1")
        conn.close()
        status.append("Database is operational.")
    except sqlite3.Error as e:
        issues.append(f"Database failed: {str(e)}")
        logging.error(f"Database check failed: {str(e)}")

    # Check scheduler
    try:
        if scheduler.running:
            status.append("Scheduler is operational.")
        else:
            issues.append("Scheduler is not running.")
    except Exception as e:
        issues.append(f"Scheduler failed: {str(e)}")
        logging.error(f"Scheduler check failed: {str(e)}")

    # Check Phi-2 model
    try:
        if phi2_service:
            for sentence in phi2_service.generate_response("Test prompt", max_length=10):
                if "Error" not in sentence:
                    status.append("Phi-2 language model is operational.")
                    break
            else:
                issues.append("Phi-2 model failed to generate response.")
        else:
            issues.append("Phi-2 service not initialized.")
    except Exception as e:
        issues.append(f"Phi-2 model failed: {str(e)}")
        logging.error(f"Phi-2 model check failed: {str(e)}")

    # Format response
    response = "System status report:\n"
    if status:
        response += "Operational systems:\n- " + "\n- ".join(status) + "\n"
    if issues:
        response += "Issues detected:\n- " + "\n- ".join(issues)
    else:
        response += "No issues detected."
    
    return response

def process_command(command, phi2_service=None):
    #context = check_context(command)
    #if context:
    #    jarvis_speak(context, "info")

    if "open youtube" in command or "launch youtube" in command:
        jarvis_speak("Accessing YouTube", "confirmation")
        run_remote_command("xdg-open 'https://www.youtube.com'", MAIN_PC_USER, MAIN_PC_IP)

    elif "open google" in command or "launch google" in command:
        jarvis_speak("Opening Google search interface", "confirmation")
        run_remote_command("xdg-open 'https://www.google.com'", MAIN_PC_USER, MAIN_PC_IP)

    elif "search for" in command or "look up" in command or "find" in command:
        query = command.replace("search for", "").replace("look up", "").replace("find", "").strip()
        if query:
            jarvis_speak(f"Searching for {query}", "confirmation")
            run_remote_command(f"xdg-open 'https://www.google.com/search?q={query}'", MAIN_PC_USER, MAIN_PC_IP)
        else:
            jarvis_speak("What would you like me to search for, sir?", "info")

    elif "what time is it" in command or "current time" in command or "time" in command:
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        jarvis_speak(f"The current time is {current_time}, sir.", "info")

    elif "what's the date" in command or "current date" in command or "date" in command:
        current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
        jarvis_speak(f"Today is {current_date}, sir.", "info")

    elif "open notepad" in command or "text editor" in command or "open editor" in command:
        jarvis_speak("Launching text editor", "confirmation")
        if run_remote_command("which gedit", MAIN_PC_USER, MAIN_PC_IP):
            run_remote_command("gedit &", MAIN_PC_USER, MAIN_PC_IP)
        elif run_remote_command("which nano", MAIN_PC_USER, MAIN_PC_IP):
            run_remote_command("gnome-terminal -- nano &", MAIN_PC_USER, MAIN_PC_IP)
        else:
            jarvis_speak("I'm unable to locate a text editor on your main PC, sir.", "error")

    elif "open calculator" in command or "calculator" in command:
        jarvis_speak("Opening calculator", "confirmation")
        if run_remote_command("which gnome-calculator", MAIN_PC_USER, MAIN_PC_IP):
            run_remote_command("gnome-calculator &", MAIN_PC_USER, MAIN_PC_IP)
        elif run_remote_command("which kcalc", MAIN_PC_USER, MAIN_PC_IP):
            run_remote_command("kcalc &", MAIN_PC_USER, MAIN_PC_IP)
        else:
            jarvis_speak("Calculator application not found on main PC, sir.", "error")

    elif "weather" in command:
        city = ""
        if "in" in command:
            city = command.split("in")[-1].strip()
        elif "for" in command:
            city = command.split("for")[-1].strip()
        if not city:
            city = get_preference("weather_city") or "Heraklion"
        weather_info = get_weather(city)
        jarvis_speak(weather_info, "warning")

    elif "set my preferred" in command:
        parts = command.split("set my preferred")[1].split("to")
        if len(parts) == 2:
            key = parts[0].strip()
            value = parts[1].strip()
            set_preference(key, value)
        else:
            jarvis_speak("Please specify a preference and value, sir.", "error")

    elif "system shutdown" in command or "shutdown computer" in command:
        jarvis_speak("Initiating system shutdown sequence, sir.", "info")
        time.sleep(2)
        run_remote_command("gnome-terminal -- poweroff", MAIN_PC_USER, MAIN_PC_IP)

    elif "restart system" in command or "restart computer" in command:
        jarvis_speak("Initiating system restart sequence, sir.", "info")
        time.sleep(2)
        run_remote_command("gnome-terminal -- bash -c 'reboot; exec bash'", MAIN_PC_USER, MAIN_PC_IP)

    elif "power down" in command or "shut down jarvis" in command:
        jarvis_speak("Powering down all systems. Goodbye, sir.", "info")
        logging.info("JARVIS shutting down")
        sys.exit()

    elif "exit" in command or "quit" in command:
        jarvis_speak("Going offline, sir. Have a good day.", "info")
        logging.info("JARVIS exiting")
        sys.exit()

    elif "status report" in command or "system status" in command:
        status_report = check_system_status()
        jarvis_speak(status_report, "info")

    elif "help" in command or "what can you do" in command:
        help_text = """I can assist with:
        - Launching YouTube, Google, calculator, text editors
        - Internet searches
        - Time and date
        - Weather reports (e.g., 'weather in New York')
        - System shutdown/restart
        - Remembering details (e.g., 'remember my name is John')
        - Managing lists (e.g., 'add milk to shopping list')
        - Setting reminders (e.g., 'remind me to call at 2025-07-12T17:00')
        - Memory inspection (e.g., 'what do you know about me')
        - Viewing conversation history (e.g., 'what did we talk about')
        - Setting preferences (e.g., 'set my preferred weather city to New York')
        - System status report (e.g., 'status report')
        - Answering questions or reasoning (e.g., 'why is the sky blue')
        - Generating code (e.g., 'write a Python function to sort a list')
        - Say 'exit' to terminate"""
        jarvis_speak("Here are my capabilities, sir:", "info")
        print(help_text)

    elif "thank you" in command or "thanks" in command:
        responses = ["You're welcome, sir.", "My pleasure, sir.", "Always happy to help, sir.", "At your service, sir."]
        jarvis_speak(random.choice(responses), "info")

    elif "good morning" in command:
        jarvis_speak("Good morning, sir. How may I assist you today?", "info")
        history = get_conversation_history(limit=20)
        weather_count = sum(1 for h in history if h["command"] and "weather" in h["command"])
        if weather_count > 3:
            city = get_preference("weather_city") or "Heraklion"
            jarvis_speak(f"Would you like the weather for {city}?", "info")

    elif "good evening" in command:
        jarvis_speak("Good evening, sir. What can I do for you?", "info")

    elif "good night" in command:
        jarvis_speak("Good night, sir. Rest well.", "info")

    elif "what did we talk about" in command:
        history = get_conversation_history()
        if history:
            response = "Our recent conversations include: "
            for entry in history:
                if entry["command"]:
                    response += f"You said '{entry['command']}' and I responded '{entry['response']}' on {entry['timestamp'].split('T')[0]}, "
            jarvis_speak(response.rstrip(', '), "info")
        else:
            jarvis_speak("We haven't had any conversations stored yet, sir.", "info")

    elif "remember that" in command:
        parts = command.split("remember that")[1].split("is")
        if len(parts) == 2:
            key = parts[0].strip()
            value = parts[1].strip()
            existing = retrieve_memory(key)
            data = {"type": "simple", "value": value, "timestamp": datetime.datetime.now().isoformat()}
            if existing:
                try:
                    old_value = json.loads(existing)["value"]
                    jarvis_speak(f"Updating {key} from {old_value} to {value}.", "info")
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse existing memory JSON for key={key}")
            store_memory(key, json.dumps(data))
            jarvis_speak(f"I have remembered that {key} is {value}", "confirmation")
        else:
            jarvis_speak("I'm not sure what to remember, sir.", "error")

    elif command.startswith("what is") or command.startswith("tell me about"):
        key = command.replace("what is", "").replace("tell me about", "").strip()
        data = retrieve_memory(key)
        if data:
            try:
                data = json.loads(data)
                if data["type"] == "simple":
                    response_key = key.replace("my", "your")
                    jarvis_speak(f"You mentioned on {data['timestamp'].split('T')[0]} that {response_key} is {data['value']}.", "info")
                elif data["type"] == "list":
                    items = ', '.join(data["items"])
                    jarvis_speak(f"Your {key.replace('_list', '')} list includes {items}.", "info")
                elif data["type"] == "reminders":
                    items = ', '.join([f"{item['task']} at {item['time']}" for item in data["items"]])
                    jarvis_speak(f"Your reminders include {items}.", "info")
            except json.JSONDecodeError:
                logging.error(f"Failed to parse memory JSON for key={key}")
                jarvis_speak(f"I encountered an issue reading {key}, sir.", "error")
        else:
            if phi2_service:
                prompt = f"You are JARVIS, an AI assistant inspired by Iron Man. Respond to the following command or question concisely, in a helpful and witty tone: {command}"
                for sentence in phi2_service.generate_response(prompt):
                    speech_queue.put(sentence)
            else:
                jarvis_speak("Phi-2 service is unavailable, sir.", "error")

    elif "add" in command and "to my" in command:
        parts = command.split("to my")
        if len(parts) == 2:
            item = parts[0].replace("add", "").strip()
            list_name = parts[1].strip().replace(" list", "")
            add_to_list(list_name, item)
        else:
            jarvis_speak("I'm not sure what to add, sir.", "error")

    elif "remove" in command and "from my" in command:
        parts = command.split("from my")
        if len(parts) == 2:
            item = parts[0].replace("remove", "").strip()
            list_name = parts[1].strip().replace(" list", "")
            list_key = f"{list_name}_list"
            current_list = retrieve_memory(list_key)
            if current_list:
                try:
                    current_list = json.loads(current_list)
                    if item in current_list["items"]:
                        current_list["items"].remove(item)
                        store_memory(list_key, json.dumps(current_list))
                        jarvis_speak(f"{item} has been removed from your {list_name} list.", "confirmation")
                    else:
                        jarvis_speak(f"{item} is not in your {list_name} list.", "info")
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse list JSON for key={list_key}")
                    jarvis_speak(f"I encountered an issue with your {list_name} list, sir.", "error")
            else:
                jarvis_speak(f"You don't have a {list_name} list yet.", "info")

    elif command.startswith("what's on my"):
        list_name = command.split("what's on my")[1].strip().replace(" list", "")
        read_list(list_name)

    elif "remind me to" in command:
        parts = command.split(" at ")
        if len(parts) == 2:
            task = parts[0].replace("remind me to", "").strip()
            time_str = parts[1].strip()
            add_reminder(task, time_str)
        else:
            jarvis_speak("Please specify a task and time, sir.", "error")

    elif "what do you know about me" in command:
        list_memories()

    elif "forget" in command:
        key = command.replace("forget", "").strip()
        forget_memory(key)

    elif command.startswith("write a") or command.startswith("generate a") or command.startswith("code for"):
        if phi2_service:
            prompt = f"Generate Python code for the following request: {command}"
            jarvis_speak("Here is the generated code, sir:", "info")
            for sentence in phi2_service.generate_response(prompt, max_length=500):
                speech_queue.put(sentence)
                print(sentence)
            jarvis_speak("The code has been printed to the console for your review.", "info")
        else:
            jarvis_speak("Phi-2 service is unavailable, sir.", "error")

    else:
        if phi2_service:
            prompt = f"You are JARVIS, an AI assistant inspired by Iron Man. Respond to the following command or question concisely, in a helpful and witty tone: {command}"
            for sentence in phi2_service.generate_response(prompt):
                speech_queue.put(sentence)
        else:
            responses = [
                "I'm not sure I understand that command, sir.",
                "Could you please rephrase that, sir?",
                "I don't have that capability currently, sir.",
                "I'm afraid I cannot process that request, sir."
            ]
            jarvis_speak(random.choice(responses), "error")
            jarvis_speak("Say 'help' for available commands.", "info")
