import speech_recognition as sr
import asyncio
import edge_tts
import tempfile
import platform
import os
import random
import logging

recognizer = sr.Recognizer()

JARVIS_GREETINGS = [
    "At your service, sir.",
    "How may I assist you today?",
    "Yes, sir. How can I help?",
    "I'm here to help, sir.",
    "What can I do for you?",
    "Ready to assist, sir.",
    "Good day, sir.",
    "Always a pleasure to assist.",
    "Standing by for your command.",
    "Your digital assistant is online.",
    "Welcome back, sir.",
    "At your disposal.",
    "Awaiting instructions.",
    "Prepared to serve.",
    "Operational and ready.",
    "Greetings, sir. What shall we do today?",
    "Fully functional, sir.",
    "I’m all ears, sir.",
    "Command recognized. Standing by.",
    "It’s good to hear from you, sir.",
    "Ready when you are, sir."
]

JARVIS_CONFIRMATIONS = [
    "Right away, sir.",
    "Consider it done.",
    "Certainly, sir.",
    "Of course.",
    "Immediately, sir.",
    "Very well, sir.",
    "Absolutely, sir.",
    "Executing your command now.",
    "Working on it right away.",
    "Right this moment, sir.",
    "On it.",
    "Understood, proceeding now.",
    "Affirmative.",
    "With pleasure, sir.",
    "Task received, sir.",
    "Actioning your request.",
    "It's already underway.",
    "As you wish, sir.",
    "On your command.",
    "No problem, sir.",
    "Initiating now."
]

JARVIS_ERRORS = [
    "I'm afraid I didn't catch that, sir.",
    "Could you repeat that, please?",
    "I'm sorry, I didn't understand.",
    "Pardon me, sir. Could you say that again?",
    "I'm having trouble understanding you, sir.",
    "Apologies, sir, that didn’t register.",
    "I’m not sure I understood that.",
    "Could you please clarify, sir?",
    "I beg your pardon, sir?",
    "Something went wrong in the input.",
    "Regrettably, I missed that.",
    "That doesn't compute, sir.",
    "I'm sorry, could you rephrase that?",
    "The input was unclear, sir.",
    "Forgive me, I need a clearer instruction.",
    "Unfortunately, I couldn't process that.",
    "I'm struggling to interpret that, sir.",
    "That input seems incomplete.",
    "It appears I misheard, sir.",
    "Might you try that again, sir?"
]

JARVIS_WEATHER_RESPONSES = [
    "The weather data indicates",
    "Current meteorological conditions show",
    "Weather analysis reveals",
    "Environmental sensors report"
]

def play_audio(file_path):
    system = platform.system()
    if system == "Windows":
        os.system(f'start /min wmplayer "{file_path}"')
    elif system == "Darwin":
        os.system(f"afplay '{file_path}'")
    else:
        if os.system("which mpg123 > /dev/null 2>&1") == 0:
            os.system(f"mpg123 -q '{file_path}'")
        elif os.system("which cvlc > /dev/null 2>&1") == 0:
            os.system(f"cvlc --play-and-exit '{file_path}' > /dev/null 2>&1")
        elif os.system("which mpv > /dev/null 2>&1") == 0:
            os.system(f"mpv '{file_path}' > /dev/null 2>&1")
        else:
            logging.error("No audio player found to play TTS audio.")
            print("No audio player found to play TTS audio.")

async def edge_tts_speak(text, voice="en-US-GuyNeural"):
    communicate = edge_tts.Communicate(text, voice)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        await communicate.save(temp_audio.name)
        temp_audio_path = temp_audio.name
    play_audio(temp_audio_path)
    os.remove(temp_audio_path)

def speak(text):
    print(f"JARVIS: {text}")
    logging.info(f"JARVIS Response: {text}")
    try:
        asyncio.run(edge_tts_speak(text))
        from core.memory import store_conversation
        store_conversation(None, text)
    except Exception as e:
        logging.error(f"edge-tts error: {e}")
        print(f"edge-tts error: {e}")

def jarvis_speak(text, response_type="normal"):
    if response_type == "greeting":
        prefix = random.choice(JARVIS_GREETINGS)
        speak(prefix)
    elif response_type == "confirmation":
        prefix = random.choice(JARVIS_CONFIRMATIONS)
        speak(f"{prefix} {text}")
    elif response_type == "error":
        error_msg = random.choice(JARVIS_ERRORS)
        speak(error_msg)
    elif response_type == "weather":
        prefix = random.choice(JARVIS_WEATHER_RESPONSES)
        speak(f"{prefix}: {text}")
    else:
        speak(text)

def get_available_microphones():
    try:
        mic_list = sr.Microphone.list_microphone_names()
        print("Available microphones:")
        logging.info("Listing available microphones")
        for i, mic in enumerate(mic_list):
            print(f"  {i}: {mic}")
            logging.info(f"Microphone {i}: {mic}")
        return mic_list
    except Exception as e:
        logging.error(f"Error listing microphones: {e}")
        print(f"Error listing microphones: {e}")
        return []

# core/speech.py
def find_working_microphone():
    mic_list = get_available_microphones()
    for i, mic in enumerate(mic_list):
        if "pulse" in mic.lower():
            try:
                mic = sr.Microphone(device_index=i)
                with mic as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print(f"Using microphone {i}: {mic_list[i]}")
                logging.info(f"Using microphone {i}: {mic_list[i]}")
                return i
            except Exception as e:
                logging.error(f"Microphone {i} failed: {e}")
                continue
    try:
        mic = sr.Microphone()
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("Using default microphone")
        logging.info("Using default microphone")
        return None
    except Exception as e:
        logging.error(f"Default microphone failed: {e}")
        print(f"Default microphone failed: {e}")
    for i in range(len(mic_list)):
        try:
            mic = sr.Microphone(device_index=i)
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print(f"Using microphone {i}: {mic_list[i]}")
            logging.info(f"Using microphone {i}: {mic_list[i]}")
            return i
        except Exception as e:
            logging.error(f"Microphone {i} failed: {e}")
            print(f"Microphone {i} failed: {e}")
            continue
    logging.error("No working microphone found")
    print("No working microphone found!")
    return -1

def listen_for_wake_word(device_index=None):
    try:
        if device_index is None:
            mic = sr.Microphone()
        elif device_index == -1:
            return False
        else:
            mic = sr.Microphone(device_index=device_index)
        with mic as source:
            print("Listening for 'JARVIS'...")
            logging.info("Listening for wake word 'JARVIS'")
            recognizer.energy_threshold = 300
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            audio = recognizer.listen(source, timeout=3, phrase_time_limit=2)
        text = recognizer.recognize_google(audio).lower()
        print(f"Detected: {text}")
        logging.info(f"Wake word detection: {text}")
        return "jarvis" in text
    except (sr.UnknownValueError, sr.WaitTimeoutError):
        return False
    except sr.RequestError as e:
        logging.error(f"Network connectivity issue: {e}")
        print(f"Network connectivity issue: {e}")
        return False
    except Exception as e:
        logging.error(f"Audio input error: {e}")
        print(f"Audio input error: {e}")
        return False

def listen_for_command(device_index=None):
    try:
        if device_index is None:
            mic = sr.Microphone()
        elif device_index == -1:
            return ""
        else:
            mic = sr.Microphone(device_index=device_index)
        with mic as source:
            print("Awaiting your command, sir...")
            logging.info("Listening for command")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
        command = recognizer.recognize_google(audio).lower()
        print(f"Command received: {command}")
        logging.info(f"Command received: {command}")
        from core.memory import store_conversation
        store_conversation(command, None)
        return command
    except sr.UnknownValueError:
        jarvis_speak("", "error")
        logging.error("Speech recognition failed: Unknown value")
        return ""
    except sr.RequestError:
        speak("I'm experiencing connectivity issues with my speech recognition systems, sir.")
        logging.error("Speech recognition failed: Network connectivity issue")
        return ""
    except sr.WaitTimeoutError:
        speak("I didn't receive a command, sir.")
        logging.info("Command listening timed out")
        return ""
    except Exception as e:
        logging.error(f"Command processing error: {e}")
        print(f"Command processing error: {e}")
        return ""
