import sqlite3
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.advisor.businessman import BusinessmanAdvisor
from src.domain.models import DeltaEvent, PriceDelta

def format_vnd(amount):
    return f"{amount:,}₫".replace(",", ".")

def build_action_card(item):
    is_drop = item["delta"]["type"] == "PRICE_DROP"
    card_class = "card-danger" if is_drop else "card-success"
    percent_color = "var(--danger)" if item["delta"]["percent"] < 0 else "var(--success)"
    sign = "+" if item["delta"]["percent"] > 0 else ""
    counter_price = int(item["advice"]["recommended_counter_price"])

    return f"""
        <div class="action-card {card_class}" id="card-{item['sku']}">
          <div class="action-card-top">
            <div>
              <span class="action-badge {item['delta']['badge_class']}">{item['delta']['badge']}</span>
              <div class="product-title-large">{item['title']}</div>
              <div class="product-sublink">
                <span class="platform-tag">{item['platform']}</span>
                <span>Mã SKU: <strong>{item['sku']}</strong></span> &bull; 
                <span>Giá shop mình: <strong style="color:#fff;">{format_vnd(item['shop_price'])}</strong> (Vốn: {format_vnd(item['cost_price'])})</span> &bull;
                <a href="{item['url']}" target="_blank" style="color:var(--accent); text-decoration:none;">Xem link shop đối thủ ↗</a>
              </div>
            </div>

            <div class="price-movement-box">
              <span class="price-old">{format_vnd(item['delta']['old_price'])}</span>
              <span style="color: var(--text-subtle);">&rarr;</span>
              <span class="price-new">{format_vnd(item['delta']['new_price'])}</span>
              <span style="color: {percent_color}; font-weight:700;">
                ({sign}{item['delta']['percent']:.1f}%)
              </span>
            </div>
          </div>

          <!-- AI Strategic Guidance Box -->
          <div class="ai-advisor-panel">
            <div class="ai-intel-side">
              <div class="ai-intel-header">
                <span>🧠 AI Tình Báo Giá Phân Tích:</span>
              </div>
              <div>&bull; <strong>Ý đồ đối thủ:</strong> {item['advice']['intent_diagnosis']}</div>
              <div>&bull; <strong>Kế sách phản đòn:</strong> {item['advice']['tactical_action']}</div>
              <div style="color: var(--text-muted); font-size: 12px; margin-top: 2px;">
                &bull; <strong>Đòn đánh phi giá (Quà/Combo):</strong> {item['advice']['executive_briefing']}
              </div>
            </div>

            <div class="ai-decision-side">
              <div class="counter-label">Giá phản công tối ưu</div>
              <div class="counter-number">{format_vnd(counter_price)}</div>
              <div class="margin-tag">Biên lãi giữ được: ~{item['advice']['projected_margin_pct']:.1f}%</div>
            </div>
          </div>

          <!-- Bottom Actions -->
          <div class="action-card-footer">
            <button class="btn btn-outline" onclick="toggleChart('{item['sku']}')">
              📈 So kèo lịch sử giá 7 ngày
            </button>
            <div style="display:flex; gap:8px;" id="action-btns-{item['sku']}">
              <button class="btn" onclick="ignoreDelta('{item['sku']}')">
                Bỏ qua
              </button>
              <button class="btn btn-primary" onclick="applyCounterPrice('{item['sku']}', {counter_price})">
                ✅ Áp dụng giá {format_vnd(counter_price)} ngay
              </button>
            </div>
          </div>

          <!-- Drawer Chart -->
          <div class="chart-drawer" id="chart-wrap-{item['sku']}">
            <canvas id="chart-{item['sku']}"></canvas>
          </div>
        </div>"""

def build_table_row(p):
    has_action = "true" if p["delta"] else "false"
    if p["delta"] and p["delta"]["type"] == "PRICE_DROP":
        comp_price_color = "var(--danger)"
        market_eval = '<span style="color:var(--danger); font-size:12px; font-weight:600;">🔴 Đang bị phá giá</span>'
    elif p["delta"] and p["delta"]["type"] == "PRICE_HIKE":
        comp_price_color = "var(--success)"
        market_eval = '<span style="color:var(--success); font-size:12px; font-weight:600;">🟢 Cơ hội hốt khách</span>'
    else:
        comp_price_color = "#cbd5e1"
        market_eval = '<span style="color:var(--text-subtle); font-size:12px;">⚪ Giá cân bằng</span>'

    return f"""
              <tr data-sku="{p['sku']}" data-action="{has_action}">
                <td style="font-family: var(--mono); font-size: 12px; color: var(--text-muted);">{p['sku']}</td>
                <td style="color: #fff; font-weight: 500;">
                  <div style="max-width: 290px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{p['title']}</div>
                  <div style="font-size: 11px; color: var(--text-subtle);">Đã bán: {p['sold_count']} &bull; Đánh giá: {p['rating']}★</div>
                </td>
                <td><span class="platform-tag">{p['platform']}</span></td>
                <td style="font-family: var(--mono); font-weight: 600; color: #fff;" id="shop-price-{p['sku']}">
                  {format_vnd(p['shop_price'])}
                </td>
                <td style="font-family: var(--mono); font-weight: 700; color: {comp_price_color};">
                  {format_vnd(p['current_price'])}
                </td>
                <td>
                  {market_eval}
                </td>
                <td>
                  <span style="color: var(--success); font-size: 12px;">● Sẵn kho</span>
                </td>
                <td style="text-align: right;">
                  <a href="{p['url']}" target="_blank" class="btn" style="padding: 2px 8px; font-size: 11px;">Mở ↗</a>
                </td>
              </tr>"""

def generate_fashion_dashboard():
    out_dir = "/home/jeromi/jerome-lab/projects/market-sentinel/web"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "index.html")

    base_date = datetime.now(timezone.utc) - timedelta(days=6)
    
    fashion_catalog = [
        {
            "sku": "TEE-OVS-260-BLK",
            "title": "Áo Thun Heavyweight Oversize 260gsm (Local Brand Unisex - Đen)",
            "url": "https://shopee.vn/ao-thun-heavyweight-oversize-260gsm-unisex-local-brand-i.849201.294104",
            "platform": "Shopee",
            "current_price": 189000,
            "shop_price": 250000,
            "cost_price": 110000,
            "currency": "₫",
            "stock_status": "in_stock",
            "rating": 4.9,
            "sold_count": "14.2k",
            "last_scraped_at": "Hôm nay, 08:15",
            "delta": {
                "type": "PRICE_DROP",
                "old_price": 249000,
                "new_price": 189000,
                "diff": -60000,
                "percent": -24.1,
                "badge": "🚨 ĐỐI THỦ PHÁ GIÁ",
                "badge_class": "badge-danger"
            },
            "timeline": [
                {"date": (base_date + timedelta(days=0)).strftime("%d/%m"), "competitor": 249000, "my_shop": 250000},
                {"date": (base_date + timedelta(days=2)).strftime("%d/%m"), "competitor": 249000, "my_shop": 250000},
                {"date": (base_date + timedelta(days=4)).strftime("%d/%m"), "competitor": 220000, "my_shop": 250000},
                {"date": (base_date + timedelta(days=6)).strftime("%d/%m"), "competitor": 189000, "my_shop": 250000},
            ],
            "advice": {
                "threat_level": "CRITICAL",
                "intent_diagnosis": "Đối thủ Shop X (120k followers) đang chạy Flash Sale xả kho tồn mùa trước để xoay vòng vốn và giật top ngành hàng Áo thun nam.",
                "recommended_counter_price": 185000,
                "projected_margin_pct": 40.5,
                "tactical_action": "Hạ giá đối ứng về 185.000₫ (thấp hơn đối thủ 4.000₫) để đoạt lại huy hiệu 'Rẻ Vô Địch' của sàn Shopee. Biên lãi vẫn an toàn ở mức 40.5% nhờ giá vốn xưởng 110.000₫.",
                "executive_briefing": "Kèm quà tặng 1 đôi tất dệt kim trị giá 5.000₫ cho đơn từ 2 áo để giữ giá trị giỏ hàng (AOV) không bị sụt giảm theo giá."
            }
        },
        {
            "sku": "JEAN-WID-BLU-02",
            "title": "Quần Jean Baggy Ống Suông Rộng Unisex (Denim 13oz Cao Cấp)",
            "url": "https://tiktok.com/@streetwear_studio/video/quan-jean-baggy-ong-suong-denim",
            "platform": "TikTok Shop",
            "current_price": 460000,
            "shop_price": 390000,
            "cost_price": 210000,
            "currency": "₫",
            "stock_status": "in_stock",
            "rating": 4.8,
            "sold_count": "8.5k",
            "last_scraped_at": "Hôm nay, 08:20",
            "delta": {
                "type": "PRICE_HIKE",
                "old_price": 390000,
                "new_price": 460000,
                "diff": 70000,
                "percent": 17.9,
                "badge": "📈 CƠ HỘI TĂNG LÃI",
                "badge_class": "badge-success"
            },
            "timeline": [
                {"date": (base_date + timedelta(days=0)).strftime("%d/%m"), "competitor": 390000, "my_shop": 390000},
                {"date": (base_date + timedelta(days=2)).strftime("%d/%m"), "competitor": 390000, "my_shop": 390000},
                {"date": (base_date + timedelta(days=4)).strftime("%d/%m"), "competitor": 420000, "my_shop": 390000},
                {"date": (base_date + timedelta(days=6)).strftime("%d/%m"), "competitor": 460000, "my_shop": 390000},
            ],
            "advice": {
                "threat_level": "OPPORTUNITY",
                "intent_diagnosis": "Đối thủ đang tắc biên nguồn vải Jean hoặc cháy hàng các size hot (L, XL), phải nâng giá để hạn chế số đơn bị trễ giao hàng.",
                "recommended_counter_price": 420000,
                "projected_margin_pct": 50.0,
                "tactical_action": "Tăng nhẹ giá lên 420.000₫ (vẫn rẻ hơn đối thủ 40.000₫) để thu thêm 30.000₫ tiền lãi ròng trên mỗi chiếc bán ra mà khách vẫn chọn mua bên mình.",
                "executive_briefing": "Bật hashtag 'Hàng sẵn kho - Giao hỏa tốc 2h' trên Livestream TikTok để vợt sạch lượng khách đang thất vọng vì giá cao bên đối thủ."
            }
        },
        {
            "sku": "JKT-BMB-WTR-03",
            "title": "Áo Khoác Gió Bomber 2 Lớp Chống Nước (Trượt Nước Gân Quả Trám)",
            "url": "https://shopee.vn/ao-khoac-gio-bomber-chong-nuoc-localbrand-i.51203.91823",
            "platform": "Shopee",
            "current_price": 350000,
            "shop_price": 350000,
            "cost_price": 175000,
            "currency": "₫",
            "stock_status": "in_stock",
            "rating": 4.9,
            "sold_count": "5.3k",
            "last_scraped_at": "Hôm nay, 07:50",
            "delta": None,
            "timeline": [
                {"date": (base_date + timedelta(days=0)).strftime("%d/%m"), "competitor": 350000, "my_shop": 350000},
                {"date": (base_date + timedelta(days=3)).strftime("%d/%m"), "competitor": 350000, "my_shop": 350000},
                {"date": (base_date + timedelta(days=6)).strftime("%d/%m"), "competitor": 350000, "my_shop": 350000},
            ]
        },
        {
            "sku": "POL-PIQ-NAV-04",
            "title": "Áo Polo Pique Cotton Phối Cổ Bo Dệt (Form Regular Nam Tính)",
            "url": "https://lazada.vn/products/ao-polo-pique-cotton-nam-co-bo-i829104.html",
            "platform": "Lazada",
            "current_price": 285000,
            "shop_price": 280000,
            "cost_price": 130000,
            "currency": "₫",
            "stock_status": "in_stock",
            "rating": 4.7,
            "sold_count": "3.1k",
            "last_scraped_at": "Hôm nay, 08:00",
            "delta": None,
            "timeline": [
                {"date": (base_date + timedelta(days=0)).strftime("%d/%m"), "competitor": 285000, "my_shop": 280000},
                {"date": (base_date + timedelta(days=3)).strftime("%d/%m"), "competitor": 285000, "my_shop": 280000},
                {"date": (base_date + timedelta(days=6)).strftime("%d/%m"), "competitor": 285000, "my_shop": 280000},
            ]
        },
        {
            "sku": "SHT-LIN-KHA-05",
            "title": "Quần Short Đũi Túi Hộp Co Giãn 4 Chiều (Mặc Nhà & Dạo Phố)",
            "url": "https://shopee.vn/quan-short-dui-nam-tui-hop-i.389104.18491",
            "platform": "Shopee",
            "current_price": 165000,
            "shop_price": 165000,
            "cost_price": 75000,
            "currency": "₫",
            "stock_status": "in_stock",
            "rating": 4.6,
            "sold_count": "9.8k",
            "last_scraped_at": "Hôm nay, 07:30",
            "delta": None,
            "timeline": [
                {"date": (base_date + timedelta(days=0)).strftime("%d/%m"), "competitor": 165000, "my_shop": 165000},
                {"date": (base_date + timedelta(days=3)).strftime("%d/%m"), "competitor": 165000, "my_shop": 165000},
                {"date": (base_date + timedelta(days=6)).strftime("%d/%m"), "competitor": 165000, "my_shop": 165000},
            ]
        },
        {
            "sku": "HD-FLC-GRY-06",
            "title": "Áo Hoodie Nỉ Bông Dày 380gsm Form Boxy (Streetwear Mùa Thu Đông)",
            "url": "https://tiktok.com/@localbrand_official/video/ao-hoodie-ni-bong-380gsm",
            "platform": "TikTok Shop",
            "current_price": 420000,
            "shop_price": 420000,
            "cost_price": 220000,
            "currency": "₫",
            "stock_status": "in_stock",
            "rating": 4.9,
            "sold_count": "6.2k",
            "last_scraped_at": "Hôm qua, 22:15",
            "delta": None,
            "timeline": [
                {"date": (base_date + timedelta(days=0)).strftime("%d/%m"), "competitor": 420000, "my_shop": 420000},
                {"date": (base_date + timedelta(days=3)).strftime("%d/%m"), "competitor": 420000, "my_shop": 420000},
                {"date": (base_date + timedelta(days=6)).strftime("%d/%m"), "competitor": 420000, "my_shop": 420000},
            ]
        },
        {
            "sku": "PNT-CAR-BLK-07",
            "title": "Quần Dài Túi Hộp Parachute Kaki Co Giãn (Dây Rút Gấu Ống Rộng)",
            "url": "https://shopee.vn/quan-kaki-tui-hop-parachute-i.190284.48192",
            "platform": "Shopee",
            "current_price": 320000,
            "shop_price": 320000,
            "cost_price": 160000,
            "currency": "₫",
            "stock_status": "in_stock",
            "rating": 4.8,
            "sold_count": "4.1k",
            "last_scraped_at": "Hôm nay, 06:40",
            "delta": None,
            "timeline": [
                {"date": (base_date + timedelta(days=0)).strftime("%d/%m"), "competitor": 320000, "my_shop": 320000},
                {"date": (base_date + timedelta(days=3)).strftime("%d/%m"), "competitor": 320000, "my_shop": 320000},
                {"date": (base_date + timedelta(days=6)).strftime("%d/%m"), "competitor": 320000, "my_shop": 320000},
            ]
        },
        {
            "sku": "SHT-CBN-RET-08",
            "title": "Áo Sơ Mi Cuban Collar Tay Ngắn Họa Tiết Retro (Chất Lụa Hàn Mát)",
            "url": "https://shopee.vn/ao-so-mi-cuban-collar-retro-lua-han-i.94012.38194",
            "platform": "Shopee",
            "current_price": 275000,
            "shop_price": 275000,
            "cost_price": 135000,
            "currency": "₫",
            "stock_status": "in_stock",
            "rating": 4.7,
            "sold_count": "2.9k",
            "last_scraped_at": "Hôm nay, 07:10",
            "delta": None,
            "timeline": [
                {"date": (base_date + timedelta(days=0)).strftime("%d/%m"), "competitor": 275000, "my_shop": 275000},
                {"date": (base_date + timedelta(days=3)).strftime("%d/%m"), "competitor": 275000, "my_shop": 275000},
                {"date": (base_date + timedelta(days=6)).strftime("%d/%m"), "competitor": 275000, "my_shop": 275000},
            ]
        }
    ]

    action_items = [p for p in fashion_catalog if p["delta"] is not None]
    total_tracked = len(fashion_catalog)
    safe_count = total_tracked - len(action_items)

    dashboard_data = {
        "summary": {
            "total_tracked": total_tracked,
            "drop_count": len([i for i in action_items if i["delta"]["type"] == "PRICE_DROP"]),
            "hike_count": len([i for i in action_items if i["delta"]["type"] == "PRICE_HIKE"]),
            "safe_count": safe_count,
            "min_margin": 15.0,
            "currency": "₫"
        },
        "action_items": action_items,
        "products": fashion_catalog
    }

    action_cards_html = "\n".join([build_action_card(item) for item in action_items])
    table_rows_html = "\n".join([build_table_row(p) for p in fashion_catalog])
    data_json = json.dumps(dashboard_data)

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Market Sentinel — Trợ lý Tình báo Giá Shop Thời Trang</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg: #090a0f;
      --card-bg: #12141c;
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover: rgba(255, 255, 255, 0.12);
      --primary: #4f46e5;
      --primary-hover: #4338ca;
      --accent: #38bdf8;
      --danger: #ef4444;
      --danger-bg: rgba(239, 68, 68, 0.12);
      --success: #10b981;
      --success-bg: rgba(16, 185, 129, 0.12);
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --text-subtle: #64748b;
      --mono: 'JetBrains Mono', monospace;
      --sans: 'Inter', system-ui, -apple-system, sans-serif;
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      line-height: 1.5;
      padding-bottom: 80px;
    }}

    /* Header */
    header {{
      background: #0f1118;
      border-bottom: 1px solid var(--card-border);
      padding: 12px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 40;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .brand-icon {{
      width: 38px;
      height: 38px;
      background: linear-gradient(135deg, #4f46e5, #0ea5e9);
      border-radius: 9px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
    }}
    .brand-text h1 {{
      font-size: 15.5px;
      font-weight: 700;
      letter-spacing: -0.3px;
    }}
    .brand-text p {{
      font-size: 12px;
      color: var(--text-muted);
    }}
    .header-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .live-status-pill {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: #10b981;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.25);
      padding: 4px 10px;
      border-radius: 999px;
    }}
    .status-dot {{
      width: 6px;
      height: 6px;
      background: #10b981;
      border-radius: 50%;
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
      0% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(0.9); }}
      100% {{ opacity: 1; transform: scale(1); }}
    }}

    .btn {{
      padding: 7px 14px;
      border-radius: 8px;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid var(--card-border);
      background: rgba(255, 255, 255, 0.05);
      color: var(--text);
      transition: all 0.15s ease;
      text-decoration: none;
    }}
    .btn:hover {{
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.2);
    }}
    .btn-primary {{
      background: var(--primary);
      border-color: var(--primary);
      color: #fff;
    }}
    .btn-primary:hover {{
      background: var(--primary-hover);
    }}
    .btn-tg {{
      background: #229ed9;
      border-color: #229ed9;
      color: #fff;
    }}
    .btn-tg:hover {{
      background: #1b87ba;
    }}
    .btn-outline {{
      background: transparent;
      border-color: rgba(255, 255, 255, 0.15);
      color: var(--text-muted);
    }}
    .btn-outline:hover {{
      color: #fff;
      border-color: rgba(255, 255, 255, 0.3);
    }}

    /* Main Container */
    main {{
      max-width: 1140px;
      margin: 0 auto;
      padding: 24px 20px;
      display: flex;
      flex-direction: column;
      gap: 26px;
    }}

    /* Interactive Guided Workflow Banner */
    .flow-guide-bar {{
      background: linear-gradient(90deg, rgba(79, 70, 229, 0.15) 0%, rgba(14, 165, 233, 0.15) 100%);
      border: 1px solid rgba(79, 70, 229, 0.3);
      border-radius: 10px;
      padding: 12px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    .flow-steps {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 12.5px;
    }}
    .flow-step-item {{
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--text-muted);
    }}
    .flow-step-item.active {{
      color: #fff;
      font-weight: 600;
    }}
    .step-num {{
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-family: var(--mono);
    }}
    .flow-step-item.active .step-num {{
      background: var(--primary);
      color: #fff;
    }}

    /* 1-Click Track URL Hero */
    .track-hero {{
      background: linear-gradient(135deg, #131622 0%, #0e1018 100%);
      border: 1px solid rgba(79, 70, 229, 0.25);
      border-radius: 12px;
      padding: 20px 22px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    }}
    .track-hero-title {{
      font-size: 15px;
      font-weight: 700;
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .track-hero-subtitle {{
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 12px;
    }}
    .track-bar-form {{
      display: flex;
      gap: 10px;
    }}
    .track-input {{
      flex: 1;
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 13px;
      color: #fff;
      outline: none;
      transition: border-color 0.2s;
    }}
    .track-input:focus {{
      border-color: var(--primary);
      box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.25);
    }}
    .sample-pill-group {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 10px;
      flex-wrap: wrap;
    }}
    .sample-pill {{
      font-size: 11.5px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      padding: 3px 10px;
      border-radius: 6px;
      cursor: pointer;
      color: var(--text-muted);
      transition: all 0.15s;
    }}
    .sample-pill:hover {{
      background: rgba(79, 70, 229, 0.2);
      border-color: var(--primary);
      color: #fff;
    }}

    /* 4 Commercial Metric Cards */
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
    }}
    .metric-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 16px 18px;
      display: flex;
      align-items: center;
      gap: 14px;
    }}
    .metric-icon {{
      width: 44px;
      height: 44px;
      border-radius: 9px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
    }}
    .metric-val {{
      font-size: 21px;
      font-weight: 700;
      letter-spacing: -0.5px;
      font-family: var(--mono);
    }}
    .metric-label {{
      font-size: 12px;
      color: var(--text-muted);
    }}

    /* Section Headers */
    .section-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }}
    .section-title {{
      font-size: 15.5px;
      font-weight: 700;
      letter-spacing: -0.3px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    /* Action Cards */
    .action-cards-grid {{
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .action-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      position: relative;
      transition: border-color 0.2s;
    }}
    .action-card.card-danger {{
      border-left: 4px solid var(--danger);
    }}
    .action-card.card-success {{
      border-left: 4px solid var(--success);
    }}

    .action-card-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 14px;
    }}
    .action-badge {{
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      letter-spacing: 0.4px;
      font-family: var(--mono);
      display: inline-block;
      margin-bottom: 6px;
    }}
    .badge-danger {{
      background: var(--danger-bg);
      color: var(--danger);
      border: 1px solid rgba(239, 68, 68, 0.3);
    }}
    .badge-success {{
      background: var(--success-bg);
      color: var(--success);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}
    .product-title-large {{
      font-size: 15.5px;
      font-weight: 600;
      color: #fff;
    }}
    .product-sublink {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 3px;
      display: flex;
      gap: 10px;
      align-items: center;
    }}
    .platform-tag {{
      background: rgba(255, 255, 255, 0.08);
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 11px;
      color: #cbd5e1;
    }}

    .price-movement-box {{
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 8px 14px;
      display: flex;
      align-items: center;
      gap: 10px;
      font-family: var(--mono);
      white-space: nowrap;
    }}
    .price-old {{
      text-decoration: line-through;
      color: var(--text-subtle);
      font-size: 13px;
    }}
    .price-new {{
      font-size: 18px;
      font-weight: 700;
      color: #fff;
    }}

    /* AI Commercial Advisor Box */
    .ai-advisor-panel {{
      background: rgba(14, 165, 233, 0.05);
      border: 1px solid rgba(14, 165, 233, 0.2);
      border-radius: 9px;
      padding: 16px;
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 18px;
    }}
    .ai-intel-side {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 13px;
    }}
    .ai-intel-header {{
      font-size: 11.5px;
      font-weight: 700;
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .ai-decision-side {{
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
    }}
    .counter-label {{
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
    }}
    .counter-number {{
      font-size: 22px;
      font-weight: 700;
      color: var(--accent);
      font-family: var(--mono);
      margin: 2px 0;
    }}
    .margin-tag {{
      font-size: 11px;
      color: var(--success);
      background: var(--success-bg);
      border: 1px solid rgba(16, 185, 129, 0.25);
      padding: 2px 8px;
      border-radius: 4px;
      font-weight: 600;
      font-family: var(--mono);
    }}

    .action-card-footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid var(--card-border);
    }}
    .chart-drawer {{
      height: 180px;
      margin-top: 14px;
      display: none;
    }}

    /* Catalog Table */
    .catalog-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
    }}
    .catalog-toolbar {{
      padding: 12px 18px;
      background: #0f1118;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }}
    .catalog-search {{
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 12.5px;
      color: #fff;
      outline: none;
      width: 260px;
    }}
    .catalog-search:focus {{
      border-color: var(--primary);
    }}
    .tab-filters {{
      display: flex;
      gap: 6px;
    }}
    .tab-btn {{
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      cursor: pointer;
      color: var(--text-muted);
      border: 1px solid transparent;
      user-select: none;
    }}
    .tab-btn.active {{
      background: rgba(255, 255, 255, 0.08);
      border-color: var(--card-border);
      color: #fff;
      font-weight: 600;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    thead th {{
      background: #0d0f15;
      text-align: left;
      padding: 10px 16px;
      font-size: 11px;
      color: var(--text-subtle);
      text-transform: uppercase;
      font-weight: 600;
      letter-spacing: 0.5px;
      border-bottom: 1px solid var(--card-border);
    }}
    tbody td {{
      padding: 11px 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
      color: var(--text-muted);
      vertical-align: middle;
    }}
    tbody tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
      color: #fff;
    }}

    /* Toast */
    #toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #1e1b4b;
      border: 1px solid #6366f1;
      color: #fff;
      padding: 12px 20px;
      border-radius: 9px;
      font-size: 13px;
      display: none;
      box-shadow: 0 10px 30px rgba(0,0,0,0.6);
      z-index: 100;
      animation: slideUp 0.25s ease-out;
    }}
    @keyframes slideUp {{
      from {{ transform: translateY(20px); opacity: 0; }}
      to {{ transform: translateY(0); opacity: 1; }}
    }}

    /* Telegram Modal */
    .modal-overlay {{
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(4px);
      z-index: 50;
      display: none;
      align-items: center;
      justify-content: center;
    }}
    .modal-card {{
      width: 460px;
      background: #17212b;
      border: 1px solid #2b5278;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.7);
    }}
    .tg-bubble {{
      background: #182533;
      border: 1px solid #2b5278;
      border-radius: 9px;
      padding: 14px;
      font-size: 13px;
      line-height: 1.5;
      margin: 14px 0;
    }}
  </style>
</head>
<body>

  <!-- Top Bar -->
  <header>
    <div class="brand">
      <div class="brand-icon">🛡️</div>
      <div class="brand-text">
        <h1>Market Sentinel</h1>
        <p>Trợ lý Tình báo Giá Shop Thời Trang & E-Commerce</p>
      </div>
    </div>

    <div class="header-actions">
      <div class="live-status-pill">
        <span class="status-dot"></span>
        <span>Đang canh giá 24/7 (Shopee / TikTok Shop / Lazada)</span>
      </div>
      <button class="btn btn-tg" onclick="openTelegramModal()">
        📱 Nhận tin Telegram
      </button>
      <button class="btn" onclick="exportData()">
        📥 Xuất Excel
      </button>
      <button class="btn btn-primary" onclick="triggerScan()">
        ⚡ Quét giá ngay
      </button>
    </div>
  </header>

  <main>
    <!-- Interactive Guided Workflow Banner for Customers -->
    <div class="flow-guide-bar">
      <div class="flow-steps">
        <div class="flow-step-item active">
          <span class="step-num">1</span>
          <span>Dán link đối thủ</span>
        </div>
        <span style="color: var(--text-subtle);">&rarr;</span>
        <div class="flow-step-item active">
          <span class="step-num">2</span>
          <span>AI phát hiện phá giá</span>
        </div>
        <span style="color: var(--text-subtle);">&rarr;</span>
        <div class="flow-step-item active">
          <span class="step-num">3</span>
          <span>Bấm 1 nút phản công giá</span>
        </div>
        <span style="color: var(--text-subtle);">&rarr;</span>
        <div class="flow-step-item">
          <span class="step-num">4</span>
          <span>Báo về Telegram mỗi sáng</span>
        </div>
      </div>
      <div style="font-size: 12px; color: var(--accent);">
        ✨ <em>Khách có thể bấm thử các nút bên dưới để test luồng!</em>
      </div>
    </div>

    <!-- 1-Click Track Bar: Simple & Straightforward -->
    <section class="track-hero">
      <div class="track-hero-title">
        <span>🎯 Thêm link sản phẩm đối thủ để AI canh chừng</span>
      </div>
      <div class="track-hero-subtitle">
        Dán link áo quần từ Shopee, TikTok Shop, Lazada hoặc Website local brand. Hệ thống sẽ tự động bóc tách giá bán, tình trạng kho và báo ngay khi đối thủ giảm giá.
      </div>
      <div class="track-bar-form">
        <input type="text" id="trackUrlInput" class="track-input" 
               placeholder="Dán link sản phẩm Shopee / TikTok Shop... (hoặc bấm link mẫu bên dưới)">
        <button class="btn btn-primary" style="padding: 0 20px;" onclick="addTrackUrl()">
          + Bắt đầu theo dõi
        </button>
      </div>
      
      <!-- Quick Sample Buttons for Instant Testing -->
      <div class="sample-pill-group">
        <span style="font-size: 12px; color: var(--text-subtle);">Bấm thử link mẫu:</span>
        <span class="sample-pill" onclick="fillSampleUrl('shopee')">
          ⚡ [Shopee] Áo Thun Heavyweight Oversize 260gsm (Shop X)
        </span>
        <span class="sample-pill" onclick="fillSampleUrl('tiktok')">
          ⚡ [TikTok Shop] Quần Jean Baggy Denim 13oz
        </span>
        <span class="sample-pill" onclick="fillSampleUrl('polo')">
          ⚡ [Shopee Mall] Áo Polo Thể Thao Dry-fit
        </span>
      </div>
    </section>

    <!-- 4 Key Commercial Metric Cards -->
    <section class="metric-grid">
      <div class="metric-card">
        <div class="metric-icon" style="background: rgba(99, 102, 241, 0.12); color: #818cf8;">👕</div>
        <div>
          <div class="metric-val">{dashboard_data["summary"]["total_tracked"]}</div>
          <div class="metric-label">Mẫu áo/quần đang theo dõi</div>
        </div>
      </div>

      <div class="metric-card" style="border-color: rgba(239, 68, 68, 0.3);">
        <div class="metric-icon" style="background: var(--danger-bg); color: var(--danger);">🚨</div>
        <div>
          <div class="metric-val" style="color: var(--danger);">{dashboard_data["summary"]["drop_count"]} đối thủ</div>
          <div class="metric-label">Phá giá (Nguy cơ mất khách)</div>
        </div>
      </div>

      <div class="metric-card" style="border-color: rgba(16, 185, 129, 0.3);">
        <div class="metric-icon" style="background: var(--success-bg); color: var(--success);">📈</div>
        <div>
          <div class="metric-val" style="color: var(--success);">{dashboard_data["summary"]["hike_count"]} đối thủ</div>
          <div class="metric-label">Tăng giá (Cơ hội tăng biên lãi)</div>
        </div>
      </div>

      <div class="metric-card" style="border-color: rgba(14, 165, 233, 0.3);">
        <div class="metric-icon" style="background: rgba(14, 165, 233, 0.12); color: var(--accent);">🛡️</div>
        <div>
          <div class="metric-val" style="color: var(--accent);">&ge; {dashboard_data["summary"]["min_margin"]}%</div>
          <div class="metric-label">Biên lợi nhuận sàn được bảo vệ</div>
        </div>
      </div>
    </section>

    <!-- ACTION FIRST: AI Businessman Recommendations -->
    <section>
      <div class="section-header">
        <div class="section-title">
          <span>⚡ Cảnh báo sáng nay cần m quyết định ({len(action_items)})</span>
        </div>
        <div style="font-size: 12.5px; color: var(--text-muted);">
          Đã lọc bỏ các biến động giá nhỏ không đáng kể
        </div>
      </div>

      <div class="action-cards-grid">
        {action_cards_html}
      </div>
    </section>

    <!-- Catalog Table: All Tracked Products -->
    <section>
      <div class="section-header">
        <div class="section-title">
          <span>📦 Toàn bộ danh mục áo quần đang theo dõi ({total_tracked})</span>
        </div>
      </div>

      <div class="catalog-card">
        <div class="catalog-toolbar">
          <input type="text" id="catalogSearchInput" class="catalog-search" 
                 placeholder="Tìm theo tên áo quần, mã SKU, sàn..." oninput="filterCatalog()">
          <div class="tab-filters">
            <span class="tab-btn active" data-filter="all" onclick="setCatalogFilter(this, 'all')">Tất cả ({total_tracked})</span>
            <span class="tab-btn" data-filter="action" onclick="setCatalogFilter(this, 'action')">Có biến động ({len(action_items)})</span>
            <span class="tab-btn" data-filter="safe" onclick="setCatalogFilter(this, 'safe')">Giá an toàn ({safe_count})</span>
          </div>
        </div>

        <div style="overflow-x: auto;">
          <table>
            <thead>
              <tr>
                <th style="width: 140px;">Mã SKU</th>
                <th>Tên sản phẩm</th>
                <th style="width: 100px;">Nền tảng</th>
                <th style="width: 120px;">Giá shop mình</th>
                <th style="width: 120px;">Giá đối thủ</th>
                <th style="width: 150px;">Đánh giá thị trường</th>
                <th style="width: 90px;">Tồn kho</th>
                <th style="width: 80px; text-align: right;">Xem</th>
              </tr>
            </thead>
            <tbody id="catalogTableBody">
              {table_rows_html}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </main>

  <!-- Telegram Preview Modal -->
  <div class="modal-overlay" id="tgModal" onclick="closeTelegramModal(event)">
    <div class="modal-card" onclick="event.stopPropagation()">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:14px; font-weight:700; color:#fff;">📱 Báo cáo gửi về Telegram của m (Lúc 08:00 sáng):</span>
        <button class="btn" style="padding:2px 8px; font-size:11px;" onclick="closeTelegramModal()">✕</button>
      </div>

      <div class="tg-bubble">
        <div style="font-weight:700; color:#ef4444; margin-bottom:6px;">📉 🔥 [CẢNH BÁO ĐỐI THỦ PHÁ GIÁ - SHOPEE]</div>
        <div><strong>Mặt hàng:</strong> Áo Thun Heavyweight Oversize 260gsm</div>
        <div><strong>Shop đối thủ:</strong> Shop X (120k followers)</div>
        <div><strong>Biến động:</strong> <del style="color:#94a3b8;">249.000₫</del> &rarr; <strong style="color:#fff;">189.000₫</strong> (-24.1%)</div>
        <div style="border-top:1px dashed #2b5278; margin:10px 0; padding-top:8px;">
          <div style="color:#38bdf8; font-weight:700;">🧠 AI Cố Vấn Tình Báo Đề Xuất:</div>
          <div>&bull; <strong>Ý đồ:</strong> Xả kho tồn trước mùa hoặc chạy Flash Sale giật top.</div>
          <div>&bull; <strong>Giá phản công:</strong> <code>185.000₫</code> (Rẻ hơn đối thủ 4k để lấy top 1 hiển thị, vẫn giữ <strong>40.5% lãi ròng</strong>).</div>
          <div style="margin-top:4px;">&bull; <strong>Phi giá:</strong> Tặng kèm 1 đôi tất dệt kim 5k cho đơn từ 2 áo để giữ giá trị đơn hàng cao.</div>
        </div>
      </div>

      <div style="display:flex; justify-content:flex-end; gap:8px;">
        <button class="btn" onclick="closeTelegramModal()">Đóng</button>
        <button class="btn btn-tg" onclick="testSendTelegram()">Gửi tin nhắn test về máy</button>
      </div>
    </div>
  </div>

  <div id="toast"></div>

  <script>
    const DATA = {data_json};
    const chartInstances = {{}};
    let currentFilter = 'all';

    function fillSampleUrl(type) {{
      const input = document.getElementById('trackUrlInput');
      if (type === 'shopee') {{
        input.value = 'https://shopee.vn/ao-thun-heavyweight-oversize-260gsm-unisex-local-brand-i.849201.294104';
      }} else if (type === 'tiktok') {{
        input.value = 'https://tiktok.com/@streetwear_studio/video/quan-jean-baggy-ong-suong-denim';
      }} else {{
        input.value = 'https://shopee.vn/ao-polo-the-thao-nam-coolmate-dry-fit-i.10294.5819';
      }}
      showToast('Đã điền link mẫu! Bấm "+ Bắt đầu theo dõi" để thêm.');
    }}

    function addTrackUrl() {{
      const input = document.getElementById('trackUrlInput');
      const val = input.value.trim();
      if (!val) {{
        showToast('⚠️ Vui lòng dán link sản phẩm Shopee / TikTok Shop đối thủ!');
        return;
      }}
      showToast('⚡ Đang kết nối bot bóc tách giá và tình trạng kho...');
      input.value = '';
      setTimeout(() => {{
        showToast('✅ Đã thêm sản phẩm thành công vào danh mục theo dõi 24/7!');
      }}, 1000);
    }}

    function applyCounterPrice(sku, price) {{
      const btns = document.getElementById(`action-btns-${{sku}}`);
      if (btns) {{
        btns.innerHTML = `<span style="color:#10b981; font-weight:600; font-size:12.5px;">✓ Đã đồng bộ giá ${{price.toLocaleString('vi-VN')}}₫ lên shop!</span>`;
      }}
      const priceTd = document.getElementById(`shop-price-${{sku}}`);
      if (priceTd) {{
        priceTd.innerText = `${{price.toLocaleString('vi-VN')}}₫`;
        priceTd.style.color = '#38bdf8';
      }}
      showToast(`✅ Đã phê duyệt! Giá bán mới ${{price.toLocaleString('vi-VN')}}₫ đã được cập nhật thành công lên gian hàng.`);
    }}

    function ignoreDelta(sku) {{
      const card = document.getElementById(`card-${{sku}}`);
      if (card) {{
        card.style.opacity = '0.5';
      }}
      showToast(`Đã bỏ qua cảnh báo biến động giá của mã ${{sku}}.`);
    }}

    function toggleChart(sku) {{
      const wrap = document.getElementById(`chart-wrap-${{sku}}`);
      if (wrap.style.display === 'block') {{
        wrap.style.display = 'none';
        return;
      }}
      wrap.style.display = 'block';

      if (!chartInstances[sku]) {{
        const item = DATA.action_items.find(i => i.sku === sku);
        if (!item) return;

        const ctx = document.getElementById(`chart-${{sku}}`).getContext('2d');
        const isDrop = item.delta.type === 'PRICE_DROP';

        chartInstances[sku] = new Chart(ctx, {{
          type: 'line',
          data: {{
            labels: item.timeline.map(t => t.date),
            datasets: [
              {{
                label: 'Giá đối thủ',
                data: item.timeline.map(t => t.competitor),
                borderColor: isDrop ? '#ef4444' : '#10b981',
                backgroundColor: isDrop ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointRadius: 4,
              }},
              {{
                label: 'Giá shop mình',
                data: item.timeline.map(t => t.my_shop),
                borderColor: '#38bdf8',
                borderDash: [5, 5],
                borderWidth: 2,
                fill: false,
                tension: 0.1,
                pointRadius: 3,
              }}
            ]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
              legend: {{
                display: true,
                labels: {{ color: '#94a3b8', font: {{ size: 11 }} }}
              }}
            }},
            scales: {{
              x: {{ grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
              y: {{ 
                grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}, 
                ticks: {{ 
                  color: '#94a3b8',
                  callback: function(value) {{ return (value / 1000) + 'k₫'; }}
                }} 
              }}
            }}
          }}
        }});
      }}
    }}

    function setCatalogFilter(el, filter) {{
      currentFilter = filter;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      el.classList.add('active');
      filterCatalog();
    }}

    function filterCatalog() {{
      const q = document.getElementById('catalogSearchInput').value.toLowerCase();
      const rows = document.querySelectorAll('#catalogTableBody tr');

      rows.forEach(r => {{
        const sku = r.getAttribute('data-sku');
        const hasAction = r.getAttribute('data-action') === 'true';
        const item = DATA.products.find(p => p.sku === sku);
        if (!item) return;

        const matchSearch = item.sku.toLowerCase().includes(q) || 
                            item.title.toLowerCase().includes(q) || 
                            item.platform.toLowerCase().includes(q);
        let matchFilter = true;
        if (currentFilter === 'action') matchFilter = hasAction;
        else if (currentFilter === 'safe') matchFilter = !hasAction;

        r.style.display = (matchSearch && matchFilter) ? '' : 'none';
      }});
    }}

    function triggerScan() {{
      showToast('⚡ Đang tự động quét giá 8 mẫu áo quần đối thủ trên Shopee & TikTok...');
      setTimeout(() => {{
        showToast('✅ Quét hoàn tất! Đã cập nhật giá và tồn kho thời gian thực.');
      }}, 1200);
    }}

    function exportData() {{
      const headers = ['Mã SKU', 'Tên sản phẩm', 'Nền tảng', 'Giá shop mình (VND)', 'Giá đối thủ (VND)', 'Tồn kho', 'Link đối thủ'];
      const rows = DATA.products.map(p => [
        p.sku, 
        `"${{p.title.replace(/"/g, '""')}}"`, 
        p.platform,
        p.shop_price,
        p.current_price, 
        p.stock_status, 
        p.url
      ]);
      // UTF-8 BOM so Excel opens Vietnamese characters without broken accents
      const csv = '\\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\\n');
      const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'Bao_cao_gia_thoi_trang_Market_Sentinel.csv';
      a.click();
      showToast('📥 Đã tải xuống file Excel/CSV báo cáo giá thời trang chuẩn tiếng Việt!');
    }}

    function openTelegramModal() {{
      document.getElementById('tgModal').style.display = 'flex';
    }}

    function closeTelegramModal(e) {{
      if (!e || e.target.id === 'tgModal' || e.target.tagName === 'BUTTON') {{
        document.getElementById('tgModal').style.display = 'none';
      }}
    }}

    function testSendTelegram() {{
      showToast('📲 [Telegram Bot] Đã gửi thông báo tình báo giá về điện thoại của m!');
    }}

    function showToast(msg) {{
      const t = document.getElementById('toast');
      t.innerText = msg;
      t.style.display = 'block';
      setTimeout(() => {{ t.style.display = 'none'; }}, 2800);
    }}
  </script>
</body>
</html>
"""

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Fashion B2B Commercial Dashboard generated successfully at {out_file}")

if __name__ == "__main__":
    generate_fashion_dashboard()
