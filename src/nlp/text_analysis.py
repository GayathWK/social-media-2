"""
text_analysis.py
----------------
NLP analysis pipeline for AI coding assistant trust/distrust research.
 
Performs two analyses on collected social media comments:
 
1. Sentiment Analysis (VADER)
   - Scores every comment (compound, positive, negative, neutral)
   - Classifies each comment as positive, negative, or neutral
   - Chosen because VADER is specifically designed for social media text —
     it handles informal language, slang, and punctuation emphasis well
     without requiring training data.
 
2. Topic Modelling (LDA)
   - Discovers latent topics across all comments
   - Topics are mapped to 5 research themes:
       productivity, reliability, security, cost, code_ownership
   - LDA chosen over BERTopic for interpretability and reproducibility —
     results are stable across runs with a fixed random seed, and the
     term-topic distributions are easy to inspect and justify in the report.
 
Output saved to: data/processed/
  - comments_with_sentiment.json   — all comments with VADER scores + label
  - topic_model_terms.json         — top terms per LDA topic
  - comments_with_topics.json      — all comments with dominant topic assigned
  - summary_stats.json             — aggregate sentiment by tool, video, topic

"""
 
import os
import json
import re
import logging
from collections import defaultdict
 
import nltk
import pandas as pd
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from gensim import corpora
from gensim.models import LdaModel
 
# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)
logging.getLogger("gensim").setLevel(logging.WARNING) 

# NLTK downloads (safe to run multiple times)
def download_nltk_resources():
    for resource in ["stopwords", "punkt", "wordnet", "omw-1.4", "punkt_tab"]:
        nltk.download(resource, quiet=True)
 
# Configuration
 
# LDA settings
NUM_TOPICS = 5          # Matches our 5 research themes
LDA_PASSES = 15         # More passes = more stable topics, reasonable for this corpus size
LDA_RANDOM_SEED = 42    # Fixed seed for reproducibility
 
# Our 5 research themes — used to manually map LDA topics after inspection
# Each list contains seed keywords that strongly signal that theme.
# After running LDA, we match each discovered topic to the closest theme
# by comparing the topic's top terms against these seed word lists.
THEME_SEEDS = {
    "productivity":   ["faster", "speed", "time", "efficient", "workflow",
                       "automate", "quick", "save", "boilerplate", "autocomplete",
                       "suggest", "generate", "write", "complete"],
    "reliability":    ["bug", "error", "wrong", "incorrect", "broken",
                       "unreliable", "hallucinate", "mistake", "garbage",
                       "fix", "issue", "fail", "trash", "useless", "test"],
    "security":       ["security", "privacy", "data", "leak", "vulnerable",
                       "license", "safe", "risk", "expose", "telemetry"],
    "cost":           ["price", "expensive", "cheap", "cost", "subscription",
                       "free", "worth", "money", "pay", "pricing", "plan", "open"],
    "code_ownership": ["copyright", "ownership", "training", "stolen",
                       "plagiarism", "license", "legal", "intellectual",
                       "property", "scraping"],
}
 
# Domain-specific stopwords to add on top of NLTK's standard list
EXTRA_STOPWORDS = {
    "ai", "code", "coding", "use", "using", "used", "tool", "like", "just",
    "get", "got", "one", "would", "could", "really", "think", "know", "also",
    "github", "copilot", "cursor", "claude", "video", "comment", "people",
    "thing", "things", "make", "good", "great", "way", "work", "working",
    "much", "many", "still", "even", "well", "want", "need", "new", "go",
    # Added — video/creator noise
    "ali", "antigravity", "composer", "lex", "fridman",
    # Added — filler words
    "thank", "thanks", "please", "nice", "awesome", "amazing", "love",
    "best", "better", "see", "say", "going", "something", "actually"
}
 
# Text preprocessing
def preprocess_text(text: str, stop_words: set, lemmatizer: WordNetLemmatizer) -> list[str]:
    """
    Clean and tokenise a comment for LDA input.
    Steps:
      1. Lowercase
      2. Remove URLs, mentions, hashtags
      3. Remove non-alphabetic characters
      4. Tokenise
      5. Remove stopwords
      6. Lemmatise
      7. Keep only tokens of length >= 3
    """
    # Lowercase
    text = text.lower()
    # Remove URLs
    text = re.sub(r"http\S+|www\S+", "", text)
    # Remove @mentions and #hashtags
    text = re.sub(r"[@#]\w+", "", text)
    # Keep only alphabetic characters and spaces
    text = re.sub(r"[^a-z\s]", " ", text)
    # Tokenise
    tokens = word_tokenize(text)
    # Filter stopwords, short tokens
    tokens = [
        lemmatizer.lemmatize(t)
        for t in tokens
        if t not in stop_words and len(t) >= 3
    ]
    return tokens
 
# Sentiment analysis
def run_sentiment_analysis(comments: list[dict]) -> list[dict]:
    """
    Score every comment using VADER.
 
    VADER is well-suited to social media text — it accounts for:
    - Capitalisation (GREAT vs great)
    - Punctuation emphasis (great!!!)
    - Common internet slang and emoticons
 
    Each comment gets:
      compound  — overall score from -1 (most negative) to +1 (most positive)
      pos/neg/neu — proportion scores
      sentiment_label — 'positive', 'negative', or 'neutral'
 
    Thresholds follow VADER's recommended values:
      compound >= 0.05  → positive
      compound <= -0.05 → negative
      otherwise         → neutral
    """
    analyser = SentimentIntensityAnalyzer()
    enriched = []
 
    log.info(f"Running sentiment analysis on {len(comments)} comments...")
 
    for c in comments:
        scores = analyser.polarity_scores(c.get("text", ""))
        compound = scores["compound"]
 
        label = "neutral"
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
 
        enriched.append({
            **c,
            "sentiment_compound": compound,
            "sentiment_pos": scores["pos"],
            "sentiment_neg": scores["neg"],
            "sentiment_neu": scores["neu"],
            "sentiment_label": label
        })
 
    log.info("Sentiment analysis complete.")
    return enriched
 

# Topic modelling
def run_topic_modelling(comments: list[dict], stop_words: set) -> tuple[LdaModel, corpora.Dictionary, list]:
    """
    Run LDA topic modelling on all comment texts.
 
    LDA (Latent Dirichlet Allocation) treats each comment as a mixture
    of topics, and each topic as a distribution over words. With NUM_TOPICS=5
    we expect to recover topics roughly corresponding to our 5 research themes.
 
    Returns:
      lda_model   — trained LDA model
      dictionary  — gensim Dictionary (word <-> id mapping)
      corpus      — bag-of-words corpus used for training
    """
    lemmatizer = WordNetLemmatizer()
 
    log.info("Preprocessing comment text for LDA...")
    texts = [
        preprocess_text(c.get("text", ""), stop_words, lemmatizer)
        for c in comments
    ]
 
    # Filter out empty documents
    texts = [t for t in texts if len(t) > 0]
    log.info(f"  {len(texts)} non-empty documents after preprocessing")
 
    # Build vocabulary
    dictionary = corpora.Dictionary(texts)
 
    # Filter extremes:
    # - ignore terms appearing in fewer than 5 documents (too rare, likely noise)
    # - ignore terms appearing in more than 70% of documents (too common, not informative)
    dictionary.filter_extremes(no_below=5, no_above=0.7)
    log.info(f"  Vocabulary size after filtering: {len(dictionary)} terms")
 
    # Convert to bag-of-words
    corpus = [dictionary.doc2bow(text) for text in texts]
 
    log.info(f"Training LDA model ({NUM_TOPICS} topics, {LDA_PASSES} passes)...")
    lda_model = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=NUM_TOPICS,
        passes=LDA_PASSES,
        random_state=LDA_RANDOM_SEED,
        alpha="auto",       # Learn document-topic distribution automatically
        eta="auto"          # Learn topic-word distribution automatically
    )
 
    log.info("LDA training complete.")

    # Save model for reuse — avoids retraining on every run
    os.makedirs("data/processed/lda_model", exist_ok=True)
    lda_model.save("data/processed/lda_model/lda.model")
    dictionary.save("data/processed/lda_model/dictionary.gensim")
    log.info("LDA model saved to data/processed/lda_model/")

    return lda_model, dictionary, corpus, texts

 
# Map LDA topics to research themes
def map_topics_to_themes(lda_model: LdaModel, num_words: int = 15) -> dict:
    """
    Map each LDA topic index to one of our 5 research themes.
 
    Method:
      For each topic, get the top N terms.
      Count how many of those terms appear in each theme's seed word list.
      Assign the theme with the highest overlap.
      If no overlap, label as 'other'.
 
    This mapping is inspectable and justifiable — the full term lists
    are saved to topic_model_terms.json for the report.
    """
    topic_map = {}
    topic_terms = {}
 
    for topic_id in range(NUM_TOPICS):
        # Get top terms for this topic
        terms = [
            word for word, _ in lda_model.show_topic(topic_id, topn=num_words)
        ]
        topic_terms[topic_id] = terms
 
        # Score against each theme's seed words
        scores = {}
        for theme, seeds in THEME_SEEDS.items():
            scores[theme] = sum(1 for t in terms if t in seeds)
 
        best_theme = max(scores, key=scores.get)
        best_score = scores[best_theme]
 
        topic_map[topic_id] = best_theme if best_score > 0 else "other"
 
        log.info(f"  Topic {topic_id} → '{topic_map[topic_id]}' | top terms: {', '.join(terms[:8])}")
 
    return topic_map, topic_terms
 
# Assign dominant topic to each comment
def assign_topics_to_comments(
    comments: list[dict],
    lda_model: LdaModel,
    dictionary: corpora.Dictionary,
    topic_map: dict,
    stop_words: set
) -> list[dict]:
    """
    For each comment, find its dominant LDA topic and assign the mapped theme.
    Comments with no meaningful tokens get topic_label = 'unknown'.
    """
    lemmatizer = WordNetLemmatizer()
    enriched = []
 
    log.info("Assigning topics to comments...")
 
    for c in comments:
        tokens = preprocess_text(c.get("text", ""), stop_words, lemmatizer)
        bow = dictionary.doc2bow(tokens)
 
        if not bow:
            enriched.append({**c, "dominant_topic_id": None, "topic_label": "unknown", "topic_score": 0.0})
            continue
 
        topic_dist = lda_model.get_document_topics(bow)
        if not topic_dist:
            enriched.append({**c, "dominant_topic_id": None, "topic_label": "unknown", "topic_score": 0.0})
            continue
 
        dominant = max(topic_dist, key=lambda x: x[1])
        topic_id, score = dominant
 
        enriched.append({
            **c,
            "dominant_topic_id": int(topic_id),
            "topic_label": topic_map.get(topic_id, "other"),
            "topic_score": round(float(score), 4)
        })
 
    log.info("Topic assignment complete.")
    return enriched
 
# Summary statistics
def compute_summary_stats(comments: list[dict]) -> dict:
    """
    Compute aggregate sentiment and topic distributions for the report.
    Breaks down by: tool, video, sentiment label, topic label.
    """
    df = pd.DataFrame(comments)
 
    summary = {}
 
    # Sentiment by tool
    summary["sentiment_by_tool"] = (
        df.groupby(["tool", "sentiment_label"])
        .size()
        .unstack(fill_value=0)
        .to_dict()
    )
 
    # Average compound sentiment by tool
    summary["avg_sentiment_by_tool"] = (
        df.groupby("tool")["sentiment_compound"]
        .mean()
        .round(4)
        .to_dict()
    )
 
    # Topic distribution by tool
    if "topic_label" in df.columns:
        summary["topics_by_tool"] = (
            df.groupby(["tool", "topic_label"])
            .size()
            .unstack(fill_value=0)
            .to_dict()
        )
 
    # Overall sentiment distribution
    summary["overall_sentiment"] = df["sentiment_label"].value_counts().to_dict()
 
    # Overall topic distribution
    if "topic_label" in df.columns:
        summary["overall_topics"] = df["topic_label"].value_counts().to_dict()
 
    # Sentiment by comment type (top_level vs reply)
    summary["sentiment_by_type"] = (
        df.groupby(["type", "sentiment_label"])
        .size()
        .unstack(fill_value=0)
        .to_dict()
    )
 
    return summary
 
# Save helpers
def save_json(data, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(path) / 1024
    log.info(f"Saved {os.path.basename(path)} ({size_kb:.1f} KB)")
 
# Main pipeline
def run_pipeline(
    input_path: str = "data/raw/youtube/comments_raw.json",
    output_dir: str = "data/processed"
):
    # 1. Load raw comments
    log.info(f"Loading comments from {input_path}...")
    with open(input_path, encoding="utf-8") as f:
        comments = json.load(f)
    log.info(f"Loaded {len(comments)} comments.")
 
    # 2. Download NLTK resources
    download_nltk_resources()
 
    # 3. Build stopword list
    stop_words = set(stopwords.words("english")) | EXTRA_STOPWORDS
 
    # 4. Sentiment analysis
    comments_with_sentiment = run_sentiment_analysis(comments)
    save_json(comments_with_sentiment, f"{output_dir}/comments_with_sentiment.json")
 
    # 5. Topic modelling — load saved model if available, else train
    lda_model_path = "data/processed/lda_model/lda.model"
    dict_path = "data/processed/lda_model/dictionary.gensim"

    if os.path.exists(lda_model_path) and os.path.exists(dict_path):
        log.info("Found existing LDA model — loading instead of retraining.")
        log.info("Delete data/processed/lda_model/ to force retrain.")
        lda_model = LdaModel.load(lda_model_path)
        dictionary = corpora.Dictionary.load(dict_path)
    else:
        log.info("No saved model found — training from scratch.")
        lda_model, dictionary, corpus, texts = run_topic_modelling(
            comments_with_sentiment, stop_words
        )
 
 
    # 6. Map topics to themes
    log.info("Mapping LDA topics to research themes...")
    topic_map, topic_terms = map_topics_to_themes(lda_model)
 
    # Save topic terms for report inspection
    topic_terms_output = {
        str(tid): {
            "theme": topic_map[tid],
            "top_terms": terms
        }
        for tid, terms in topic_terms.items()
    }
    save_json(topic_terms_output, f"{output_dir}/topic_model_terms.json")
 
    # 7. Assign topics to comments
    comments_with_topics = assign_topics_to_comments(
        comments_with_sentiment, lda_model, dictionary, topic_map, stop_words
    )
    save_json(comments_with_topics, f"{output_dir}/comments_with_topics.json")
 
    # 8. Summary statistics
    log.info("Computing summary statistics...")
    stats = compute_summary_stats(comments_with_topics)
    save_json(stats, f"{output_dir}/summary_stats.json")
 
    # Print a quick summary to terminal
    log.info("=" * 50)
    log.info("NLP pipeline complete.")
    log.info(f"  Total comments analysed: {len(comments)}")
    log.info(f"  Sentiment distribution:  {stats['overall_sentiment']}")
    log.info(f"  Topic distribution:      {stats.get('overall_topics', {})}")
    log.info(f"  Avg sentiment by tool:")
    for tool, score in stats["avg_sentiment_by_tool"].items():
        label = "positive" if score > 0.05 else "negative" if score < -0.05 else "neutral"
        log.info(f"    {tool:12s}: {score:+.4f} ({label})")
    log.info("=" * 50)
 

if __name__ == "__main__":
    run_pipeline()
 
