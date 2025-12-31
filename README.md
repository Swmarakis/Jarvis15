# J.A.R.V.I.S. - Personal Voice Assistant

A highly capable, modular voice assistant inspired by Iron Man's J.A.R.V.I.S. This project integrates offline Large Language Models (LLMs), persistent database memory, and system automation to act as a comprehensive daily helper.

## ⚡ Features

* **🎙️ Voice Interaction:**
    * **Wake Word Detection:**listens efficiently for the wake word "JARVIS".
    * **Natural Speech:** Uses `edge-tts` for high-quality, neural-network-based voice output.
    * **Speech Recognition:** Uses Google Speech Recognition for accurate command-to-text conversion.
* **🧠 Intelligence (LLM):**
    * **Phi-2 Integration:** Connects to a local **Ollama** instance running the `phi` model for general conversation, reasoning, and code generation.
    * **Context Awareness:** Can recall previous parts of the conversation.
* **💾 Long-Term Memory:**
    * **Fact Recall:** "Remember that my keys are on the table."
    * **Lists:** Manage shopping lists, to-do lists, etc.
    * **Preferences:** Remembers user preferences (e.g., preferred weather city).
    * **Database:** Uses SQLite (`jarvis_memory.db`) for persistent storage across restarts.
* **⚙️ System & Remote Control:**
    * **Remote Command Execution:** Can execute commands on a main PC via SSH (configured in settings).
    * **App Launching:** Opens Calculator, Notepad (gedit/nano), Browsers, etc.
    * **Web Search:** direct "Search for..." commands opening Google or YouTube.
* **📅 Productivity:**
    * **Scheduler:** Built-in `APScheduler` for setting and executing reminders at specific times.
    * **Weather:** Real-time weather updates via Open-Meteo API.

## 📂 Project Structure

```text
.
├── core/
│   ├── memory.py       # SQLite database interactions (CRUD for memories)
│   ├── phi2.py         # Interface for local Ollama LLM service
│   ├── scheduler.py    # Reminder and background task scheduling
│   └── speech.py       # TTS and STT logic (Wake word, Listening, Speaking)
├── services/
│   ├── system.py       # Remote SSH command execution
│   └── weather.py      # Open-Meteo API integration
├── utils/
│   └── helpers.py      # Command processing logic and intent routing
├── config/
│   └── settings.py     # Configuration (IPs, Usernames)
├── main.py             # Entry point
└── requirements.txt    # Python dependencies
