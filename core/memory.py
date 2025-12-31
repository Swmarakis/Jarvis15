import sqlite3
import logging
import json
from datetime import datetime



def init_memory_db():
    try:
        conn = sqlite3.connect('jarvis_memory.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS memory
                     (key TEXT PRIMARY KEY, value TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS conversation
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, command TEXT, response TEXT, timestamp TEXT)''')
        conn.commit()
        conn.close()
        logging.info("Memory database initialized")
    except sqlite3.Error as e:
        logging.error(f"Database initialization failed: {str(e)}")

def store_memory(key, value):
    try:
        conn = sqlite3.connect('jarvis_memory.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO memory (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
        logging.info(f"Stored memory: {key}")
    except sqlite3.Error as e:
        logging.error(f"Failed to store memory {key}: {str(e)}")

def retrieve_memory(key):
    try:
        conn = sqlite3.connect('jarvis_memory.db')
        c = conn.cursor()
        c.execute("SELECT value FROM memory WHERE key = ?", (key,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"Failed to retrieve memory {key}: {str(e)}")
        return None

def retrieve_all_memories():
    try:
        conn = sqlite3.connect('jarvis_memory.db')
        c = conn.cursor()
        c.execute("SELECT key, value FROM memory")
        memories = c.fetchall()
        conn.close()
        return dict(memories)  # Return as dictionary for consistency with list_memories
    except sqlite3.Error as e:
        logging.error(f"Failed to retrieve all memories from database: {str(e)}")
        return {}

def delete_memory(key):
    try:
        conn = sqlite3.connect('jarvis_memory.db')
        c = conn.cursor()
        c.execute("DELETE FROM memory WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        logging.info(f"Deleted memory: {key}")
    except sqlite3.Error as e:
        logging.error(f"Failed to delete memory {key}: {str(e)}")

def get_conversation_history(limit=10):
    try:
        conn = sqlite3.connect('jarvis_memory.db')
        c = conn.cursor()
        c.execute("SELECT command, response, timestamp FROM conversation ORDER BY id DESC LIMIT ?", (limit,))
        results = c.fetchall()
        conn.close()
        return [{"command": r[0], "response": r[1], "timestamp": r[2]} for r in results]
    except sqlite3.Error as e:
        logging.error(f"Failed to retrieve conversation history: {str(e)}")
        return []

def store_conversation(command, response):
    try:
        conn = sqlite3.connect('jarvis_memory.db')
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute("INSERT INTO conversation (command, response, timestamp) VALUES (?, ?, ?)",
                  (command, response, timestamp))
        conn.commit()
        conn.close()
        logging.info(f"Stored conversation: {command}")
    except sqlite3.Error as e:
        logging.error(f"Failed to store conversation: {str(e)}")

def set_preference(key, value):
    data = {"type": "preference", "value": value, "timestamp": datetime.now().isoformat()}
    store_memory(f"preference_{key}", json.dumps(data))
    logging.info(f"Set preference {key} to {value}")

def get_preference(key):
    data = retrieve_memory(f"preference_{key}")
    if data:
        try:
            return json.loads(data)["value"]
        except json.JSONDecodeError:
            logging.error(f"Failed to parse preference JSON for key={key}")
            return None
    return None

def load_reminders():
    try:
        from core.scheduler import add_reminder  # Import here
        reminders = retrieve_memory("reminders")
        if reminders:
            reminder_data = json.loads(reminders)
            if reminder_data["type"] == "reminders":
                for item in reminder_data["items"]:
                    task = item["task"]
                    time_str = item["time"]
                    add_reminder(task, time_str)
                logging.info("Reminders loaded from database")
    except (sqlite3.Error, json.JSONDecodeError, KeyError) as e:
        logging.error(f"Failed to load reminders: {str(e)}")