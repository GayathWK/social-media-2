# AI Coding Assistant Trust Analysis

**COSC 3047 - Social Media and Network Analysis, Assignment 2**
RMIT University, Semester 1 2026

## Research Question

What drives trust and distrust in AI coding assistants among developers, and how do influential users and discussion communities shape concerns around productivity, reliability, security, cost, and code ownership?

## Project Details

- Group: 69
- Course: COSC 3047 (Undergraduate)

## Data Sources

This project uses public discussion data from three online platforms:

- **YouTube**: video comments and replies about GitHub Copilot, Cursor, Claude Code, Codex, and AI coding tools.
- **GitHub Issues**: public issues and issue comments from `microsoft/vscode-copilot-release`, `openai/codex`, and `anthropics/claude-code`.
- **Hacker News**: public story and comment threads about AI coding tools and developer workflows.

The final merged dataset used for analysis contains comment text for NLP and interaction edges for network analysis. Raw and processed data files are included with the submitted code so the analysis can be rerun without collecting from the APIs again. Smaller representative samples are also included in `data/samples/`.

## Repository Structure

```text
social-media-2/
├── collection_notebooks/
│   ├── youtube_collection_cleaning.ipynb
│   ├── github_collection_cleaning.ipynb
│   └── hackerNews_collection_cleaning.ipynb
├── data/
│   ├── raw/               # Raw API outputs used for the analysis
│   ├── processed/         # Cleaned, merged, NLP, and network outputs
│   └── samples/           # Small representative samples for submission
├── src/
│   ├── nlp/               # Platform-specific NLP notebooks
│   └── utils/             # API helper modules
├── data_merge.ipynb       # Merges platform datasets
├── full_text_analysis.ipynb
├── full_network_analysis.ipynb
├── requirements.txt
└── README.md
```

## Fresh Setup

From a fresh computer, use Python 3.12 or a recent Python 3 version.

```bash
git clone <repo-url>
cd social-media-2

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m ipykernel install --user --name social-media-2 --display-name "Python (social-media-2)"
cp .env.example .env
```

On Windows PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

In VS Code, select the notebook kernel named `Python (social-media-2)`.

## Credentials

Add credentials to `.env`:

```text
YOUTUBE_API_KEY=your_youtube_api_key_here
GITHUB_TOKEN=your_github_token_here
```

`YOUTUBE_API_KEY` is required for fresh YouTube collection. `GITHUB_TOKEN` is optional for public GitHub data, but recommended because it increases API rate limits. Hacker News collection does not require credentials.

Do not commit `.env`, API keys, tokens, or private account information.

## Reuse Included Data or Pull Fresh Data

The submitted repository includes the raw and processed data used for the final report. This means the analysis can be rerun without using API credentials or spending API quota.

Default behaviour:

- Collection notebooks reuse existing raw JSON files when they are present.
- `full_text_analysis.ipynb` reuses the saved LDA model when it is present.
- Analysis outputs are written back into `data/processed/`.

To pull fresh API data instead, set this flag near the top of the relevant collection notebook:

```python
FORCE_API_PULL = True
```

To retrain the combined LDA model instead of loading the saved model, set this flag in `full_text_analysis.ipynb`:

```python
FORCE_RETRAIN_LDA = True
```

## Running the Full Pipeline

Run notebooks in this order. The collection notebooks reuse existing raw files by default. To force a fresh API pull, set `FORCE_API_PULL = True` near the top of the relevant collection notebook before running it.

1. `collection_notebooks/youtube_collection_cleaning.ipynb`
   - Collects YouTube video metadata, top-level comments, replies, and reply edges.
   - Requires `YOUTUBE_API_KEY` only when pulling fresh data.
   - Outputs to `data/raw/youtube/` and `data/processed/youtube/`.

2. `collection_notebooks/github_collection_cleaning.ipynb`
   - Collects GitHub issues, issue comments, labels, cleaned text, and user-issue edges.
   - Uses `GITHUB_TOKEN` when pulling fresh data.
   - Outputs to `data/raw/github/` and `data/processed/github/`.

3. `collection_notebooks/hackerNews_collection_cleaning.ipynb`
   - Collects Hacker News stories and comments using public APIs.
   - Outputs to `data/raw/hackernews/` and `data/processed/hackernews/`.

4. Optional platform-specific NLP notebooks:
   - `src/nlp/youtube_text_analysis.ipynb`
   - `src/nlp/github_text_analysis.ipynb`
   - `src/nlp/hackernews_text_analysis.ipynb`

5. `data_merge.ipynb`
   - Merges YouTube, GitHub, and Hacker News into:
     - `data/processed/combined/combined_comments.csv`
     - `data/processed/combined/combined_edges.json`

6. `full_text_analysis.ipynb`
   - Runs VADER sentiment analysis and LDA topic modelling on the combined comments.
   - Outputs:
     - `data/processed/nlp/comments_with_topics.csv`
     - `data/processed/nlp/summary_stats.json`
     - sentiment/topic figures in `data/processed/nlp/`

7. `full_network_analysis.ipynb`
   - Builds the directed reply graph and projected community graph.
   - Runs PageRank, in-degree, betweenness, connected component analysis, and Louvain community detection.
   - Outputs:
     - `data/processed/network/centrality_scores.csv`
     - `data/processed/network/community_profiles.csv`
     - network figures in `data/processed/network/`

To rerun only the final analysis from the included files without API collection, start at `data_merge.ipynb`, then run `full_text_analysis.ipynb` and `full_network_analysis.ipynb`.

## Expected Final Outputs

The report figures are generated by:

- `full_text_analysis.ipynb`
  - `sentiment_overview.png`
  - `topic_overview.png`
  - `sentiment_by_topic.png`
  - `topic_channel_heatmap.png`
  - `wordcloud_trust_distrust.png`

- `full_network_analysis.ipynb`
  - `degree_distribution.png`
  - `top_users_centrality.png`
  - `community_profiles.png`
  - `network_graph.png`
  - `synthesis_network_nlp.png`

The final local run used `32,810` merged comments and `14,128` raw network edges before network-specific cleaning and projection.

## Network Analysis Summary

The network component uses two graph structures:

- A directed reply graph for direct user-to-user replies, used for PageRank, in-degree, betweenness, and degree distribution.
- An undirected projected community graph, where users are connected if they reply to each other or participate in the same discussion thread or GitHub issue, used for Louvain community detection.

Nodes represent public platform users. Directed edges represent replies from one user to another. User-thread edges represent participation in a video, Hacker News story, or GitHub issue and are projected into user-user co-participation edges for community detection.

## Data Samples

`data/samples/` contains small representative samples:

- `youtube_comments_sample.json`
- `combined_comments_sample.json`
- `combined_edges_sample.json`

These files show the structure of the text records and network edge records without committing the full dataset.

## Notes

- API credentials, virtual environments, caches, and saved LDA model internals are ignored by git. Raw and processed CSV/JSON/figure outputs are included for reproducibility.
- NLTK resources are downloaded inside the notebooks. The main resources used are `stopwords`, `punkt`, `wordnet`, `omw-1.4`, `punkt_tab`, and `vader_lexicon`.
- All assessed data processing, NLP, network construction, and visualisation are implemented in Python.
