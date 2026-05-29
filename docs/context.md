# Project Context: AI-Powered Restaurant Recommendation System (Zomato Use Case)

## Overview

Build an **AI-powered restaurant recommendation service** inspired by Zomato. The system suggests restaurants from user preferences by combining **structured restaurant data** with a **Large Language Model (LLM)** to produce personalized, human-like recommendations.

## Objective

Design and implement an application that:

1. Accepts user preferences (location, budget, cuisine, ratings, and more)
2. Uses a real-world restaurant dataset
3. Uses an LLM to generate personalized, natural-language recommendations
4. Displays clear, useful results to the user

## Data Source

| Item | Detail |
|------|--------|
| **Dataset** | Zomato restaurant data on Hugging Face |
| **URL** | https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation |
| **Relevant fields** | Restaurant name, location, cuisine, cost, rating, and related attributes |

## System Workflow

### 1. Data Ingestion

- Load and preprocess the Zomato dataset from Hugging Face
- Extract fields: restaurant name, location, cuisine, cost, rating, etc.

### 2. User Input

Collect preferences including:

| Preference | Examples |
|------------|----------|
| **Location** | Delhi, Bangalore |
| **Budget** | low, medium, high |
| **Cuisine** | Italian, Chinese |
| **Minimum rating** | Numeric threshold |
| **Additional** | family-friendly, quick service, etc. |

### 3. Integration Layer

- Filter and prepare restaurant records that match user input
- Pass structured, filtered results into an LLM prompt
- Design prompts so the LLM can reason over and rank options

### 4. Recommendation Engine (LLM)

The LLM should:

- Rank restaurants by fit to preferences
- Explain why each recommendation matches
- Optionally summarize the overall set of choices

### 5. Output Display

Present top recommendations in a user-friendly format. Each item should include:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- AI-generated explanation (why it was recommended)

## Architecture (Logical Layers)

```
┌─────────────────┐
│   User Input    │  location, budget, cuisine, rating, extras
└────────┬────────┘
         ▼
┌─────────────────┐
│ Data Ingestion  │  Hugging Face dataset → preprocess → structured records
└────────┬────────┘
         ▼
┌─────────────────┐
│ Filter / Prep   │  match user prefs → candidate restaurant list
└────────┬────────┘
         ▼
┌─────────────────┐
│  LLM + Prompt   │  rank, explain, optionally summarize
└────────┬────────┘
         ▼
┌─────────────────┐
│ Output Display  │  top N recommendations with explanations
└─────────────────┘
```

## Key Requirements (Checklist)

- [ ] Load Zomato dataset from Hugging Face
- [ ] Preprocess and expose structured fields (name, location, cuisine, cost, rating)
- [ ] UI or interface for user preference collection
- [ ] Filtering logic aligned with user inputs
- [ ] LLM integration with a well-designed ranking/explanation prompt
- [ ] Formatted output: name, cuisine, rating, cost, AI explanation

## Constraints & Notes

- Recommendations must be grounded in **real dataset rows** (filter first, then LLM reasons over candidates—not purely hallucinated listings).
- Budget is expressed categorically: **low / medium / high**.
- Explanations should be **personalized** and tied to the user’s stated preferences.
- The experience should mirror a **Zomato-style** discovery flow: practical filters plus conversational, helpful copy from the LLM.

## Source Document

This context is derived from `docs/problemStatement.txt`.
