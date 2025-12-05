# fetch_setlists.py

import os
import requests
from dotenv import load_dotenv

# Load .env so we can read the API key
load_dotenv()

API_KEY = os.getenv("SETLIST_FM_API_KEY")
if not API_KEY:
    raise RuntimeError("API key not found. Make sure you added SETLIST_FM_API_KEY to .env")

BASE_URL = "https://api.setlist.fm/rest/1.0"

# Prepare a session with the required headers
session = requests.Session()
session.headers.update({
    "x-api-key": API_KEY,
    "Accept": "application/json",
    "Accept-Language": "en",
})


def search_artist(artist_name: str):
    """
    Search setlist.fm for an artist by name.
    Returns the first artist result dict, or None if not found.
    """
    params = {
        "artistName": artist_name,
        "p": 1,
        "sort": "sortName",
    }

    print(f"Searching for artist: {artist_name!r}")
    resp = session.get(f"{BASE_URL}/search/artists", params=params)
    resp.raise_for_status()
    data = resp.json()

    artists = data.get("artist", [])
    if not artists:
        print("No artists found.")
        return None

    best = artists[0]
    print(f"Found: {best.get('name')} (MBID: {best.get('mbid')})")
    return best


def main():
    artist_name = input("Enter band/artist name: ").strip()
    if not artist_name:
        print("No artist name entered, exiting.")
        return

    artist = search_artist(artist_name)
    if not artist:
        return

    # Just to show we can access fields:
    mbid = artist.get("mbid")
    print(f"\nUsing MBID: {mbid}")


if __name__ == "__main__":
    main()
