# Sổ tay Quyết định Kiến trúc (ADR) - Market Sentinel

Tài liệu này ghi lại các lựa chọn kỹ thuật quan trọng và lý do. Mọi phiên AI tiếp theo phải tuân thủ, không tự ý đảo ngược.

---

### ADR-001: Kiến trúc 3 tầng phân tách nghiêm ngặt (Collector -> Domain/Parser -> Repository)
- **Ngày:** 07/11/2026
- **Bối cảnh:** Các script cào web thông thường nhồi nhét tải HTML, parse BeautifulSoup, chèn SQL và in ra terminal trong cùng một file, khiến code giòn (brittle) và không thể test tự động.
- **Quyết định:** Tách biệt 3 tầng:
  1. `Collector`: Chỉ fetch raw HTTP với retry, backoff và rate limit. Không parse HTML.
  2. `Domain/Parser`: Parse HTML ra Pydantic models. Không chạm database hay HTTP.
  3. `Repository`: Chỉ quản lý persistence vào SQLite. Không biết data đến từ đâu.
- **Lý do không chọn giải pháp khác:** Không dùng monolithic script vì khách hàng freelance yêu cầu code bảo trì được, dễ thay đổi target nguồn mà không phải viết lại từ đầu.
- **Hệ quả / Ràng buộc:** Mỗi tầng phải test độc lập bằng mocks/fixtures trước khi ghép.

---

### ADR-002: Zero-Trust Data Ingestion qua Pydantic Schema
- **Ngày:** 07/11/2026
- **Bối cảnh:** Website nguồn thường thay đổi layout đột ngột, chèn honeypot, hoặc trả về mã Captcha 200 OK với HTML rác, dẫn đến dữ liệu bẩn tràn vào cơ sở dữ liệu.
- **Quyết định:** Mọi item cào được bắt buộc phải pass qua Pydantic model (`ProductItem`) với validation nghiêm ngặt: chuẩn hóa giá tiền sang float (xóa ký tự $, đ, dấu phẩy), kiểm tra độ dài title, enum cho trạng thái kho (`IN_STOCK`, `OUT_OF_STOCK`, `UNKNOWN`).
- **Lý do không chọn giải pháp khác:** Không dùng bare dictionary vì lỗi `KeyError` lúc runtime sẽ làm crash toàn bộ batch cào.
- **Hệ quả / Ràng buộc:** Dữ liệu lỗi schema sẽ bị catch thành `InvalidItemRecord` và lưu log kiểm toán thay vì làm sập pipeline.

---

### ADR-003: Resilient HTTP Client với Exponential Backoff + Jitter
- **Ngày:** 07/11/2026
- **Bối cảnh:** Các server e-commerce thường trả mã 429 (Too Many Requests) hoặc 503 khi phát hiện lưu lượng crawler.
- **Quyết định:** Sử dụng `httpx.Client` với custom retry decorator / handler: Retry tối đa 3 lần cho các mã [429, 500, 502, 503, 504], tính delay theo `base * (2 ** attempt) + uniform(0, 1)` (Full Jitter), xoay vòng User-Agent từ danh sách browser phổ biến.
- **Lý do không chọn giải pháp khác:** Không spam request cố định vì sẽ bị ban IP ngay lập tức.
- **Hệ quả / Ràng buộc:** Toàn bộ outbound network calls bắt buộc đi qua lớp `ResilientCollector`.

---

### ADR-004: SQLite WAL Mode cho Delta Detection (Price Tracking)
- **Ngày:** 07/11/2026
- **Bối cảnh:** Cần lưu snapshot giá theo thời gian để so sánh xem giá có giảm/tăng không và cảnh báo.
- **Quyết định:** Dùng SQLite nhúng với chế độ `PRAGMA journal_mode=WAL;` và `PRAGMA busy_timeout=5000;`. Lưu 2 bảng: `products` (thông tin hiện tại) và `price_snapshots` (lịch sử giá kèm timestamp).
- **Lý do không chọn giải pháp khác:** Không dùng PostgreSQL để khách hàng có thể chạy độc lập không cần cài thêm DB server cồng kềnh; khi cần scale thì interface Repository vẫn giữ nguyên.
