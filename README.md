# TGOV Scraper

A set of tools for scraping and analyzing data from the Tulsa Government Access Television (TGOV) website.

## Setup

This project uses Poetry for dependency management.

```bash
# Install dependencies
poetry install --no-root

# Activate the virtual environment
poetry self add poetry-plugin-shell
poetry shell
```

## Running
### Jupyter notebooks

```bash
# Install Jupyter kernel for this environment (needed for Jupyter notebooks)
python -m ipykernel install --user --name=tgov-scraper --display-name="TGOV Scraper"

jupyter notebook
```

### Prefect flows
See https://docs.prefect.io/get-started

```bash
prefect server start                      # to start the persistent server

python -m flows.translate_meetings        # to run a specific flow
```

### Tests

```bash
# Run all tests
pytest

# Run specific tests
pytest tests/test_meetings.py

# Run tests with verbose output
pytest -v
```

## Project Structure

- `data/`: local data artifacts
- `flows/`: prefect flows
- `notebooks/`: Jupyter notebooks for analysis and exploration
- `scripts/`: one off scripts for downloading, conversions, etc
- `src/`: Source code for the scraper
  - `models/`: Pydantic models for data representation
- `tasks/`: prefect tasks
- `tests/`: Test files


## Running the transcription scripts

### download the mp4
```
poetry run python scripts/download_m3u8.py 'https://archive-stream.granicus.com/OnDemand/_definst_/mp4:archive/tulsa-ok/tulsa-ok_843d30f2-b631-4a16-8018-a2a31930be70.mp4/playlist.m3u8' --output data/video/test_granicus_video.mp4
```
### transcribe
```
poetry run python scripts/video2text.py data/video/test_granicus_video.mp4 --model-size tiny --verbose
```
