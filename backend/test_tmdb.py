import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("TMDB_API_KEY")

print("=" * 60)
print("TMDB DIRECT CONNECTION TEST")
print("=" * 60)

if not api_key:
    print("❌ TMDB_API_KEY not found")
    exit()

print("✅ API key loaded")
print("Testing TMDB...")

url = "https://api.tmdb.org/3/movie/550"

params = {
    "api_key": api_key,
    "language": "en-US"
}

try:
    response = requests.get(
        url,
        params=params,
        timeout=(10, 15)
    )

    print("Status code:", response.status_code)

    if response.status_code == 200:
        data = response.json()

        print("✅ TMDB CONNECTION WORKING")
        print("Movie:", data.get("title"))
        print("TMDB ID:", data.get("id"))

    else:
        print("❌ TMDB returned an error")
        print(response.text[:500])

except requests.exceptions.Timeout:
    print("❌ Request timed out")

except requests.exceptions.ConnectionError as e:
    print("❌ Connection error:")
    print(e)

except Exception as e:
    print("❌ Other error:")
    print(e)