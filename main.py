import logging
import speech_recognition as sr
from core.phi2 import Phi2Service
from core.speech import recognizer, find_working_microphone, jarvis_speak, listen_for_wake_word, listen_for_command
from core.scheduler import scheduler, load_reminders
from core.memory import init_memory_db, get_preference, set_preference
from utils.helpers import process_command, speech_queue
import time


# Configure logging
logging.basicConfig(
    filename='jarvis_logs.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    print("=" * 50)
    print("    J.A.R.V.I.S. - Your Personal Assistant")
    print("=" * 50)
    logging.info("JARVIS started")
    jarvis_speak("Good day, sir. JARVIS is online and ready for your command.", "greeting")

    # Initialize memory database
    init_memory_db()
    if not get_preference("weather_city"):
        set_preference("weather_city", "Heraklion")

    # Load reminders
    load_reminders()

    # Initialize Phi-2 service
    try:
        phi2_service = Phi2Service(model_name="phi")
        logging.info("Phi-2 service initialized")
    except Exception as e:
        logging.error(f"Failed to initialize Phi-2 service: {str(e)}")
        jarvis_speak("Warning: Phi-2 language model failed to initialize.", "error")
        phi2_service = None

    # Find working microphone
    mic_index = find_working_microphone()
    if mic_index == -1:
        jarvis_speak("No working microphone found. Please check audio settings.", "error")
        logging.error("No working microphone found")
        return

    while True:
        try:
            if listen_for_wake_word(mic_index):
                jarvis_speak("Yes, sir?", "confirmation")
                command = listen_for_command(mic_index)
                if command:
                    process_command(command, phi2_service)
                    # Wait until the speech queue is empty
                    while not speech_queue.empty():
                        time.sleep(0.1)  # Small delay to prevent busy waiting
                else:
                    jarvis_speak("I didn't catch that, sir.", "error")
        except KeyboardInterrupt:
            jarvis_speak("Shutting down. Goodbye, sir.")
            logging.info("JARVIS shutting down via KeyboardInterrupt")
            speech_queue.put(None)  # Signal speech worker to stop
            scheduler.shutdown()
            break
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            print(f"Unexpected error: {str(e)}")
            jarvis_speak("An error occurred, sir. Please check the logs.", "error")

if __name__ == "__main__":
    main()