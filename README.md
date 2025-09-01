# Singapore HSA Guidance Scraper & Database System

Production-grade ingestion and search for all guidance documents from Singapore Health Sciences Authority (HSA).

## Features
- Async scraping of Therapeutic Products & Medical Devices guidance
- Robots.txt compliance, rate limiting, retries, deduplication
- PostgreSQL schema with full-text search, file tracking, and BI-ready views
- File download and text extraction (PDF, DOC/DOCX, XLS/XLSX)
- CLI tools for search, status, cleanup, and network tests
- Structured JSON logging
- Unit & integration tests with VCR cassettes

## Setup
1. **Install dependencies:**
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Configure environment:**
   Create a `.env` file (or set env vars):
   ```ini
   PGHOST=localhost
   PGPORT=5432
   PGDATABASE=quriousri
   PGUSER=fda_user
   PGPASSWORD=your_password
   ```
3. **Bootstrap database:**
   ```sh
   python enhanced_db_setup.py
   ```

## Usage
- **Dry-run crawl:**
  ```sh
  python hsa_scraper.py --division all --dry-run
  ```
- **Full crawl:**
  ```sh
  python hsa_scraper.py --division medical-devices --concurrency 6
  ```
- **Extract texts:**
  ```sh
  python file_extract.py --only-pending
  ```
- **Search CLI:**
  ```sh
  python search_cli.py --q "clinical evaluation" --division "Medical Devices" --type pdf --from 2020-01-01
  ```
- **DB status:**
  ```sh
  python db_status.py
  ```
- **Clear database (dangerous):**
  ```sh
  python clear_database.py --drop-all --danger
  python clear_database.py --purge-files --danger
  ```
- **Network test:**
  ```sh
  python network_test.py
  ```

## Cron Example
```
0 3 * * * cd /path/to/project && . .venv/bin/activate && python hsa_scraper.py --division all
```

## Troubleshooting
- **Missing dependencies:** Run `pip install -r requirements.txt`.
- **DB connection errors:** Check `.env` and PostgreSQL status.
- **Extraction failures:** See `db_status.py` for skipped/failed files.
- **Rate limits/429:** Scraper will back off and retry automatically.

## Tests
- **Run all tests:**
  ```sh
  pytest
  ```
- **Integration (live dry-run):**
  ```sh
  pytest --vcr-record=once
  ```

## Directory Structure
- `data/hsa/{division}/{yyyy}/` – Downloaded files
- `tests/` – Unit and integration tests

## License
MIT
