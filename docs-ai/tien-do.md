# Tiến độ & Bàn giao Trạng thái - Market Sentinel

## 1. Đã xong (Completed & Verified)
- [x] Khởi tạo dự án độc lập tại `/home/jeromi/jerome-lab/projects/market-sentinel`
- [x] Thiết lập virtual environment `.venv` với Python 3.14, cài đặt `pytest`, `pydantic`, `httpx`, `beautifulsoup4`, `lxml`
- [x] Hoàn thiện bộ nhớ AI Vibe Coding (`docs-ai/tong-quan.md`, `quyet-dinh.md`, `kien-truc.md`, `tien-do.md`)
- [x] **Task 1: Domain Schemas & Parsers (Mock-First)**
  * `ProductItem`, `StockStatus`, `PriceDelta` bằng Pydantic v2.
  * Parser `EcommerceCatalogParser` cô lập card lỗi, parse chuẩn tiền tệ đa quốc gia (USD, GBP, EUR, VND).
  * Đạt 10/10 unit tests.
- [x] **Task 2: Resilient Collector**
  * `ResilientCollector` dùng `httpx`: User-Agent rotation, exponential backoff with jitter on 429/5xx, rate limiting throttle.
  * Đạt 6/6 unit tests với httpx MockTransport.
- [x] **Task 3: SQLite Time-Series Repository & Delta Service**
  * `SQLiteProductRepository` (WAL mode, foreign keys, parameterized queries, price history time-series).
  * `SentinelService`: so sánh snapshot cũ vs mới, tính delta %, sinh event `PRICE_DROP`, `PRICE_HIKE`, `RESTOCK`.
  * Integration tests đạt 100%.
- [x] **Task 4: Notifier & CLI Execution**
  * `TelegramNotifier` (Markdown/HTML template, dry-run mode).
  * `DataExporter` (CSV / JSON).
  * `src/cli.py` với 4 lệnh: `scrape`, `export`, `history`, `status`.
  * Đã test cào trực tiếp live benchmark trên `books.toscrape.com` (11 sản phẩm được lưu vào SQLite và export ra CSV).
- [x] **Task 5: Packaging & Portfolio Deliverables**
  * `Dockerfile` + `docker-compose.yml`.
  * `README.md` chuẩn công nghiệp có kiến trúc và hướng dẫn.
  * `PROPOSAL_TEMPLATE.md` với 2 mẫu bid Upwork/Freelance và mẹo chốt deal.
  * Toàn bộ test suite: **22/22 passed in 1.58s**.

## 2. Chưa xong (Pending Next)
- [ ] Jerome tùy chọn kết nối live Telegram Bot token vào file `.env` nếu muốn test nhận tin nhắn trực tiếp trên điện thoại.
- [ ] Jerome quay video/GIF 45s chạy lệnh CLI để gắn vào README / Upwork profile.

## 3. Đang vướng & Những cách đã thử thất bại (Blockers & Failed Attempts)
- **Lỗi Accept-Encoding gzip thô:** Lúc đầu thêm `"Accept-Encoding": "gzip, deflate, br"` vào headers của httpx khiến httpx bỏ qua bước tự động giải nén (auto-decompress), làm text trả về là binary gzip.
  * **Cách xử lý triệt để:** Bỏ manual `Accept-Encoding`, để httpx tự đàm phán và giải nén transparently. Đã fix và test live thành công.
- **Lỗi Foreign Key SQLite:** Trong test repo, gọi `record_snapshot` trước khi chèn product vào bảng `products` dính lỗi khóa ngoại.
  * **Cách xử lý:** Luôn đảm bảo Product đã tồn tại trước khi ghi snapshot history (đúng chuẩn toàn vẹn dữ liệu).
