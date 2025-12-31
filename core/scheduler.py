from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import json
import logging
from core.memory import retrieve_memory, store_memory
from core.speech import speak

scheduler = BackgroundScheduler()
scheduler.start()

def load_reminders():
    reminders = retrieve_memory("reminders")
    if reminders:
        try:
            reminders = json.loads(reminders)
            for reminder in reminders["items"]:
                try:
                    reminder_time = datetime.datetime.fromisoformat(reminder["time"])
                    if reminder_time > datetime.datetime.now():
                        scheduler.add_job(lambda: speak(f"It's time to {reminder['task']}"), 'date', run_date=reminder_time)
                        logging.info(f"Scheduled reminder: task={reminder['task']}, time={reminder['time']}")
                except ValueError:
                    logging.error(f"Invalid time format for reminder: {reminder['time']}")
                    continue
        except json.JSONDecodeError:
            logging.error("Failed to parse reminders JSON")
            return

def add_reminder(task, time_str):
    try:
        reminder_time = datetime.datetime.fromisoformat(time_str)
        reminders = retrieve_memory("reminders")
        if not reminders:
            reminders = {"type": "reminders", "items": [], "next_id": 1}
        else:
            reminders = json.loads(reminders)
        new_id = reminders["next_id"]
        reminders["items"].append({"id": new_id, "task": task, "time": time_str})
        reminders["next_id"] = new_id + 1
        store_memory("reminders", json.dumps(reminders))
        if reminder_time > datetime.datetime.now():
            scheduler.add_job(lambda: speak(f"It's time to {task}"), 'date', run_date=reminder_time)
            logging.info(f"Added reminder: task={task}, time={time_str}")
        from core.speech import jarvis_speak
        jarvis_speak(f"I'll remind you to {task} at {time_str}.", "confirmation")
    except ValueError:
        from core.speech import jarvis_speak
        jarvis_speak("I couldn't parse the time format, sir. Please use YYYY-MM-DDTHH:MM:SS.", "error")
        logging.error(f"Failed to parse reminder time: {time_str}")
