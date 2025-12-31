import logging
import requests
import json

class Phi2Service:
    def __init__(self, model_name="phi"):
        self.model_name = model_name
        self.api_url = "http://localhost:11434/api/generate"
        logging.info(f"Initializing Phi-2 service with Ollama model: {model_name}")
        try:
            response = requests.post(self.api_url, json={"model": model_name, "prompt": "Test", "stream": False})
            if response.status_code == 200:
                logging.info("Phi-2 Ollama service initialized successfully")
            else:
                raise Exception(f"Ollama server responded with status {response.status_code}")
        except Exception as e:
            logging.error(f"Failed to connect to Ollama server: {str(e)}")
            raise

    def generate_response(self, prompt, max_length=200):
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "max_tokens": max_length,
                "temperature": 0.7,
                "top_p": 0.9,
                "stream": True
            }
            with requests.post(self.api_url, json=payload, stream=True) as response:
                response.raise_for_status()
                buffer = ""
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        if "response" in data:
                            buffer += data["response"]
                            while '.' in buffer or '!' in buffer or '?' in buffer:
                                end_idx = min(
                                    buffer.find('.') if '.' in buffer else len(buffer),
                                    buffer.find('!') if '!' in buffer else len(buffer),
                                    buffer.find('?') if '?' in buffer else len(buffer)
                                )
                                if end_idx < len(buffer):
                                    sentence = buffer[:end_idx + 1].strip()
                                    buffer = buffer[end_idx + 1:].strip()
                                    yield sentence
                if buffer:
                    yield buffer.strip()
        except Exception as e:
            logging.error(f"Phi-2 generation failed: {str(e)}")
            yield f"Error generating response: {str(e)}"