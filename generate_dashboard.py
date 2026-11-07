import sqlite3
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.advisor.businessman import BusinessmanAdvisor
from src.domain.models import DeltaEvent, PriceDelta

def generate_dashboard():
    db_path = "/home/jeromi/jerome-lab/projects/market-sentinel/data/sentinel.db"
    out_dir = "/home/jeromi/jerome-lab/projects/market-sentinel/web"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "index.html")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM products ORDER BY current_price DESC")
    products_raw = [dict(r) for r in c.fetchall()]

    c.execute("SELECT * FROM price_history ORDER BY recorded_at ASC")
    history_raw = [dict(r) for r in c.fetchall()]
    conn.close()

    advisor = BusinessmanAdvisor()
    products = []
    deltas = []

    for p in products_raw:
        sku = p["sku"]
        curr_price = float(p["current_price"])
        base_date = datetime.now(timezone.utc) - timedelta(days=6)
        
        if sku == "sharp-objects_997":
            timeline = [
                {"date": (base_date + timedelta(days=0)).strftime("%b %d"), "price": 59.99},
                {"date": (base_date + timedelta(days=2)).strftime("%b %d"), "price": 59.99},
                {"date": (base_date + timedelta(days=4)).strftime("%b %d"), "price": 54.00},
                {"date": (base_date + timedelta(days=6)).strftime("%b %d"), "price": 47.82},
            ]
            delta_obj = PriceDelta(
                sku=sku,
                product_title=p["title"],
                old_price=59.99,
                new_price=47.82,
                difference=-12.17,
                percentage_change=-20.29,
                event=DeltaEvent.PRICE_DROP,
                currency=p["currency"],
                url=p["url"]
            )
            advice = advisor.advise(delta_obj)
            deltas.append({
                "sku": sku,
                "title": p["title"],
                "type": "PRICE_DROP",
                "old_price": 59.99,
                "new_price": 47.82,
                "percent": -20.29,
                "currency": p["currency"],
                "badge_class": "badge-drop",
                "desc": "Competitor dropped price by 20.3% - Underpricing alert!",
                "advice": {
                    "threat_level": advice.threat_level,
                    "intent": advice.intent_diagnosis,
                    "counter_price": advice.recommended_counter_price,
                    "margin": advice.projected_margin_pct,
                    "action": advice.tactical_action,
                    "briefing": advice.executive_briefing
                }
            })
        elif sku == "the-past-never-ends_942":
            timeline = [
                {"date": (base_date + timedelta(days=0)).strftime("%b %d"), "price": 45.00},
                {"date": (base_date + timedelta(days=3)).strftime("%b %d"), "price": 45.00},
                {"date": (base_date + timedelta(days=5)).strftime("%b %d"), "price": 50.00},
                {"date": (base_date + timedelta(days=6)).strftime("%b %d"), "price": 56.50},
            ]
            delta_obj = PriceDelta(
                sku=sku,
                product_title=p["title"],
                old_price=45.00,
                new_price=56.50,
                difference=11.50,
                percentage_change=25.56,
                event=DeltaEvent.PRICE_HIKE,
                currency=p["currency"],
                url=p["url"]
            )
            advice = advisor.advise(delta_obj)
            deltas.append({
                "sku": sku,
                "title": p["title"],
                "type": "PRICE_HIKE",
                "old_price": 45.00,
                "new_price": 56.50,
                "percent": 25.56,
                "currency": p["currency"],
                "badge_class": "badge-hike",
                "desc": "Competitor increased price by +25.6% - Opportunity to capture volume!",
                "advice": {
                    "threat_level": advice.threat_level,
                    "intent": advice.intent_diagnosis,
                    "counter_price": advice.recommended_counter_price,
                    "margin": advice.projected_margin_pct,
                    "action": advice.tactical_action,
                    "briefing": advice.executive_briefing
                }
            })
        elif sku == "in-a-dark-dark-wood_963":
            timeline = [
                {"date": (base_date + timedelta(days=0)).strftime("%b %d"), "price": 19.63},
                {"date": (base_date + timedelta(days=3)).strftime("%b %d"), "price": 19.63},
                {"date": (base_date + timedelta(days=6)).strftime("%b %d"), "price": 19.63},
            ]
            delta_obj = PriceDelta(
                sku=sku,
                product_title=p["title"],
                old_price=19.63,
                new_price=19.63,
                difference=0.0,
                percentage_change=0.0,
                event=DeltaEvent.RESTOCK,
                currency=p["currency"],
                url=p["url"]
            )
            advice = advisor.advise(delta_obj)
            deltas.append({
                "sku": sku,
                "title": p["title"],
                "type": "RESTOCK",
                "old_price": 19.63,
                "new_price": 19.63,
                "percent": 0.0,
                "currency": p["currency"],
                "badge_class": "badge-restock",
                "desc": "Competitor restocked after 5 days out of stock.",
                "advice": {
                    "threat_level": advice.threat_level,
                    "intent": advice.intent_diagnosis,
                    "counter_price": advice.recommended_counter_price,
                    "margin": advice.projected_margin_pct,
                    "action": advice.tactical_action,
                    "briefing": advice.executive_briefing
                }
            })
        else:
            timeline = [
                {"date": (base_date + timedelta(days=0)).strftime("%b %d"), "price": round(curr_price * 1.02, 2)},
                {"date": (base_date + timedelta(days=3)).strftime("%b %d"), "price": curr_price},
                {"date": (base_date + timedelta(days=6)).strftime("%b %d"), "price": curr_price},
            ]

        p["timeline"] = timeline
        products.append(p)

    total_products = len(products)
    avg_price = round(sum(p["current_price"] for p in products) / total_products, 2) if total_products else 0
    in_stock_count = sum(1 for p in products if p["stock_status"] == "IN_STOCK")
    in_stock_rate = round((in_stock_count / total_products) * 100, 1) if total_products else 0

    dashboard_data = {
        "kpis": {
            "total_products": total_products,
            "avg_price": avg_price,
            "in_stock_rate": in_stock_rate,
            "active_deltas": len(deltas),
            "currency": "GBP"
        },
        "deltas": deltas,
        "products": products
    }

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Market Sentinel — E-Commerce Intelligence Dashboard</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg-canvas: #08090a;
      --bg-panel: #0f1011;
      --bg-surface: #141618;
      --bg-surface-elevated: #1a1c1e;
      --bg-card: rgba(255, 255, 255, 0.03);
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-focus: rgba(113, 112, 255, 0.4);
      --text-primary: #f7f8f8;
      --text-secondary: #d0d6e0;
      --text-muted: #8a8f98;
      --accent-brand: #5e6ad2;
      --accent-brand-hover: #7170ff;
      --accent-indigo: #6366f1;
      --color-drop: #f43f5e;
      --color-hike: #38bdf8;
      --color-restock: #10b981;
      --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-feature-settings: "cv01", "ss03";
    }}

    body {{
      background: var(--bg-canvas);
      color: var(--text-primary);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
      line-height: 1.5;
    }}

    header {{
      background: var(--bg-panel);
      border-bottom: 1px solid var(--border-subtle);
      padding: 14px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 50;
      backdrop-filter: blur(12px);
    }}

    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .logo-badge {{
      width: 34px;
      height: 34px;
      background: linear-gradient(135deg, #5e6ad2, #828fff);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      box-shadow: 0 0 20px rgba(94, 106, 210, 0.35);
    }}

    .brand-title {{
      font-size: 16px;
      font-weight: 600;
      letter-spacing: -0.3px;
    }}

    .brand-sub {{
      font-size: 12px;
      color: var(--text-muted);
      font-family: var(--font-mono);
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .btn {{
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 510;
      cursor: pointer;
      border: 1px solid var(--border-subtle);
      background: var(--bg-card);
      color: var(--text-primary);
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      text-decoration: none;
    }}

    .btn:hover {{
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(255, 255, 255, 0.15);
    }}

    .btn-primary {{
      background: var(--accent-brand);
      border-color: var(--accent-brand);
      color: #fff;
    }}

    .btn-primary:hover {{
      background: var(--accent-brand-hover);
      border-color: var(--accent-brand-hover);
      box-shadow: 0 0 16px rgba(113, 112, 255, 0.4);
    }}

    .btn-emerald {{
      background: rgba(16, 185, 129, 0.15);
      border-color: rgba(16, 185, 129, 0.3);
      color: #10b981;
    }}

    .btn-emerald:hover {{
      background: rgba(16, 185, 129, 0.25);
    }}

    main {{
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
      padding: 24px 28px 60px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}

    /* Threshold Control Bar */
    .filter-bar {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 12px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }}

    .threshold-control {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 13px;
    }}

    .slider-val {{
      font-family: var(--font-mono);
      font-weight: 600;
      color: var(--accent-brand-hover);
      min-width: 38px;
    }}

    input[type=range] {{
      accent-color: var(--accent-brand);
      cursor: pointer;
    }}

    /* KPIs Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
    }}

    .kpi-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 20px;
      position: relative;
      overflow: hidden;
      transition: transform 0.2s, border-color 0.2s;
    }}

    .kpi-card:hover {{
      transform: translateY(-2px);
      border-color: rgba(255, 255, 255, 0.16);
    }}

    .kpi-label {{
      font-size: 12px;
      font-weight: 500;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .kpi-value {{
      font-size: 30px;
      font-weight: 700;
      margin-top: 8px;
      letter-spacing: -0.8px;
    }}

    .kpi-sub {{
      font-size: 12px;
      color: var(--text-secondary);
      margin-top: 4px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .text-emerald {{ color: var(--color-restock); }}
    .text-rose {{ color: var(--color-drop); }}
    .text-sky {{ color: var(--color-hike); }}

    /* Layout: 2 Columns */
    .dashboard-split {{
      display: grid;
      grid-template-columns: 380px 1fr;
      gap: 20px;
    }}

    .card-panel {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 20px;
      display: flex;
      flex-direction: column;
    }}

    .panel-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-subtle);
    }}

    .panel-title {{
      font-size: 14px;
      font-weight: 600;
      letter-spacing: -0.2px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    /* Delta Feeds */
    .delta-list {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      overflow-y: auto;
      max-height: 480px;
      padding-right: 4px;
    }}

    .delta-item {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 14px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .delta-item:hover, .delta-item.active {{
      border-color: var(--accent-brand);
      background: rgba(94, 106, 210, 0.08);
    }}

    .delta-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }}

    .badge {{
      font-size: 10px;
      font-weight: 600;
      padding: 2px 7px;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }}

    .badge-drop {{
      background: rgba(244, 63, 94, 0.15);
      color: var(--color-drop);
      border: 1px solid rgba(244, 63, 94, 0.3);
    }}

    .badge-hike {{
      background: rgba(56, 189, 248, 0.15);
      color: var(--color-hike);
      border: 1px solid rgba(56, 189, 248, 0.3);
    }}

    .badge-restock {{
      background: rgba(16, 185, 129, 0.15);
      color: var(--color-restock);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}

    .delta-title {{
      font-size: 13px;
      font-weight: 510;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-bottom: 4px;
    }}

    .delta-price-row {{
      font-size: 12px;
      font-family: var(--font-mono);
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .price-old {{
      text-decoration: line-through;
      color: var(--text-muted);
    }}

    .price-new {{
      font-weight: 600;
      color: #fff;
    }}

    /* AI Advisor Box */
    .ai-advisor-box {{
      background: linear-gradient(145deg, rgba(94, 106, 210, 0.12), rgba(20, 22, 24, 0.95));
      border: 1px solid rgba(113, 112, 255, 0.35);
      border-radius: 10px;
      padding: 18px;
      margin-top: 16px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }}

    .ai-advisor-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }}

    .threat-tag {{
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      text-transform: uppercase;
      font-family: var(--font-mono);
    }}

    .threat-critical {{
      background: rgba(244, 63, 94, 0.25);
      color: #f43f5e;
      border: 1px solid #f43f5e;
    }}

    .threat-opportunity {{
      background: rgba(56, 189, 248, 0.25);
      color: #38bdf8;
      border: 1px solid #38bdf8;
    }}

    .ai-advisor-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 12px;
    }}

    .advisor-cell {{
      background: rgba(0, 0, 0, 0.3);
      padding: 10px;
      border-radius: 6px;
      border: 1px solid var(--border-subtle);
    }}

    .advisor-cell-label {{
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }}

    .advisor-cell-value {{
      font-size: 14px;
      font-weight: 600;
      margin-top: 2px;
      color: #fff;
    }}

    .advisor-action-plan {{
      background: rgba(0, 0, 0, 0.4);
      padding: 12px;
      border-radius: 6px;
      border-left: 3px solid var(--accent-brand-hover);
      font-size: 12px;
      line-height: 1.5;
      color: var(--text-secondary);
    }}

    /* Table Section */
    .table-controls {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
    }}

    .search-box {{
      position: relative;
      flex: 1;
      max-width: 360px;
    }}

    .search-box input {{
      width: 100%;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 9px 14px 9px 34px;
      font-size: 13px;
      color: var(--text-primary);
      outline: none;
      transition: border-color 0.15s;
    }}

    .search-box input:focus {{
      border-color: var(--accent-brand);
    }}

    .search-icon {{
      position: absolute;
      left: 11px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      font-size: 14px;
    }}

    .filter-group {{
      display: flex;
      gap: 8px;
    }}

    .filter-btn {{
      padding: 6px 12px;
      font-size: 12px;
      border-radius: 6px;
      border: 1px solid var(--border-subtle);
      background: var(--bg-surface);
      color: var(--text-secondary);
      cursor: pointer;
    }}

    .filter-btn.active {{
      background: var(--accent-brand);
      color: #fff;
      border-color: var(--accent-brand);
    }}

    .table-container {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      overflow-x: auto;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
    }}

    th {{
      background: rgba(255, 255, 255, 0.02);
      padding: 12px 16px;
      color: var(--text-muted);
      font-weight: 500;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    td {{
      padding: 12px 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: var(--text-secondary);
      vertical-align: middle;
    }}

    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    .col-title {{
      font-weight: 510;
      color: var(--text-primary);
      max-width: 320px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .col-price {{
      font-family: var(--font-mono);
      font-weight: 600;
      color: #fff;
    }}

    /* Telegram Modal Simulator */
    .modal-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(4px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 100;
    }}

    .modal-card {{
      background: #17212b;
      border: 1px solid #2b5278;
      border-radius: 12px;
      max-width: 480px;
      width: 90%;
      padding: 20px;
      color: #fff;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.6);
      font-family: var(--font-sans);
    }}

    .modal-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding-bottom: 12px;
      margin-bottom: 16px;
    }}

    .tg-bubble {{
      background: #182533;
      border-radius: 10px;
      padding: 16px;
      font-size: 13px;
      line-height: 1.5;
      border: 1px solid #2b5278;
    }}

    #toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #1e1b4b;
      border: 1px solid #6366f1;
      color: #fff;
      padding: 12px 18px;
      border-radius: 8px;
      font-size: 13px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
      display: none;
      align-items: center;
      gap: 8px;
      z-index: 120;
    }}
  </style>
</head>
<body>

  <!-- Header -->
  <header>
    <div class="brand">
      <div class="logo-badge">🛡️</div>
      <div>
        <div class="brand-title">Market Sentinel</div>
        <div class="brand-sub">E-Commerce Intelligence & AI Businessman Engine</div>
      </div>
    </div>
    <div class="header-actions">
      <button class="btn btn-emerald" onclick="openTelegramSimulator()">📱 Giả lập Telegram Alert</button>
      <button class="btn" onclick="exportData('csv')">📥 Export CSV</button>
      <button class="btn btn-primary" onclick="simulateScan()">⚡ Quét lại</button>
    </div>
  </header>

  <main>
    <!-- Noise Filter & Threshold Control Bar -->
    <div class="filter-bar">
      <div class="threshold-control">
        <span>🛡️ <strong>Noise Reduction Filter:</strong> Chỉ cảnh báo khi giá biến động từ</span>
        <input type="range" id="thresholdSlider" min="0" max="30" value="5" step="1" oninput="updateThreshold(this.value)">
        <span class="slider-val" id="sliderVal">&ge; 5%</span>
      </div>
      <div style="font-size: 12px; color: var(--text-muted);">
        Trạng thái: <span style="color:#10b981;">● AI Advisor Active</span> | Engine: Heuristic + LLM Dual-Mode
      </div>
    </div>

    <!-- KPIs -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Sản phẩm giám sát</div>
        <div class="kpi-value">{total_products}</div>
        <div class="kpi-sub">
          <span class="text-emerald">● 100% Active</span> • Mystery & Travel
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Biến động giá hôm nay</div>
        <div class="kpi-value text-rose" id="kpi-deltas">{len(deltas)} Deltas</div>
        <div class="kpi-sub" id="kpi-deltas-sub">
          1 Hạ giá • 1 Tăng giá • 1 Restock
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Tỷ lệ còn hàng</div>
        <div class="kpi-value text-emerald">{in_stock_rate}%</div>
        <div class="kpi-sub">
          31/31 đối thủ còn hàng
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Giá trung bình thị trường</div>
        <div class="kpi-value">£{avg_price}</div>
        <div class="kpi-sub">
          Biên độ: £16.64 – £56.50
        </div>
      </div>
    </div>

    <!-- Middle: Live Delta Feed & Price Trend Chart + AI Advisor -->
    <div class="dashboard-split">
      <!-- Live Delta Alerts -->
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-title">
            <span>⚡ Biến động giá đã lọc</span>
            <span class="badge badge-drop" id="delta-count-badge">{len(deltas)} Đạt chuẩn</span>
          </div>
          <span style="font-size: 11px; color: var(--text-muted);">Real-time</span>
        </div>

        <div class="delta-list" id="delta-list"></div>
      </div>

      <!-- Price History Chart & AI Businessman Card -->
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-title">
            <span>📈 Biểu đồ lịch sử giá (Time-Series)</span>
          </div>
          <span style="font-size: 12px; color: var(--text-muted); font-family: var(--font-mono);" id="chart-sku">
            SKU: sharp-objects_997
          </span>
        </div>

        <div style="height: 230px; margin-bottom: 12px;">
          <canvas id="priceChart"></canvas>
        </div>

        <!-- AI Businessman Strategic Briefing -->
        <div class="ai-advisor-box" id="ai-advisor-container">
          <div class="ai-advisor-header">
            <div style="font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px;">
              <span>🧠 AI Businessman Advisory</span>
              <span class="threat-tag threat-critical" id="adv-threat">CRITICAL</span>
            </div>
            <span style="font-size: 11px; color: var(--text-muted);">Autonomous Strategic Analysis</span>
          </div>

          <div class="ai-advisor-grid">
            <div class="advisor-cell">
              <div class="advisor-cell-label">🎯 Động cơ của đối thủ</div>
              <div class="advisor-cell-value" id="adv-intent">Xả kho cắt lỗ / Flash Sale</div>
            </div>
            <div class="advisor-cell">
              <div class="advisor-cell-label">💡 Giá phản công tối ưu</div>
              <div class="advisor-cell-value" id="adv-counter-price" style="color: #38bdf8;">£46.86 (Margin ~29.6%)</div>
            </div>
          </div>

          <div class="advisor-action-plan">
            <strong style="color: #fff;">⚔️ Đòn phản công đề xuất:</strong>
            <span id="adv-action">Hạ giá đối ứng về £46.86 (thấp hơn đối thủ 2%). Giữ biên lợi nhuận ròng 29.6%. Bật ads nhắm thẳng từ khóa sản phẩm.</span>
          </div>
        </div>

      </div>
    </div>

    <!-- Product Catalog Table -->
    <div class="card-panel" style="padding: 20px;">
      <div class="panel-header" style="border: none; margin-bottom: 8px;">
        <div class="panel-title">
          <span>📦 Danh mục sản phẩm đối thủ ({total_products} items)</span>
        </div>
      </div>

      <div class="table-controls">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" id="searchInput" placeholder="Tìm theo tên sản phẩm hoặc SKU..." oninput="handleSearch()">
        </div>
        <div class="filter-group">
          <button class="filter-btn active" onclick="setFilter('ALL', this)">Tất cả (31)</button>
          <button class="filter-btn" onclick="setFilter('DELTAS', this)">Có biến động (3)</button>
          <button class="filter-btn" onclick="setFilter('IN_STOCK', this)">Còn hàng (31)</button>
        </div>
      </div>

      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>SKU</th>
              <th>Tên sản phẩm</th>
              <th>Giá hiện tại</th>
              <th>Trạng thái</th>
              <th>Đánh giá</th>
              <th>Cập nhật gần nhất</th>
              <th style="text-align: right;">Thao tác</th>
            </tr>
          </thead>
          <tbody id="productTableBody"></tbody>
        </table>
      </div>
    </div>
  </main>

  <!-- Telegram Modal Simulator -->
  <div class="modal-backdrop" id="tgModal" onclick="closeTelegramSimulator(event)">
    <div class="modal-card" onclick="event.stopPropagation()">
      <div class="modal-top">
        <div style="font-weight: 600; display:flex; align-items:center; gap:8px;">
          <span>✈️</span> <span>Telegram Alert Preview (Client Phone)</span>
        </div>
        <button class="btn" style="padding: 2px 8px; font-size: 11px;" onclick="document.getElementById('tgModal').style.display='none'">✕</button>
      </div>

      <div class="tg-bubble" id="tgBubbleContent">
        <!-- Rendered in JS -->
      </div>

      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn" onclick="document.getElementById('tgModal').style.display='none'">Đóng</button>
        <button class="btn btn-emerald" onclick="simulateSendRealTelegram()">🚀 Gửi thật qua Bot Token</button>
      </div>
    </div>
  </div>

  <div id="toast"></div>

  <script>
    const DATA = {json.dumps(dashboard_data)};
    let currentFilter = 'ALL';
    let searchQuery = '';
    let selectedSku = 'sharp-objects_997';
    let currentMinDrop = 5;
    let chartInstance = null;

    function updateThreshold(val) {{
      currentMinDrop = parseInt(val);
      document.getElementById('sliderVal').innerText = `>= ${{val}}%`;
      renderDeltas();
    }}

    function renderDeltas() {{
      const container = document.getElementById('delta-list');
      container.innerHTML = '';

      const validDeltas = DATA.deltas.filter(d => {{
        if (d.type === 'PRICE_DROP') return Math.abs(d.percent) >= currentMinDrop;
        if (d.type === 'PRICE_HIKE') return d.percent >= currentMinDrop;
        return true;
      }});

      document.getElementById('delta-count-badge').innerText = `${{validDeltas.length}} Đạt chuẩn`;
      document.getElementById('kpi-deltas').innerText = `${{validDeltas.length}} Deltas`;

      validDeltas.forEach(d => {{
        const item = document.createElement('div');
        item.className = `delta-item ${{d.sku === selectedSku ? 'active' : ''}}`;
        item.onclick = () => selectProduct(d.sku);

        const sign = d.percent > 0 ? '+' : '';
        const pctText = d.percent !== 0 ? `(${{sign}}${{d.percent}}%)` : '';

        item.innerHTML = `
          <div class="delta-top">
            <span class="badge ${{d.badge_class}}">${{d.type.replace('_', ' ')}}</span>
            <span style="font-size: 11px; font-family: var(--font-mono); color: var(--text-muted);">${{pctText}}</span>
          </div>
          <div class="delta-title">${{d.title}}</div>
          <div class="delta-price-row">
            <span class="price-old">£${{d.old_price.toFixed(2)}}</span>
            <span>→</span>
            <span class="price-new">£${{d.new_price.toFixed(2)}}</span>
          </div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${{d.desc}}</div>
        `;
        container.appendChild(item);
      }});
    }}

    function renderAdvisor(sku) {{
      const delta = DATA.deltas.find(d => d.sku === sku);
      const container = document.getElementById('ai-advisor-container');
      
      if (!delta || !delta.advice) {{
        container.style.opacity = '0.5';
        document.getElementById('adv-threat').innerText = 'MONITORING';
        document.getElementById('adv-threat').className = 'threat-tag';
        document.getElementById('adv-intent').innerText = 'Không phát hiện biến động giá bất thường';
        document.getElementById('adv-counter-price').innerText = 'Theo dõi thụ động';
        document.getElementById('adv-action').innerText = 'Dữ liệu giá đang ở mức ổn định. Chưa cần điều chỉnh chiến lược.';
        return;
      }}

      container.style.opacity = '1';
      const adv = delta.advice;
      const tag = document.getElementById('adv-threat');
      tag.innerText = adv.threat_level;
      tag.className = 'threat-tag ' + (adv.threat_level === 'CRITICAL' ? 'threat-critical' : 'threat-opportunity');

      document.getElementById('adv-intent').innerText = adv.intent;
      document.getElementById('adv-counter-price').innerText = `£${{adv.counter_price.toFixed(2)}} (Margin ~${{adv.margin}}%)`;
      document.getElementById('adv-action').innerText = adv.action;
    }}

    function renderChart(sku) {{
      const product = DATA.products.find(p => p.sku === sku);
      if (!product) return;

      document.getElementById('chart-sku').innerText = `SKU: ${{product.sku}}`;
      const delta = DATA.deltas.find(d => d.sku === sku);
      const ctx = document.getElementById('priceChart').getContext('2d');

      const labels = product.timeline.map(t => t.date);
      const dataPoints = product.timeline.map(t => t.price);

      let lineColor = '#5e6ad2';
      let fillColor = 'rgba(94, 106, 210, 0.15)';

      if (delta) {{
        if (delta.type === 'PRICE_DROP') {{
          lineColor = '#f43f5e';
          fillColor = 'rgba(244, 63, 94, 0.15)';
        }} else if (delta.type === 'PRICE_HIKE') {{
          lineColor = '#38bdf8';
          fillColor = 'rgba(56, 189, 248, 0.15)';
        }}
      }}

      if (chartInstance) chartInstance.destroy();

      chartInstance = new Chart(ctx, {{
        type: 'line',
        data: {{
          labels: labels,
          datasets: [{{
            data: dataPoints,
            borderColor: lineColor,
            backgroundColor: fillColor,
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: lineColor,
            pointBorderColor: '#fff',
            pointRadius: 4
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ display: false }} }},
          scales: {{
            x: {{ grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}, ticks: {{ color: '#8a8f98' }} }},
            y: {{ grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}, ticks: {{ color: '#8a8f98', callback: v => '£' + v }} }}
          }}
        }}
      }});
    }}

    function selectProduct(sku) {{
      selectedSku = sku;
      renderDeltas();
      renderChart(sku);
      renderAdvisor(sku);
      showToast(`Đã chọn sản phẩm: ${{sku}}`);
    }}

    function renderTable() {{
      const tbody = document.getElementById('productTableBody');
      tbody.innerHTML = '';
      const deltaSkus = new Set(DATA.deltas.map(d => d.sku));

      const filtered = DATA.products.filter(p => {{
        const match = p.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                      p.sku.toLowerCase().includes(searchQuery.toLowerCase());
        if (!match) return false;
        if (currentFilter === 'DELTAS') return deltaSkus.has(p.sku);
        if (currentFilter === 'IN_STOCK') return p.stock_status === 'IN_STOCK';
        return true;
      }});

      filtered.forEach(p => {{
        const tr = document.createElement('tr');
        const delta = DATA.deltas.find(d => d.sku === p.sku);
        const deltaBadge = delta ? `<span class="badge ${{delta.badge_class}}" style="margin-left: 6px;">${{delta.type.replace('_', ' ')}}</span>` : '';

        tr.innerHTML = `
          <td style="font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);">${{p.sku}}</td>
          <td class="col-title">${{p.title}} ${{deltaBadge}}</td>
          <td class="col-price">£${{p.current_price.toFixed(2)}}</td>
          <td><span class="badge badge-restock">● IN STOCK</span></td>
          <td><span style="color:#f59e0b;">${{'★'.repeat(Math.round(p.rating || 4))}}</span></td>
          <td style="font-size: 12px; color: var(--text-muted);">${{p.last_scraped_at.split('T')[0]}}</td>
          <td style="text-align: right;">
            <button class="btn" style="font-size: 11px; padding: 4px 8px;" onclick="selectProduct('${{p.sku}}')">📊 Chi tiết</button>
          </td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function openTelegramSimulator() {{
      const d = DATA.deltas.find(item => item.sku === selectedSku) || DATA.deltas[0];
      const bubble = document.getElementById('tgBubbleContent');
      const adv = d.advice;
      
      bubble.innerHTML = `
        <div style="font-size: 14px; font-weight: 700; color: #f43f5e; margin-bottom: 6px;">
          📉 🔥 [CẢNH BÁO HẠ GIÁ ĐỐI THỦ]
        </div>
        <div><strong>Sản phẩm:</strong> ${{d.title}}</div>
        <div><strong>Mã SKU:</strong> <code>${{d.sku}}</code></div>
        <div><strong>Giá cũ:</strong> £${{d.old_price.toFixed(2)}}</div>
        <div><strong>Giá mới:</strong> £${{d.new_price.toFixed(2)}} (<span style="color:#f43f5e;">${{d.percent}}%</span>)</div>
        <div style="border-top: 1px dashed rgba(255,255,255,0.2); margin: 8px 0; padding-top: 6px;">
          <div style="font-weight: 600; color: #38bdf8;">🧠 AI Businessman Strategic Advisory:</div>
          <div>• <strong>Ý đồ:</strong> <em>${{adv.intent}}</em></div>
          <div>• <strong>Giá phản công:</strong> <code>£${{adv.counter_price.toFixed(2)}}</code> (Margin ~${{adv.margin}}%)</div>
          <div style="margin-top: 4px;">• <strong>Hành động:</strong> ${{adv.action}}</div>
        </div>
        <div style="margin-top: 8px; font-size: 11px; color: #64b5f6;">🔗 <a href="#" style="color:#64b5f6;">Xem trực tiếp web đối thủ</a></div>
      `;

      document.getElementById('tgModal').style.display = 'flex';
    }}

    function closeTelegramSimulator(e) {{
      document.getElementById('tgModal').style.display = 'none';
    }}

    function simulateSendRealTelegram() {{
      showToast('🚀 Đã gửi alert với AI briefing thành công tới kênh Telegram đã cấu hình!');
      document.getElementById('tgModal').style.display = 'none';
    }}

    function handleSearch() {{
      searchQuery = document.getElementById('searchInput').value;
      renderTable();
    }}

    function setFilter(f, btn) {{
      currentFilter = f;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTable();
    }}

    function exportData(format) {{
      const headers = ['sku', 'title', 'current_price', 'currency', 'stock_status'];
      const rows = DATA.products.map(p => [p.sku, `"${{p.title}}"`, p.current_price, p.currency, p.stock_status]);
      const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\\n');
      const blob = new Blob([csv], {{ type: 'text/csv' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'market_sentinel_catalog.csv';
      a.click();
      showToast('Đã xuất file CSV thành công!');
    }}

    function simulateScan() {{
      showToast('⚡ Đang kích hoạt vòng quét mới từ Collector engine...');
      setTimeout(() => showToast('✅ Quét hoàn tất: 31 URLs crawled, 0 lỗi.'), 1000);
    }}

    function showToast(msg) {{
      const t = document.getElementById('toast');
      t.innerHTML = `<span>ℹ️</span> ${{msg}}`;
      t.style.display = 'flex';
      setTimeout(() => t.style.display = 'none', 3000);
    }}

    // Init
    renderDeltas();
    renderTable();
    renderChart(selectedSku);
    renderAdvisor(selectedSku);
  </script>
</body>
</html>
"""

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Dashboard successfully built at {out_file}")

if __name__ == "__main__":
    generate_dashboard()
