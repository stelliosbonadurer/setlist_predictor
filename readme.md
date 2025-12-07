# Setlist Predictor

Predict upcoming setlists using historical data from setlist.fm. The project includes data collection, exploratory analysis, and a roadmap of sequence models that grow from simple Markov chains to transformers.

## Highlights
- Scrape and normalize setlists from setlist.fm with rate-limit backoff.
- Explore patterns (top songs, openers/closers, transitions) via Jupyter notebooks.
- Prepare clean, per-song CSVs ready for sequence modeling.
- Incrementally build models: Markov → N-gram → RNN/LSTM → Transformer.

## Repository Layout
```
setlist_predictor/
├── fetch_setlists.py              # Download and normalize setlists
├── data/                          # CSVs written by the scraper
│   └── kitchen_dwellers_setlists.csv
├── notebooks/
│   └── eda_kitchen_dwellers.ipynb # Exploratory analysis
├── models/
│   ├── markov/
│   ├── ngram/
│   ├── rnn/
│   └── transformer/
└── README.md
```

## Data Schema
Each CSV row represents one song performance with these columns:
- `show_id`, `show_date`, `city`, `state`, `country`, `venue`, `artist_name`, `tour_name`
- `festival_flag` (1 if festival), `set_index`, `song_index`
- `song_name`, `is_cover`, `cover_artist`, `encore_index` (int if encore, else blank)

## Getting Started
1) **Create a virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate       # macOS/Linux
.\.venv\Scripts\activate        # Windows
```

2) **Install dependencies**
```bash
pip install requests python-dotenv pandas matplotlib notebook
# or: pip install -r requirements.txt
```

3) **Configure credentials**  
Create `.env` in the project root:
```
SETLIST_FM_API_KEY=your_api_key_here
```
Do not commit `.env`.

## Fetching Setlists
Run the scraper for any artist:
```bash
python3 fetch_setlists.py "Kitchen Dwellers"
```
You’ll be prompted to pick the correct artist match, then all setlists are fetched and written to `data/<artist>_setlists.csv`.

## Exploratory Analysis
Launch Jupyter and open the Kitchen Dwellers notebook:
```bash
python3 -m notebook
```
File: `notebooks/eda_kitchen_dwellers.ipynb`  
It covers show counts, most-played songs, openers/closers, and simple transition checks.

## Modeling Roadmap
- **Level 1 — Markov chains:** next-song probabilities and basic setlist generation.
- **Level 2 — N-grams:** multi-song context for richer transitions.
- **Level 3 — RNN/LSTM:** neural sequence modeling for longer dependencies.
- **Level 4 — Transformers:** state-of-the-art sequence modeling with optional contextual features.

## Goals
- End-to-end predictive pipeline for live music setlists.
- Reusable framework for any setlist.fm-supported artist.
- Clear visualizations and insights suitable for a portfolio project.

## Notes and License
- For personal/educational use. Respect setlist.fm’s terms of service and rate limits.
