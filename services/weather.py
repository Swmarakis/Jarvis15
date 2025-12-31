import requests
import logging
from core.speech import jarvis_speak

def get_weather(city):
    try:
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
        response = requests.get(geocode_url, timeout=10)
        data = response.json()
        if not data.get("results"):
            logging.error(f"Weather lookup failed: City {city} not found")
            return f"Sorry, I couldn't find weather information for {city}."
        latitude = data["results"][0]["latitude"]
        longitude = data["results"][0]["longitude"]
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true&temperature_2m,weather_code"
        response = requests.get(weather_url, timeout=10)
        weather_data = response.json()
        temp = weather_data["current_weather"]["temperature"]
        weather_code = weather_data["current_weather"]["weathercode"]
        weather_codes = {
            0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
            45: "fog", 51: "light drizzle", 61: "light rain", 63: "moderate rain",
            71: "light snow", 73: "moderate snow", 95: "thunderstorm"
        }
        desc = weather_codes.get(weather_code, "unknown condition")
        logging.info(f"Weather retrieved for {city}: {desc}, {temp}°C")
        return f"The weather in {city} is {desc} with a temperature of {temp} degrees Celsius."
    except Exception as e:
        logging.error(f"Weather error: {e}")
        print(f"Weather error: {e}")
        return "Sorry, I couldn't fetch the weather."
