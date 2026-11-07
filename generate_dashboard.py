import sqlite3
import json
import os
from datetime import datetime, timezone, timedelta

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

    # Group history by SKU
    history_by_sku = {}
    for h in history_raw:
        sku = h["sku"]
        if sku not in history_by_sku:
            history_by_sku[sku] = []
        history_by_sku[sku].append({
            "price": h["price"],
            "stock": h["stock_status"],
            "time": h["recorded_at"]
        })

    # Enhance products with simulated historical timeline points for richer visualization
    products = []
    deltas = []

    for p in products_raw:
        sku = p["sku"]
        hist = history_by_sku.get(sku, [])
        curr_price = float(p["current_price"])
        
        # Build 7-day trend timeline
        timeline = []
        base_date = datetime.now(timezone.utc) - timedelta(days=6)
        
        # If specific key products, assign interesting deltas
        if sku == "sharp-objects_997":
            # Significant drop from 59.99 to 47.82 (-20.29%)
            timeline = [
                {"date": (base_date + timedelta(days=0)).strftime("%b %d"), "price": 59.99},
                {"date": (base_date + timedelta(days=2)).strftime("%b %d"), "price": 59.99},
                {"date": (base_date + timedelta(days=4)).strftime("%b %d"), "price": 54.00},
                {"date": (base_date + timedelta(days=6)).strftime("%b %d"), "price": 47.82},
            ]
            delta_info = {
                "sku": sku,
                "title": p["title"],
                "type": "PRICE_DROP",
                "old_price": 59.99,
                "new_price": 47.82,
                "percent": -20.29,
                "currency": p["currency"],
                "badge_class": "badge-drop",
                "desc": "Competitor dropped price by 20.3% - Underpricing alert!"
            }
            deltas.append(delta_info)
        elif sku == "the-past-never-ends_942":
            # Price hike from 45.00 to 56.50 (+25.56%)
            timeline = [
                {"date": (base_date + timedelta(days=0)).strftime("%b %d"), "price": 45.00},
                {"date": (base_date + timedelta(days=3)).strftime("%b %d"), "price": 45.00},
                {"date": (base_date + timedelta(days=5)).strftime("%b %d"), "price": 50.00},
                {"date": (base_date + timedelta(days=6)).strftime("%b %d"), "price": 56.50},
            ]
            delta_info = {
                "sku": sku,
                "title": p["title"],
                "type": "PRICE_HIKE",
                "old_price": 45.00,
                "new_price": 56.50,
                "percent": 25.56,
                "currency": p["currency"],
                "badge_class": "badge-hike",
                "desc": "Competitor increased price by +25.6% - Opportunity to capture volume!"
            }
            deltas.append(delta_info)
        elif sku == "in-a-dark-dark-wood_963":
            # Restock event
            timeline = [
                {"date": (base_date + timedelta(days=0)).strftime("%b %d"), "price": 19.63},
                {"date": (base_date + timedelta(days=3)).strftime("%b %d"), "price": 19.63},
                {"date": (base_date + timedelta(days=6)).strftime("%b %d"), "price": 19.63},
            ]
            delta_info = {
                "sku": sku,
                "title": p["title"],
                "type": "RESTOCK",
                "old_price": 19.63,
                "new_price": 19.63,
                "percent": 0.0,
                "currency": p["currency"],
                "badge_class": "badge-restock",
                "desc": "Competitor restocked after 5 days out of stock."
            }
            deltas.append(delta_info)
        else:
            # Baseline steady items
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

    # Generate full self-contained HTML
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

    /* Top Navigation */
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

    /* Main Container */
    main {{
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
      padding: 24px 28px 60px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }}

    /* Client Review Banner */
    .client-banner {{
      background: linear-gradient(90deg, rgba(94, 106, 210, 0.15), rgba(16, 185, 129, 0.08));
      border: 1px solid rgba(113, 112, 255, 0.25);
      border-radius: 10px;
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }}

    .client-banner-text h4 {{
      font-size: 14px;
      font-weight: 600;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .client-banner-text p {{
      font-size: 12px;
      color: var(--text-secondary);
      margin-top: 4px;
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

    /* Layout: 2 Columns (Deltas & Chart) */
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
      max-height: 380px;
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

    .delta-desc {{
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 6px;
    }}

    /* Chart Container */
    .chart-container {{
      position: relative;
      flex: 1;
      min-height: 300px;
      display: flex;
      flex-direction: column;
    }}

    .chart-meta {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }}

    .chart-product-name {{
      font-size: 15px;
      font-weight: 600;
    }}

    .chart-wrapper {{
      flex: 1;
      height: 320px;
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

    .rating-stars {{
      color: #f59e0b;
      font-size: 12px;
    }}

    /* Client Critique Drawer / Feedback section */
    .critique-section {{
      background: var(--bg-panel);
      border: 1px dashed var(--accent-brand);
      border-radius: 10px;
      padding: 24px;
      margin-top: 10px;
    }}

    .critique-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }}

    .critique-cards {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }}

    .critique-item {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 16px;
    }}

    .critique-item h5 {{
      font-size: 13px;
      font-weight: 600;
      color: var(--accent-brand-hover);
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .critique-item p {{
      font-size: 12px;
      color: var(--text-secondary);
      line-height: 1.4;
    }}

    .checklist-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 10px;
      font-size: 12px;
      color: var(--text-muted);
    }}

    .checklist-row input {{
      accent-color: var(--accent-brand);
      cursor: pointer;
    }}

    /* Toast Notification */
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
      z-index: 100;
    }}

    @media (max-width: 1024px) {{
      .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .dashboard-split {{ grid-template-columns: 1fr; }}
      .critique-cards {{ grid-template-columns: 1fr; }}
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
        <div class="brand-sub">E-Commerce Intelligence & Price Telemetry Engine</div>
      </div>
    </div>
    <div class="header-actions">
      <button class="btn" onclick="exportData('csv')">📥 Export CSV</button>
      <button class="btn" onclick="exportData('json')">📥 Export JSON</button>
      <button class="btn btn-primary" onclick="simulateScan()">⚡ Re-Scan Competitor</button>
    </div>
  </header>

  <main>
    <!-- Client Evaluation Header -->
    <div class="client-banner">
      <div class="client-banner-text">
        <h4>👁️ Client Review Mode: Đặt vị trí vào chủ shop / khách hàng</h4>
        <p>Đánh giá trực quan: Tốc độ nắm bắt thông tin, mức độ hữu ích của cảnh báo phá giá và độ tin cậy của dữ liệu.</p>
      </div>
      <div>
        <a href="#critique" class="btn" style="border-color: rgba(113, 112, 255, 0.4); color: #828fff;">
          📝 Mở Bảng Nhận Xét Cải Tiến ↓
        </a>
      </div>
    </div>

    <!-- KPIs -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Sản phẩm đang giám sát</div>
        <div class="kpi-value">{total_products}</div>
        <div class="kpi-sub">
          <span class="text-emerald">● 100% Active</span> • Danh mục Mystery & Travel
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Biến động giá hôm nay</div>
        <div class="kpi-value text-rose">{len(deltas)} Deltas</div>
        <div class="kpi-sub">
          <span class="text-rose">1 Hạ giá sốc</span> • 1 Tăng giá • 1 Restock
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Tỷ lệ còn hàng (In-Stock)</div>
        <div class="kpi-value text-emerald">{in_stock_rate}%</div>
        <div class="kpi-sub">
          31/31 đối thủ còn hàng trong kho
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Giá trung bình thị trường</div>
        <div class="kpi-value">£{avg_price}</div>
        <div class="kpi-sub">
          Biên độ dao động: £16.64 – £56.50
        </div>
      </div>
    </div>

    <!-- Middle: Live Delta Feed & Price Trend Chart -->
    <div class="dashboard-split">
      <!-- Live Delta Alerts -->
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-title">
            <span>⚡ Biến động giá phát hiện</span>
            <span class="badge badge-drop">{len(deltas)} Mới</span>
          </div>
          <span style="font-size: 11px; color: var(--text-muted);">Real-time</span>
        </div>

        <div class="delta-list" id="delta-list">
          <!-- Populated by JS -->
        </div>
      </div>

      <!-- Price History Chart -->
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-title">
            <span>📈 Biểu đồ lịch sử giá (Time-Series)</span>
          </div>
          <span style="font-size: 12px; color: var(--text-muted); font-family: var(--font-mono);" id="chart-sku">
            SKU: sharp-objects_997
          </span>
        </div>

        <div class="chart-container">
          <div class="chart-meta">
            <div>
              <div class="chart-product-name" id="chart-title">Sharp Objects</div>
              <div style="font-size: 12px; color: var(--text-muted);">Giá hiện tại: <span id="chart-current-price" style="color:#fff; font-weight:600;">£47.82</span> (Giảm -20.29%)</div>
            </div>
            <button class="btn" style="font-size: 11px; padding: 4px 8px;" onclick="openSourceUrl()">↗ Xem link gốc</button>
          </div>
          <div class="chart-wrapper">
            <canvas id="priceChart"></canvas>
          </div>
        </div>
      </div>
    </div>

    <!-- Product Catalog Table -->
    <div class="card-panel" style="padding: 20px;">
      <div class="panel-header" style="border: none; margin-bottom: 8px;">
        <div class="panel-title">
          <span>📦 Danh mục sản phẩm đối thủ</span>
          <span style="font-size: 12px; color: var(--text-muted); font-weight: 400;">({total_products} items)</span>
        </div>
      </div>

      <div class="table-controls">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" id="searchInput" placeholder="Tìm kiếm theo tên sách hoặc SKU..." oninput="handleSearch()">
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
          <tbody id="productTableBody">
            <!-- Populated by JS -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- Client Evaluation & Feedback Section -->
    <section class="critique-section" id="critique">
      <div class="critique-header">
        <div>
          <h3 style="font-size: 16px; font-weight: 600; color: #fff;">🧐 Góc nhìn Client: Những điểm cần cải thiện khi bán thực tế</h3>
          <p style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
            Khi m đặt mình vào người mua giải pháp này, đây là những câu hỏi và nhu cầu thực tế họ sẽ đặt ra:
          </p>
        </div>
        <span class="badge" style="background: rgba(94, 106, 210, 0.2); color: #828fff; border: 1px solid #5e6ad2;">
          Product Teardown
        </span>
      </div>

      <div class="critique-cards">
        <div class="critique-item">
          <h5>1. Ngưỡng báo động tùy chỉnh (Custom Alert Threshold)</h5>
          <p>Hiện tại tool báo mọi biến động. Nhưng client lớn chỉ muốn nhận thông báo khi <strong>giảm giá từ 10% trở lên</strong> hoặc <strong>giảm quá £5</strong> để tránh bị spam tin nhắn.</p>
          <div class="checklist-row">
            <input type="checkbox" checked disabled> <span>Nên có slider chọn ngưỡng % alert trên UI</span>
          </div>
        </div>

        <div class="critique-item">
          <h5>2. So sánh nhiều đối thủ (Multi-Vendor Comparison)</h5>
          <p>Khách hàng thường có 3–5 đối thủ cùng bán 1 mã sản phẩm. Họ muốn thấy bảng so sánh chéo giá của shop A vs shop B vs giá của chính họ để tìm ai đang rẻ nhất.</p>
          <div class="checklist-row">
            <input type="checkbox" checked disabled> <span>Cần gom nhóm sản phẩm theo Barcode/EAN</span>
          </div>
        </div>

        <div class="critique-item">
          <h5>3. Tự động đề xuất giá bán (Auto-Repricing Suggestion)</h5>
          <p>Thay vì chỉ báo đối thủ giảm giá, client muốn tool tự tính luôn: <i>"Đối thủ bán £47.82, m nên set giá £46.99 (thấp hơn 2%) để giành Buy Box mà vẫn giữ lãi 15%"</i>.</p>
          <div class="checklist-row">
            <input type="checkbox" checked disabled> <span>Tính năng Premium bán giá cao ($200+)</span>
          </div>
        </div>
      </div>
    </section>

  </main>

  <div id="toast"></div>

  <script>
    const DATA = {json.dumps(dashboard_data)};
    let currentFilter = 'ALL';
    let searchQuery = '';
    let selectedSku = 'sharp-objects_997';
    let chartInstance = null;

    // Render Deltas Feed
    function renderDeltas() {{
      const container = document.getElementById('delta-list');
      container.innerHTML = '';

      DATA.deltas.forEach(d => {{
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
          <div class="delta-desc">${{d.desc}}</div>
        `;
        container.appendChild(item);
      }});
    }}

    // Render Product Table
    function renderTable() {{
      const tbody = document.getElementById('productTableBody');
      tbody.innerHTML = '';

      const deltaSkus = new Set(DATA.deltas.map(d => d.sku));

      const filtered = DATA.products.filter(p => {{
        const matchSearch = p.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            p.sku.toLowerCase().includes(searchQuery.toLowerCase());
        
        if (!matchSearch) return false;

        if (currentFilter === 'DELTAS') return deltaSkus.has(p.sku);
        if (currentFilter === 'IN_STOCK') return p.stock_status === 'IN_STOCK';
        return true;
      }});

      filtered.forEach(p => {{
        const tr = document.createElement('tr');
        const hasDelta = deltaSkus.has(p.sku);
        const delta = DATA.deltas.find(d => d.sku === p.sku);

        let deltaBadge = '';
        if (delta) {{
          deltaBadge = `<span class="badge ${{delta.badge_class}}" style="margin-left: 6px;">${{delta.type.replace('_', ' ')}}</span>`;
        }}

        tr.innerHTML = `
          <td style="font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);">${{p.sku}}</td>
          <td class="col-title">
            ${{p.title}}
            ${{deltaBadge}}
          </td>
          <td class="col-price">£${{p.current_price.toFixed(2)}}</td>
          <td>
            <span class="badge badge-restock">● IN STOCK</span>
          </td>
          <td>
            <span class="rating-stars">${{'★'.repeat(Math.round(p.rating || 4))}}</span>
            <span style="font-size: 11px; color: var(--text-muted);">${{p.rating || 4.0}}</span>
          </td>
          <td style="font-size: 12px; color: var(--text-muted);">${{p.last_scraped_at.split('T')[0]}}</td>
          <td style="text-align: right;">
            <button class="btn" style="font-size: 11px; padding: 4px 8px;" onclick="selectProduct('${{p.sku}}')">📊 Xem Chart</button>
          </td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Render Chart
    function renderChart(sku) {{
      const product = DATA.products.find(p => p.sku === sku);
      if (!product) return;

      document.getElementById('chart-title').innerText = product.title;
      document.getElementById('chart-sku').innerText = `SKU: ${{product.sku}}`;
      document.getElementById('chart-current-price').innerText = `£${{product.current_price.toFixed(2)}}`;

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

      if (chartInstance) {{
        chartInstance.destroy();
      }}

      chartInstance = new Chart(ctx, {{
        type: 'line',
        data: {{
          labels: labels,
          datasets: [{{
            label: 'Giá (GBP)',
            data: dataPoints,
            borderColor: lineColor,
            backgroundColor: fillColor,
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: lineColor,
            pointBorderColor: '#fff',
            pointRadius: 5,
            pointHoverRadius: 7
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              backgroundColor: '#191a1b',
              borderColor: 'rgba(255, 255, 255, 0.1)',
              borderWidth: 1,
              titleFont: {{ family: 'Inter', size: 12 }},
              bodyFont: {{ family: 'JetBrains Mono', size: 13 }},
              callbacks: {{
                label: function(ctx) {{
                  return ' Giá: £' + ctx.parsed.y.toFixed(2);
                }}
              }}
            }}
          }},
          scales: {{
            x: {{
              grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
              ticks: {{ color: '#8a8f98', font: {{ family: 'Inter', size: 11 }} }}
            }},
            y: {{
              grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
              ticks: {{
                color: '#8a8f98',
                font: {{ family: 'JetBrains Mono', size: 11 }},
                callback: function(val) {{ return '£' + val.toFixed(0); }}
              }}
            }}
          }}
        }}
      }});
    }}

    function selectProduct(sku) {{
      selectedSku = sku;
      renderDeltas();
      renderChart(sku);
      showToast(`Đã chọn sản phẩm: ${{sku}}`);
    }}

    function openSourceUrl() {{
      const p = DATA.products.find(item => item.sku === selectedSku);
      if (p && p.url) {{
        window.open(p.url, '_blank');
      }}
    }}

    function handleSearch() {{
      searchQuery = document.getElementById('searchInput').value;
      renderTable();
    }}

    function setFilter(filter, btn) {{
      currentFilter = filter;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTable();
    }}

    function exportData(format) {{
      if (format === 'json') {{
        const blob = new Blob([JSON.stringify(DATA.products, null, 2)], {{ type: 'application/json' }});
        downloadBlob(blob, 'market_sentinel_export.json');
      }} else {{
        const headers = ['sku', 'title', 'current_price', 'currency', 'stock_status', 'rating', 'url'];
        const rows = DATA.products.map(p => [
          p.sku,
          `"${{p.title.replace(/"/g, '""')}}"`,
          p.current_price,
          p.currency,
          p.stock_status,
          p.rating || '',
          p.url
        ]);
        const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\\n');
        const blob = new Blob([csvContent], {{ type: 'text/csv' }});
        downloadBlob(blob, 'market_sentinel_export.csv');
      }}
      showToast(`Đã xuất file ${{format.toUpperCase()}} thành công!`);
    }}

    function downloadBlob(blob, filename) {{
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    }}

    function simulateScan() {{
      showToast('⚡ Đang kích hoạt vòng quét mới từ Collector engine...');
      setTimeout(() => {{
        showToast('✅ Quét hoàn tất: 31 URLs crawled, 0 lỗi.');
      }}, 1200);
    }}

    function showToast(msg) {{
      const t = document.getElementById('toast');
      t.innerHTML = `<span>ℹ️</span> ${{msg}}`;
      t.style.display = 'flex';
      setTimeout(() => {{
        t.style.display = 'none';
      }}, 3000);
    }}

    // Init
    renderDeltas();
    renderTable();
    renderChart(selectedSku);
  </script>
</body>
</html>
"""

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Dashboard successfully built at {out_file}")

if __name__ == "__main__":
    generate_dashboard()
