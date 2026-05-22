# AI Coding Assistant Trust Analysis
**COSC 3047 — Social Media and Network Analysis, Assignment 2**
RMIT University, Semester 1 2026

## Research Question
What drives trust and distrust in AI coding assistants among developers, and how do influential users and discussion communities shape concerns around productivity, reliability, security, cost, and code ownership?

## Team
- Group: 69
- Members: Gayath Wethmin Kaluwahewa
- Course: COSC 3047 (Undergraduate)

## Data Sources
- **YouTube** — Comments from videos reviewing GitHub Copilot, Cursor, Claude Code, Codex
- **Hacker News** — Discussion threads on AI coding tools
- **GitHub Issues** — Public issues from microsoft/vscode-copilot-release, openai/codex, and anthropics/claude-code

## Project Structure
```
social_media_2/
├── data/
│   ├── raw/              # Raw collected data (not committed to git)
│   │   ├── youtube/
│   │   ├── hackernews/
│   │   └── github/
│   ├── processed/        # Cleaned, merged datasets
│   └── samples/          # Representative samples for submission (≤10MB)
├── notebooks/            
├── src/
│   ├── collectors/       # Data collection scripts
│   ├── network/          # Network construction and analysis
│   ├── nlp/              # Sentiment and topic modelling
│   └── utils/            # Shared utilities
├── visualisations/       # Output charts and network graphs
├── report/               # Final report PDF
└── requirements.txt
```

## Setup
```bash
# Clone the repo
git clone <repo-url>
cd ai-coding-trust-analysis

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure local API credentials
cp .env.example .env
# Then add your YouTube API key to .env
```

## Running the Pipeline
Run notebooks in this order:
1. `notebooks/youtube_collection_cleaning.ipynb`
2. `notebooks/github_collection_cleaning.ipynb`
3. Network analysis notebook
4. NLP sentiment and topic modelling notebook
5. Synthesis and visualisation notebook

## Data Collection Dates
- YouTube: collected 21 May 2026
- GitHub: collected 22 May 2026

## Notes
- API keys are never stored in submitted outputs. Use environment variables or the credential modules in `src/utils/`.
- Raw data is gitignored due to size. See `data/samples/` for submission sample.
- All analysis implemented in Python. See `requirements.txt` for dependencies.
