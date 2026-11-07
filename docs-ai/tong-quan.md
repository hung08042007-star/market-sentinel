# Tổng quan Dự án: Market Sentinel

## 1. Mục đích & Phạm vi
- **Dự án:** Market Sentinel (Resilient E-Commerce Scraping & Market Intelligence Engine).
- **Mục tiêu:** Hệ thống cào dữ liệu sản phẩm tự động, chống chặn (anti-block), chuẩn hóa dữ liệu với Zero-Trust Pydantic schema, lưu vết biến động giá/tồn kho vào SQLite và tự động phát cảnh báo (Telegram/CSV).
- **Tech Stack:** Python 3.14, `httpx`, `beautifulsoup4`, `lxml`, `pydantic` v2, `sqlite3`, `pytest`.

## 2. Cấu trúc Thư mục
```text
src/
├── collector/     # Tầng 1: HTTP Client, Anti-bot headers, Rate Limiting, Retries
├── domain/        # Tầng 2: Pydantic schemas, Data Normalization, Business Delta
├── repository/    # Tầng 3: SQLite WAL time-series storage, migrations
├── notifier/      # Dispatcher: Telegram bot alert, CSV/JSON exporter
└── cli.py         # Entrypoint dòng lệnh CLI
tests/
├── fixtures/      # Raw HTML snapshots, mock server payloads, malformed edge cases
├── unit/          # Unit tests cho từng tầng riêng biệt
└── integration/   # End-to-end scraper & delta alert tests
docs-ai/           # AI Memory: tong-quan, quyet-dinh, kien-truc, tien-do
```

## 3. Lệnh Vận hành Chuẩn
- **Kích hoạt Virtualenv:** `source .venv/bin/activate` (hoặc dùng đường dẫn trực tiếp `.venv/bin/python`)
- **Chạy Test:** `.venv/bin/pytest tests/ -v`
- **Chạy Scraper CLI (Dry Run):** `.venv/bin/python -m src.cli scrape --url <URL> --dry-run`
- **Chạy Theo dõi & Alert:** `.venv/bin/python -m src.cli monitor --config config.yaml`
