# 💼 Freelance Proposal Template: Web Scraping & Automation

Tài liệu này dùng để copy & tùy biến khi m bid các job cào dữ liệu, monitor giá đối thủ hoặc automation trên Upwork / Fiverr / Freelancer.

---

## 🎯 Mẫu Bid 1: Dành cho job "Scrape data from Website X into CSV / Google Sheets"

**Tiêu đề Job thường gặp:**  
*"Need Python script to scrape products/prices from e-commerce site"*, *"Web scraper for real estate listings"*

```markdown
Hi [Client Name / there],

Most scraping scripts break after 48 hours because they don't account for dynamic layout changes, rate limits, or subtle bot blocks (429/403 errors).

I specialize in building resilient, production-ready data pipelines that run reliably without manual intervention.

Here is how I will deliver your project:
1. Resilient Extraction: Implemented with custom User-Agent rotation, exponential backoff with full jitter, and per-host rate limiting so your crawler doesn't get blocked.
2. Zero-Trust Data Cleaning: Clean, typed data (Pydantic schema). Automatically strips currency symbols, normalizes date/pricing numbers, and handles missing fields without crashing.
3. Automated Export: Delivered in clean CSV, JSON, or direct integration to Google Sheets / SQLite database.
4. Packaging: Delivered with a clean 1-line run command or Docker container so you can run it on any server or schedule it via cron.

You can check out a live architecture demo of a resilient crawler I engineered here:
[Link GitHub Repo / Video demo ngắn của m]

I can have a working prototype of your target site ready for review within 24 hours. Could you share the target URL and the specific fields you need extracted?

Best regards,  
Jerome
```

---

## 🎯 Mẫu Bid 2: Dành cho job "Competitor Price Tracking & Telegram Alert"

**Tiêu đề Job thường gặp:**  
*"Monitor competitor prices daily and alert on price drops"*, *"Stock and price alert bot for shop"*

```markdown
Hi [Client Name / there],

Building a reliable price monitor requires two things: clean historical data storage (so you can accurately detect discounts) and fail-safe alerting (so you only get notified about real events, not false positives).

I have a battle-tested architecture that does exactly this:
- Time-Series Price Tracking: Stores every snapshot with timestamps in SQLite (WAL mode) to track historical trends.
- Smart Delta Detection: Automatically calculates percentage changes and triggers alerts for events like PRICE_DROP, RESTOCK, or OUT_OF_STOCK.
- Instant Alerting: Formatted Telegram alerts with product links and percentage drop directly to your channel/chat.
- Resilient Engine: Automatically recovers from 429 rate-limiting with exponential backoff.

I can set this up for your target stores and have the Telegram bot live in 1-2 days. 

Let's discuss which sites you want to monitor and your preferred alert frequency!

Cheers,  
Jerome
```

---

## 💡 Bí kíp chiến thắng khi bid job mới (Zero-Review Profile):
1. **Gửi kèm bằng chứng chạy thật (Proof of Work):** Đính kèm ảnh terminal test 22/22 passed hoặc video quay màn hình 45s chạy lệnh `market-sentinel scrape`. Khách hàng thấy terminal xanh lè + kết quả ra bảng biểu rõ ràng sẽ tin tưởng hơn 100 người chỉ copy prompt ChatGPT.
2. **Hỏi 1 câu kỹ thuật vào vấn đề:** Ví dụ: *"Trang này có dùng Cloudflare turnstile hay chỉ cần session/header rotation?"* hoặc *"Bạn muốn cảnh báo khi giá giảm bao nhiêu %?"* -> Khách sẽ nhận ra m thực sự hiểu bài toán.
