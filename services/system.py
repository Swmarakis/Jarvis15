import subprocess
from core.speech import speak
import logging

def run_remote_command(command, user, ip):
    ssh_command = f"ssh {user}@{ip} '{command}'"
    try:
        result = subprocess.run(ssh_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Remote command executed: {command}")
        return result.stdout.decode()
    except subprocess.CalledProcessError as e:
        speak("Failed to execute the command on the main PC.")
        logging.error(f"Remote command failed: {command}, error: {e}")
        return None
