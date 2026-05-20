# 📚 Peer-to-Peer Study Group Agent

An AI agent that automatically forms optimal study groups among students based on their complementary academic strengths and weaknesses using clustering algorithms.

## Features

- **K-Means & Hierarchical Clustering** — two algorithms to form balanced groups
- **Auto-detect optimal group count** — uses silhouette scoring
- **Complementarity scoring** — evaluates how well members complement each other
- **PCA Visualisation** — 2-D cluster plot exported as PNG
- **Web Dashboard** — modern dark-mode Flask UI for teachers
- **CLI Mode** — run directly from terminal

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.9+ |
| Clustering | scikit-learn (K-Means, Agglomerative) |
| Data | NumPy, Pandas |
| Visualisation | Matplotlib, Seaborn |
| Web | Flask |
| Tests | Pytest |

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Web Dashboard

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

### 3. Run the CLI

```bash
python main.py
```

Follow the interactive prompts to generate sample data, choose a clustering algorithm, and view group assignments.

### 4. Run Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
├── app.py                      # Flask web application
├── main.py                     # CLI entry point
├── requirements.txt
├── README.md
├── models/
│   └── student.py              # Student data model
├── clustering/
│   └── study_group_agent.py    # Core AI clustering engine
├── data/
│   └── sample_students.py      # Sample data generator
├── templates/
│   └── index.html              # Dashboard HTML
├── static/
│   ├── style.css               # Premium dark-mode CSS
│   └── app.js                  # Frontend JavaScript
└── tests/
    └── test_clustering.py      # Unit tests
```

## How It Works

1. **Student profiles** are built from subject scores (0–100) across 6 subjects
2. Scores are **normalised** into feature vectors
3. A clustering algorithm groups students to **maximise complementarity** (diverse strengths covering group weaknesses)
4. **Group evaluation** computes a complementarity score and diversity index

## Dashboard Usage

| Action | How |
|---|---|
| Load sample data | Set count → click "Generate Sample Data" |
| Add a student | Fill in left panel form → "Add Student" |
| Remove a student | Click ✕ in the students table |
| Form groups | Choose algorithm + optional group count → "Form Groups" |
| Search students | Type in the search box above the table |
