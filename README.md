# Market Sentinel 🛡️

> **Resilient E-Commerce Scraping & Market Intelligence Engine**  
> Built with Python 3, Pydantic v2, SQLite (WAL mode), and Telegram Dispatcher.

[![Tests](https://img.shields.io/badge/tests-22%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.14-blue.svg)]()
[![Architecture](https://img.shields.io/badge/architecture-3--Tier%20Layered-orange.svg)]()
[![Data Validation](https://img.shields.io/badge/validation-Zero--Trust%20Pydantic-purple.svg)]()

---

## 🎯 The Problem This Solves

Most freelance scraping projects crash after 48 hours because:
1. **Target anti-bot mechanisms:** Requests get blocked with HTTP 429 / 403 due to naive rapid-fire polling.
2. **Brittle HTML extraction:** Minor UI or CSS class changes break unvalidated dictionaries, injecting nulls or crashing the pipeline.
3. **No Time-Series Intelligence:** Data is dumped into flat files without tracking historical price variations, making it impossible to detect discounts or restocks.

**Market Sentinel** solves all three with an industrial-grade, defensive architecture.

---

## 🏗️ Architecture

```text
[Target Catalog URL]
        │
        ▼
[Resilient Collector]  ◄── User-Agent Rotation, Full-Jitter Backoff (429/5xx), Rate Limiting
        │ (Raw HTML / Response)
        ▼
[Domain & Parser]      ◄── CSS/DOM Extraction + Zero-Trust Pydantic v2 Normalization
        │ (Clean ProductItem)
        ▼
[Sentinel Service]     ◄── Price & Stock Delta Detection (Price Drop, Hike, Restock)
        │
        ├──► [SQLite Repository]  ◄── WAL Mode, Time-Series Snapshots (`price_history`)
        │
        └──► [Notifier & Export]  ◄── Telegram Alert Bot, CSV / JSON Exporters
```

---

## ⚡ Quickstart

### 1. Local Setup
```bash
# Clone and enter directory
cd projects/market-sentinel

# Create virtualenv and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Tests (Zero-Trust Test Suite)
```bash
pytest tests/ -v
# 22 passed in 1.5s
```

### 3. Crawl a Catalog
```bash
# Scrape catalog and store snapshots in SQLite
python -m src.cli scrape --url "https://books.toscrape.com/catalogue/category/books/travel_2/index.html" --dry-run
```

Output:
```text
🚀 Scanning target: https://books.toscrape.com/catalogue/category/books/travel_2/index.html
=================================================================
📊 CRAWL REPORT: https://books.toscrape.com/catalogue/category/books/travel_2/index.html
=================================================================
• Total Cards Found:    11
• Successfully Parsed:  11
• Malformed/Ignored:    0
• Price Deltas Detected:0
• Fetch Latency:        1465.5 ms
-----------------------------------------------------------------
Top 5 Scraped Items:
  1. [IN_STOCK] It's Only the Himalayas                       | 45.17 GBP
  2. [IN_STOCK] Full Moon over Noah’s Ark: An Odyssey to Moun | 49.43 GBP
  3. [IN_STOCK] See America: A Celebration of Our National Pa | 48.87 GBP
...
✅ Crawl snapshot committed to database.
```

### 4. Check Status & Export
```bash
# Database status
python -m src.cli status

# Export to CSV
python -m src.cli export --format csv --output data/products.csv

# Inspect time-series price trajectory for a specific SKU
python -m src.cli history --sku "1000-places-to-see-before-you-die_1"
```

---

## 📦 Docker Deployment

```bash
docker compose build
docker compose run --rm sentinel status
```

---

## 🛡️ Key Technical Decisions (ADR)
* **Zero-Trust Schemas (`src/domain/models.py`):** Automatically cleans currency symbols (`$`, `£`, `€`, `₫`), removes dangerous HTML tags, and converts prices into standardized floats.
* **Full-Jitter Backoff (`src/collector/client.py`):** Calculates backoff delay as `base * (2 ** attempt) + uniform(0.1, 0.9)`, preventing "thundering herd" bot flags.
* **Fail-Safe Extraction (`src/domain/parser.py`):** Malformed product cards are isolated into `ParseReport.warnings` without halting the entire scraping job.
