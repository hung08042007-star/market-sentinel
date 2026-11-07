# Hướng dẫn Kiến trúc - Market Sentinel

## 1. Luồng dữ liệu (Data Flow)
```text
[Target URL / CLI] 
       │
       ▼
[Collector: ResilientCollector]  <-- Quản lý Session, Retries, Exponential Backoff, User-Agent Pool
       │ (Raw HTML / Response)
       ▼
[Parser: BaseParser -> EcommerceParser]  <-- Trích xuất DOM bằng BeautifulSoup/CSS Selector
       │ (Raw Dict)
       ▼
[Domain Validator: ProductItem Schema]   <-- Pydantic v2 chuẩn hóa giá, làm sạch HTML tags, validate enum
       │ (Clean Domain Model)
       ▼
[Service: SentinelService]        <-- So sánh snapshot cũ trong DB để tính Delta (giảm giá, đổi kho)
       │
       ├──► [Repository: SQLiteProductRepo]  <-- Lưu trữ snapshot, cập nhật giá hiện tại (WAL mode)
       │
       └──► [Dispatcher / Notifier]          <-- Bắn thông báo Telegram / Console / CSV Export
```

## 2. Quy ước các tầng (Layer Contracts)

### Tầng 1: Collector (`src/collector/`)
- Trách nhiệm: Fetch an toàn từ internet.
- Input: `url: str, params: Optional[dict]`
- Output: `FetchResult(url, status_code, html_content, latency_ms, headers)`
- Ràng buộc: Xử lý timeout, 429, retry logic; không parse DOM; ném exception `ScraperBlockError` hoặc `NetworkTimeoutError` rõ ràng.

### Tầng 2: Domain & Parser (`src/domain/`)
- Trách nhiệm: Parse cấu trúc DOM và bảo đảm tính hợp lệ (Zero-Trust Data).
- Models:
  * `ProductItem`: `sku: str, title: str, current_price: float, original_price: Optional[float], currency: str, stock_status: StockStatus, url: str, captured_at: datetime`
  * `PriceDelta`: `product_id: str, old_price: float, new_price: float, diff_percentage: float, event_type: DeltaEvent`
- Ràng buộc: Làm sạch text, bỏ ký tự lạ, chuyển đổi số an toàn, không chứa logic SQL hay HTTP.

### Tầng 3: Repository (`src/repository/`)
- Trách nhiệm: Lưu trữ lịch sử và trạng thái.
- Interface: `ProductRepository(Protocol)`
  * `upsert_product(item: ProductItem) -> None`
  * `get_latest_price(sku: str) -> Optional[float]`
  * `record_snapshot(sku: str, price: float, stock: StockStatus) -> None`
  * `get_price_history(sku: str, days: int = 30) -> list[PriceSnapshot]`
- Ràng buộc: Dùng SQL Parameterized Queries (`?`), không cộng chuỗi SQL để chống SQL Injection.

### Tầng 4: Dispatcher / Notifier (`src/notifier/`)
- Trách nhiệm: Gửi cảnh báo khi có sự kiện (Giảm giá vượt ngưỡng, Hàng về kho).
- Channels: Telegram Markdown format, Console logger, CSV stream.

## 3. Quy ước Lỗi & Result Envelope
- Mọi tác vụ hàng loạt trả về `BatchCrawlResult`:
  ```json
  {
    "total_targets": 20,
    "successful_items": 19,
    "failed_targets": 1,
    "deltas_detected": 3,
    "errors": [
      { "url": "https://...", "reason": "Rate limited 429 after 3 retries" }
    ]
  }
  ```
