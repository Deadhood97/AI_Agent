# Kaggle Dataset Import

The analyst app can import a CSV directly from a Kaggle dataset.

## Setup
Install the Kaggle package:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Authenticate with one of these options:

```powershell
kaggle auth login
```

Or set credentials in `.env`:

```text
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_api_key
```

You can create a Kaggle API token from Kaggle account settings. The official token file is usually named `kaggle.json`.

## Run
Import the first CSV-like file from a dataset:

```powershell
.\.venv\Scripts\python.exe -m ui.cli_app --kaggle owner/dataset-slug
```

Import a specific file:

```powershell
.\.venv\Scripts\python.exe -m ui.cli_app --kaggle owner/dataset-slug --kaggle-file train.csv
```

Run a question immediately after import:

```powershell
.\.venv\Scripts\python.exe -m ui.cli_app --kaggle owner/dataset-slug --kaggle-file train.csv --question "What is the total revenue?"
```

Downloaded Kaggle files are stored under `artifacts/kaggle_downloads/`.
