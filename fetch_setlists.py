# fetch_setlists.py

import os
import time
import csv
import sys
from typing import List, Dict, Any, Optional

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

def get_with_backoff(url, params=None, max_retries=5):
    """
    Wrapper around session.get that retries on HTTP 429 (Too Many Requests)
    with exponential backoff.
    """
    delay = 0.5  # starting delay in seconds

    for attempt in range(max_retries):
        resp = session.get(url, params=params)

        # If it's not a rate limit error, either return or raise
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp

        # Got 429: wait and try again
        print(f"Hit rate limit (429). Sleeping {delay} seconds before retry {attempt + 1}...")
        time.sleep(delay)
        delay *= 2  # exponential backoff

    # If we get here, we kept getting 429
    raise RuntimeError("Too many 429 responses from setlist.fm, giving up for now.")

def search_artist(artist_name: str) -> Optional[Dict[str, Any]]:
    """
    Search setlist.fm for an artist by name.

    - Shows up to 10 candidates from the current API page.
    - Prioritizes artists whose names exactly match, then start with,
      then contain the search text.
    - Lets the user say "not visible" and move to the next API page.

    Returns the chosen artist dict, or None if cancelled.
    """
    query_lower = artist_name.lower()
    page = 1

    while True:
        params = {
            "artistName": artist_name,
            "p": page,
            "sort": "sortName",
        }

        print(f"\nSearching for artist {artist_name!r}, page {page}...")
        resp = get_with_backoff(f"{BASE_URL}/search/artists", params=params)
        data = resp.json()

        artists = data.get("artist", [])
        if not artists:
            if page == 1:
                print("No artists found.")
            else:
                print("No more results from the API.")
            return None

        # Prioritize better name matches
        def sort_key(a: Dict[str, Any]):
            name = (a.get("name") or "").lower()
            if name == query_lower:
                return (0, name)  # exact match
            if name.startswith(query_lower):
                return (1, name)  # startswith
            if query_lower in name:
                return (2, name)  # contains
            return (3, name)      # everything else

        artists_sorted = sorted(artists, key=sort_key)
        candidates = artists_sorted[:10]

        print("\nSelect the correct artist from this page:")
        for idx, a in enumerate(candidates, start=1):
            name = a.get("name")
            country = a.get("country", "?")
            disamb = a.get("disambiguation") or ""
            mbid = a.get("mbid")

            extra = f" - {disamb}" if disamb else ""
            print(f"{idx}. {name} [{country}]{extra} (MBID: {mbid})")

        print("0. Not visible here / show next results page")

        while True:
            choice = input(
                f"\nEnter a number 1–{len(candidates)} to select, "
                "0 for more results, or press Enter to cancel: "
            ).strip()

            if choice == "":
                print("Cancelled artist selection.")
                return None

            if choice == "0":
                # Move to next API page
                page += 1
                break  # break inner loop, fetch next page

            try:
                idx = int(choice)
            except ValueError:
                print("Please enter a valid number.")
                continue

            if 1 <= idx <= len(candidates):
                chosen = candidates[idx - 1]
                print(f"\nYou selected: {chosen.get('name')} (MBID: {chosen.get('mbid')})")
                return chosen

            print("Number out of range.")


def fetch_setlists_page(mbid: str, page: int = 1):
    """
    Fetch one page of setlists for a given artist MBID.
    Returns a list of setlist dicts (may be empty).
    """
    url = f"{BASE_URL}/artist/{mbid}/setlists"
    params = {"p": page}

    print(f"\nFetching setlists for MBID={mbid}, page={page}...")
    resp = get_with_backoff(url, params=params)
    data = resp.json()

    setlists = data.get("setlist", [])
    print(f"Got {len(setlists)} setlists on page {page}.")
    return setlists

def fetch_all_setlists_for_artist(mbid: str, pause_seconds: float = 0.5):
    """
    Fetch all setlists for an artist MBID, going through all pages.
    Returns a list of setlist dicts.
    """
    all_setlists = []
    page = 1

    while True:
        url = f"{BASE_URL}/artist/{mbid}/setlists"
        params = {"p": page}

        print(f"\nFetching page {page} for MBID={mbid}...")
        resp = get_with_backoff(url, params=params)
        data = resp.json()

        page_setlists = data.get("setlist", [])
        if not page_setlists:
            print("No more setlists on this page. Stopping.")
            break

        all_setlists.extend(page_setlists)

        # Optional: use the metadata setlist.fm returns
        total = int(data.get("total", len(all_setlists)))
        items_per_page = int(data.get("itemsPerPage", len(page_setlists)))

        print(f"  got {len(page_setlists)} setlists (total so far: {len(all_setlists)}/{total})")

        # If this page returned fewer than itemsPerPage, we've hit the last page
        if len(page_setlists) < items_per_page:
            break

        page += 1
        time.sleep(pause_seconds)  # be nice to their API

    print(f"\nFinished. Total setlists fetched: {len(all_setlists)}")
    return all_setlists

def normalize_setlist_to_rows(setlist: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert a single setlist (JSON dict from the API) into a list of row dicts,
    one row per song, with flat fields ready for CSV.
    """
    rows: List[Dict[str, Any]] = []

    show_id = setlist.get("id")
    event_date_raw = setlist.get("eventDate")  # usually dd-MM-yyyy
    # Convert dd-MM-yyyy -> yyyy-MM-dd
    if event_date_raw:
        try:
            day, month, year = event_date_raw.split("-")
            show_date = f"{year}-{month}-{day}"
        except ValueError:
            show_date = event_date_raw  # fallback, just keep original
    else:
        show_date = None

    artist_name = (setlist.get("artist") or {}).get("name")

    venue_obj = setlist.get("venue") or {}
    venue_name = venue_obj.get("name")

    city_obj = venue_obj.get("city") or {}
    city_name = city_obj.get("name")
    state_name = city_obj.get("state") or city_obj.get("stateCode")
    country_name = (city_obj.get("country") or {}).get("name")

    tour_name = (setlist.get("tour") or {}).get("name")
    # some tours are marked as festivals with @festival="true"
    festival_flag = 1 if (setlist.get("tour") or {}).get("@festival") == "true" else 0

    sets_obj = (setlist.get("sets") or {}).get("set", [])
    # Sometimes a single set is a dict instead of list
    if isinstance(sets_obj, dict):
        sets_obj = [sets_obj]

    for set_index, s in enumerate(sets_obj):
        encore_index: Optional[int]
        encore_raw = s.get("@encore")
        if encore_raw is not None:
            try:
                encore_index = int(encore_raw)
            except ValueError:
                encore_index = None
        else:
            encore_index = None

        songs = s.get("song", [])
        if isinstance(songs, dict):
            songs = [songs]

        for song_index, song in enumerate(songs):
            song_name = song.get("name")
            cover = song.get("cover")

            if isinstance(cover, dict):
                is_cover = 1
                cover_artist = cover.get("name")
            else:
                is_cover = 0
                cover_artist = None

            rows.append({
                "show_id": show_id,
                "show_date": show_date,
                "city": city_name,
                "state": state_name,
                "country": country_name,
                "venue": venue_name,
                "artist_name": artist_name,
                "tour_name": tour_name,
                "festival_flag": festival_flag,
                "set_index": set_index,
                "song_index": song_index,
                "song_name": song_name,
                "is_cover": is_cover,
                "cover_artist": cover_artist,
                "encore_index": encore_index,
            })

    return rows

def write_setlists_to_csv(artist_name: str, setlists: List[Dict[str, Any]], out_dir: str = "data") -> str:
    """
    Take all setlists for an artist and write them to a CSV file
    (one row per song). Returns the path to the CSV file.
    """
    os.makedirs(out_dir, exist_ok=True)
    safe_name = artist_name.lower().replace(" ", "_")
    filepath = os.path.join(out_dir, f"{safe_name}_setlists.csv")

    fieldnames = [
        "show_id",
        "show_date",
        "city",
        "state",
        "country",
        "venue",
        "artist_name",
        "tour_name",
        "festival_flag",
        "set_index",
        "song_index",
        "song_name",
        "is_cover",
        "cover_artist",
        "encore_index",
    ]

    total_rows = 0

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for sl in setlists:
            rows = normalize_setlist_to_rows(sl)
            for row in rows:
                writer.writerow(row)
            total_rows += len(rows)

    print(f"\nWrote {total_rows} rows to {filepath}")
    return filepath



def main():
    if len(sys.argv) > 1:
        artist_name = " ".join(sys.argv[1:]).strip()
    else:
        artist_name = input("Enter band/artist name: ").strip()
    if not artist_name:
        print("No artist name entered, exiting.")
        return

    artist = search_artist(artist_name)
    if not artist:
        return

    mbid = artist.get("mbid")
    resolved_name = artist.get("name", artist_name)
    print(f"\nUsing MBID: {mbid} for artist {resolved_name!r}")

    setlists = fetch_all_setlists_for_artist(mbid)
    if not setlists:
        print("No setlists returned.")
        return

    csv_path = write_setlists_to_csv(resolved_name, setlists)
    print(f"Done. CSV file created at: {csv_path}")


    # Show a tiny preview of the first setlist
    first = setlists[0]
    venue = first.get("venue") or {}
    city = (venue.get("city") or {}).get("name")

    print("\nExample setlist from all results:")
    print("  id:   ", first.get("id"))
    print("  date: ", first.get("eventDate"))
    print("  venue:", venue.get("name"))
    print("  city: ", city)


if __name__ == "__main__":
    main()
