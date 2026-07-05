import json
import time

import redis
import requests


r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)


def get_weather(city: str):
    """Simulasi API call yang lambat dengan caching Redis selama 5 menit."""
    cache_key = f"weather:{city.lower()}"

    try:
        cached = r.get(cache_key)
        if cached is not None:
            return json.loads(cached)
    except redis.exceptions.ConnectionError:
        cached = None

    time.sleep(2)
    try:
        response = requests.get(f"https://api.example.com/weather/{city}", timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        data = {
            "city": city,
            "temperature": "N/A",
            "source": "fallback-demo"
        }

    try:
        r.setex(cache_key, 300, json.dumps(data))
    except redis.exceptions.ConnectionError:
        pass

    return data
