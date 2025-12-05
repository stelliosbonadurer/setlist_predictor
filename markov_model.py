import pandas as pd
import numpy as np
from collections import defaultdict

# ---------- STEP 1: Load data ----------

def load_setlists(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Basic sanity checks
    required_cols = {"show_id", "date", "venue", "position", "song"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Missing required columns: {missing}")

    # Ensure position is int and sorted
    df["position"] = df["position"].astype(int)
    df = df.sort_values(["show_id", "position"]).reset_index(drop=True)
    return df

# ---------- STEP 2: Build a 1st-order Markov chain ----------

def build_markov_chain(df: pd.DataFrame):
    """
    Returns:
      transitions: dict[current_song][next_song] = probability
    """
    counts = defaultdict(lambda: defaultdict(int))

    # For each show, look at consecutive song pairs
    for show_id, group in df.groupby("show_id"):
        songs = list(group.sort_values("position")["song"])
        for i in range(len(songs) - 1):
            curr_song = songs[i]
            next_song = songs[i + 1]
            counts[curr_song][next_song] += 1

    # Convert counts to probabilities
    transitions = {}
    for curr_song, next_dict in counts.items():
        total = sum(next_dict.values())
        transitions[curr_song] = {
            next_song: count / total
            for next_song, count in next_dict.items()
        }

    return transitions

# ---------- STEP 3: Pick a starting song ----------

def most_common_opener(df: pd.DataFrame) -> str:
    openers = df[df["position"] == 1]["song"]
    return openers.value_counts().idxmax()

# ---------- STEP 4: Generate a setlist ----------

def generate_setlist(transitions, start_song: str, length: int = 10):
    setlist = [start_song]
    current = start_song

    for _ in range(length - 1):
        next_probs = transitions.get(current)
        if not next_probs:
            # If we get stuck (song never followed by anything),
            # restart from a random song that has outgoing edges
            current = np.random.choice(list(transitions.keys()))
            setlist.append(current)
            continue

        songs = list(next_probs.keys())
        probs = list(next_probs.values())
        current = np.random.choice(songs, p=probs)
        setlist.append(current)

    return setlist

# ---------- STEP 5: Glue it all together ----------

if __name__ == "__main__":
    df = load_setlists("setlist.csv")
    transitions = build_markov_chain(df)
    opener = most_common_opener(df)
    predicted = generate_setlist(transitions, start_song=opener, length=10)

    print("Most common opener:", opener)
    print("Predicted setlist:")
    for i, song in enumerate(predicted, start=1):
        print(f"{i}. {song}")
