# CLAUDE.md

## Project Overview

Joker Builds - Data scraping from PoE Ninja, data interpretation, grouping, and then chat based interface on the data for build decision based on meta analysis, and tagging

## Key Information

- **Language/Framework**: Python 3.11+ with SQLAlchemy, SQLite, Docker
- **Build Command**: docker build -t joker-builds .
- **Test Command**: python -m pytest tests/ -v
- **Lint Command**: python -m flake8 src/ (if configured)

## Project Structure

```
joker-builds/
├── CLAUDE.md        # This file - project context for Claude
└── [Your project files here]
```

## Important Notes

Utilise TDD, always create a test to confirm behaviour is working before returning work to the instructor. 
Keep most individual tests aside, but maintain a End-To-End standard workflow test and run it on each occasion
Ensure that any case that might involve polling external websites does not make too many requests
Do not leave To dos, complete all work relevant to a task, do not mock data, except for tests, where data schemas have already been confirmed
Do not stray from task, touching on unrelated or even only partially related tasks
Where utilising libraries pick those that are most popular and recently updated to avoid deprecation

## Git Workflow

ALWAYS commit changes after completing and testing each task.
ALWAYS push to remote repository after completing a feature or major fix.
Use descriptive commit messages that explain what was implemented.
We can always roll back if needed, so commit frequently to save progress.
This ensures work is preserved and allows for easy rollbacks if needed.
Push regularly to keep remote repository up to date with completed work.