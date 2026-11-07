"""Command Line Interface for Market Sentinel.

Entrypoint for crawling catalogs, monitoring price deltas, exporting datasets,
running AI Businessman commercial advisory, and dispatching alerts.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.advisor.businessman import BusinessmanAdvisor
from src.collector.client import ResilientCollector
from src.domain.models import DeltaEvent, PriceDelta
from src.domain.parser import EcommerceCatalogParser
from src.domain.service import SentinelService
from src.notifier.exporter import DataExporter
from src.notifier.telegram import TelegramNotifier
from src.repository.sqlite import SQLiteProductRepository

# Configure clean logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("market_sentinel")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="market-sentinel",
        description="Resilient E-Commerce Scraping & Market Intelligence Engine",
    )
    parser.add_argument(
        "--db",
        default=os.getenv("DATABASE_URL", "data/sentinel.db").replace("sqlite:///", ""),
        help="Path to SQLite database file (default: data/sentinel.db)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Scrape command
    scrape_cmd = subparsers.add_parser("scrape", help="Scrape a catalog URL and record snapshots")
    scrape_cmd.add_argument("--url", required=True, help="Target URL to crawl")
    scrape_cmd.add_argument("--dry-run", action="store_true", help="Do not send live Telegram notifications")
    scrape_cmd.add_argument("--alert", action="store_true", help="Dispatch Telegram notifications for price deltas")
    scrape_cmd.add_argument("--min-drop", type=float, default=0.0, help="Noise filter: minimum percentage drop (e.g. 5.0)")
    scrape_cmd.add_argument("--no-ai", action="store_true", help="Disable AI Businessman briefing")
    scrape_cmd.add_argument("--timeout", type=float, default=15.0, help="HTTP request timeout in seconds")

    # 2. Advise command (AI Businessman)
    advise_cmd = subparsers.add_parser("advise", help="Run AI Businessman strategic assessment on a product delta")
    advise_cmd.add_argument("--sku", default="sharp-objects_997", help="Product SKU identifier")
    advise_cmd.add_argument("--title", default="Sharp Objects", help="Product title")
    advise_cmd.add_argument("--old-price", type=float, default=59.99, help="Original price")
    advise_cmd.add_argument("--new-price", type=float, default=47.82, help="Competitor new price")
    advise_cmd.add_argument("--cost-price", type=float, default=None, help="Your cost price (COGS)")
    advise_cmd.add_argument("--currency", default="GBP", help="Currency code")

    # 3. Test-alert command
    alert_cmd = subparsers.add_parser("test-alert", help="Dispatch a test Telegram alert with AI briefing")
    alert_cmd.add_argument("--dry-run", action="store_true", default=True, help="Dry-run output to terminal")

    # 4. Export command
    export_cmd = subparsers.add_parser("export", help="Export tracked catalog to CSV or JSON")
    export_cmd.add_argument("--output", required=True, help="Destination output file path")
    export_cmd.add_argument("--format", choices=["csv", "json"], default="csv", help="Export format")

    # 5. History command
    hist_cmd = subparsers.add_parser("history", help="View price history for a given SKU")
    hist_cmd.add_argument("--sku", required=True, help="Product SKU identifier")
    hist_cmd.add_argument("--limit", type=int, default=20, help="Number of snapshot records to display")

    # 6. Status command
    subparsers.add_parser("status", help="Display overview statistics of database and monitoring state")

    return parser


def handle_scrape(args: argparse.Namespace, repo: SQLiteProductRepository) -> int:
    collector = ResilientCollector(timeout=args.timeout)
    service = SentinelService(repository=repo, collector=collector, parser=EcommerceCatalogParser())

    print(f"\n🚀 Scanning target: {args.url}")
    try:
        summary = service.scan_catalog(args.url)
    except Exception as exc:
        logger.error(f"Scrape failed: {exc}")
        return 1
    finally:
        collector.close()

    print("\n" + "=" * 65)
    print(f"📊 CRAWL REPORT: {args.url}")
    print("=" * 65)
    print(f"• Total Cards Found:    {summary.total_found}")
    print(f"• Successfully Parsed:  {len(summary.items_scraped)}")
    print(f"• Malformed/Ignored:    {summary.failed_cards_count}")
    print(f"• Price Deltas Detected:{len(summary.deltas_detected)}")
    print(f"• Fetch Latency:        {summary.latency_ms:.1f} ms")
    print("-" * 65)

    if summary.items_scraped:
        print("\nTop 5 Scraped Items:")
        for idx, item in enumerate(summary.items_scraped[:5], 1):
            disc_str = f" (-{item.discount_percentage}%)" if item.discount_percentage > 0 else ""
            print(f"  {idx}. [{item.stock_status.value}] {item.title[:45]:<45} | {item.current_price:,.2f} {item.currency}{disc_str}")

    if summary.deltas_detected:
        print("\n⚡ Detected Price / Stock Deltas:")
        for delta in summary.deltas_detected:
            sign = "+" if delta.percentage_change > 0 else ""
            print(f"  [{delta.event.value}] {delta.product_title[:35]:<35} | {delta.old_price:,.2f} -> {delta.new_price:,.2f} ({sign}{delta.percentage_change}%)")

        if args.alert:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            notifier = TelegramNotifier(
                bot_token=bot_token,
                chat_id=chat_id,
                dry_run=args.dry_run,
                min_drop_percent=args.min_drop,
                enable_ai_advisor=not args.no_ai,
            )
            sent = notifier.notify_deltas(summary.deltas_detected)
            mode_str = " (DRY-RUN)" if notifier.dry_run else ""
            print(f"\n📢 Telegram Notifications Dispatched: {sent}{mode_str}")

    print("\n✅ Crawl snapshot committed to database.\n")
    return 0


def handle_advise(args: argparse.Namespace) -> int:
    diff = round(args.new_price - args.old_price, 2)
    pct = round((diff / args.old_price) * 100, 2) if args.old_price else 0.0

    if diff < 0:
        event = DeltaEvent.PRICE_DROP
    elif diff > 0:
        event = DeltaEvent.PRICE_HIKE
    else:
        event = DeltaEvent.NO_CHANGE

    delta = PriceDelta(
        sku=args.sku,
        product_title=args.title,
        old_price=args.old_price,
        new_price=args.new_price,
        difference=diff,
        percentage_change=pct,
        event=event,
        currency=args.currency,
        url=f"https://books.toscrape.com/{args.sku}",
    )

    advisor = BusinessmanAdvisor()
    advice = advisor.advise(delta, cost_price=args.cost_price)

    print("\n" + "=" * 65)
    print("🧠 AI BUSINESSMAN STRATEGIC BRIEFING")
    print("=" * 65)
    print(f"• Target Product:       {advice.product_title} ({advice.sku})")
    print(f"• Movement:             {args.old_price:,.2f} -> {args.new_price:,.2f} {args.currency} ({pct:+.2f}%)")
    print(f"• Threat Assessment:    [{advice.threat_level}]")
    print(f"• Intent Diagnosis:     {advice.intent_diagnosis}")
    print(f"• Target Counter-Price: {advice.recommended_counter_price:,.2f} {args.currency}")
    print(f"• Projected Margin:     {advice.projected_margin_pct:.1f}%")
    print("-" * 65)
    print(f"🎯 Recommended Action:\n  {advice.tactical_action}")
    print("=" * 65 + "\n")
    return 0


def handle_test_alert(args: argparse.Namespace) -> int:
    delta = PriceDelta(
        sku="sharp-objects_997",
        product_title="Sharp Objects",
        old_price=59.99,
        new_price=47.82,
        difference=-12.17,
        percentage_change=-20.29,
        event=DeltaEvent.PRICE_DROP,
        currency="GBP",
        url="https://books.toscrape.com/catalogue/sharp-objects_997/index.html",
    )
    notifier = TelegramNotifier(dry_run=args.dry_run, enable_ai_advisor=True)
    sent = notifier.notify_deltas([delta])
    print(f"✅ Dispatched {sent} test alert(s).")
    return 0


def handle_export(args: argparse.Namespace, repo: SQLiteProductRepository) -> int:
    products = repo.list_products()
    if not products:
        print("⚠️ No products tracked in database yet. Run `scrape` first.")
        return 1

    if args.format == "csv":
        out_path = DataExporter.export_csv(products, args.output)
    else:
        out_path = DataExporter.export_json(products, args.output)

    print(f"✅ Successfully exported {len(products)} products to {out_path}")
    return 0


def handle_history(args: argparse.Namespace, repo: SQLiteProductRepository) -> int:
    product = repo.get_product(args.sku)
    if not product:
        print(f"❌ Product with SKU '{args.sku}' not found.")
        return 1

    history = repo.get_price_history(args.sku, limit=args.limit)
    print("\n" + "=" * 60)
    print(f"📈 PRICE HISTORY: {product.title}")
    print(f"SKU: {product.sku} | URL: {product.url}")
    print("=" * 60)
    print(f"{'TIMESTAMP':<28} | {'PRICE':<12} | {'STATUS':<15}")
    print("-" * 60)
    for row in history:
        print(f"{row['recorded_at']:<28} | {row['price']:<12.2f} | {row['stock_status']:<15}")
    print("-" * 60 + "\n")
    return 0


def handle_status(repo: SQLiteProductRepository) -> int:
    products = repo.list_products()
    print("\n" + "=" * 50)
    print("🛡️ MARKET SENTINEL STATUS")
    print("=" * 50)
    print(f"• Total Products Tracked:  {len(products)}")
    if products:
        currencies = set(p.currency for p in products)
        in_stock_cnt = sum(1 for p in products if p.stock_status.value == "IN_STOCK")
        print(f"• Currencies:              {', '.join(currencies)}")
        print(f"• In-Stock Ratio:          {in_stock_cnt}/{len(products)} ({in_stock_cnt/len(products)*100:.1f}%)")
    print(f"• Database File:           {repo.db_path}")
    print("=" * 50 + "\n")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo = SQLiteProductRepository(db_path=args.db)
    try:
        if args.command == "scrape":
            return handle_scrape(args, repo)
        elif args.command == "advise":
            return handle_advise(args)
        elif args.command == "test-alert":
            return handle_test_alert(args)
        elif args.command == "export":
            return handle_export(args, repo)
        elif args.command == "history":
            return handle_history(args, repo)
        elif args.command == "status":
            return handle_status(repo)
        return 0
    finally:
        repo.close()


if __name__ == "__main__":
    sys.exit(main())
