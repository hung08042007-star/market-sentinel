# Frontend Development Rules — Commercial B2B SaaS for Sellers

## Persona & Product Standard
You are building **Market Sentinel** — a commercial B2B Price Intelligence & Margin Protection SaaS for e-commerce sellers, shop owners, and brand managers.
Target Reference: Stripe Dashboard, Shopify Polaris, Linear, modern clean SaaS.

## Core Directives
1. **Zero Developer Slop:**
   - NEVER show raw technical internals to shop owners: No `GET 200 OK`, no `ETag`, no `SQLite WAL`, no `Latency (ms)`, no raw JSON dumps or terminal logs on the primary screen.
   - Use plain business terminology: "Giá đối thủ", "Biên lợi nhuận", "Nguy cơ mất khách", "Cơ hội tăng lãi", "Đề xuất đối sách".
2. **Action-First Architecture:**
   - **Hero Alert Banner:** Highlight immediate items requiring decisions today (who dropped price, competitor intent, counter-price recommendation, preserved net margin).
   - **1-Click Intake:** Clear, welcoming URL paste bar for Shopee/Lazada/Tiki/web competitor links.
   - **Shopkeeper Data Table:** Clear product titles, current prices, stock status, comparison badges (Đang rẻ hơn / Đang đắt hơn).
   - **Telegram 1-Tap Connect:** Instant preview of 8 AM morning mobile digest.
3. **Aesthetic & Density:**
   - Zinc/Slate dark theme (`#0c0d12`, surface cards `#151720`, crisp 1px borders `rgba(255,255,255,0.08)`).
   - Crisp semantic colors: Emerald for profit gains & safe margins, Coral/Rose for competitor price cuts, Sky/Indigo for primary buttons.
   - Legible typography: Inter for Vietnamese UI copy, JetBrains Mono strictly for prices and SKU numbers.
