# EPM AI Hub

Grade your team's SOPs, calculate time savings, and track cumulative automation ROI.

## Quick Start

```bash
cd ~/sop-value-tracker
source venv/bin/activate
streamlit run app.py
```

## Features

- **Auto-Grade with Claude** — Paste an SOP, get scored on clarity, completeness, reproducibility, automation potential, and documentation quality
- **Manual Grading** — Score dimensions yourself and input time estimates
- **Value Calculator** — Automatically computes per-person, team, and annual hours recovered
- **Portfolio Dashboard** — Aggregate view with charts showing total value and quality distribution
- **Seed Data** — Comes pre-loaded with 3 sample SOPs for demo

## Project Structure

```
sop-value-tracker/
├── app.py           # Streamlit dashboard
├── grader.py        # Claude API grading engine
├── store.py         # JSON persistence + value calculations
├── seed.py          # Demo data seeder
├── data/sops.json   # SOP data store
├── requirements.txt
└── venv/
```

## Auto-Grading

To use Claude-powered auto-grading, provide an Anthropic API key in the grading form. The key is only used for the grading call and is not stored.
