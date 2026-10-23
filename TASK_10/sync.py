"""sync.py: teen sources se data laa kar merge karta hai aur dashboard dikhata hai."""
from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass

from config import ConfigError, Settings, load_settings
from sources import SourceError, fetch_billing, fetch_crm, fetch_support


@dataclass
class SourceResult:
    name: str
    data: list | None
    error: str | None
    seconds: float

    @property
    def ok(self) -> bool:
        return self.error is None


def ensure_venv() -> None:
    if sys.prefix == sys.base_prefix:
        raise SystemExit("❌ Virtual environment active nahi hai. Pehle venv activate karein (Cell 1).")


async def pull(name: str, coro, timeout: float) -> SourceResult:
    """Ek source se data lao. Koi bhi error bahar nahi jaata."""
    start = time.perf_counter()
    try:
        data, error = await asyncio.wait_for(coro, timeout), None
    except asyncio.TimeoutError:
        data, error = None, f"timed out after {timeout:.1f}s"
    except SourceError as e:
        data, error = None, str(e)
    except Exception as e:
        data, error = None, f"unexpected {type(e).__name__}: {e}"

    seconds = time.perf_counter() - start
    detail = error if error else f"{len(data)} records"
    print(f"  {'✅' if error is None else '❌'} {name:<8} {seconds:>5.2f}s  {detail}")
    return SourceResult(name, data, error, seconds)


async def run_sync(settings: Settings) -> list[SourceResult]:
    print("Teeno sources se ek saath data aa raha hai...")
    return await asyncio.gather(
        pull("CRM",     fetch_crm(settings.crm_key),         settings.timeout),
        pull("Billing", fetch_billing(settings.billing_key), settings.timeout),
        pull("Support", fetch_support(settings.support_key), settings.timeout),
    )


def merge(results: list[SourceResult]) -> tuple[list[dict], int]:
    """customer_id par teeno sources jodo. Return: (rows, orphan_count)."""
    data = {r.name: (r.data or []) for r in results}      # fail hua source = khali list

    customers = {
        c["customer_id"]: {**c, "billed": 0.0, "paid": 0.0, "tickets": 0, "open_tickets": 0}
        for c in data["CRM"]
    }
    orphans = 0

    for inv in data["Billing"]:
        row = customers.get(inv["customer_id"])
        if row is None:
            orphans += 1
            continue
        amount = float(inv["amount"])
        row["billed"] += amount
        if inv["status"] == "paid":
            row["paid"] += amount

    for ticket in data["Support"]:
        row = customers.get(ticket["customer_id"])
        if row is None:
            orphans += 1
            continue
        row["tickets"] += 1
        if ticket["status"] == "open":
            row["open_tickets"] += 1

    return list(customers.values()), orphans


def show_dashboard(results, rows, orphans, wall) -> None:
    width = 74
    print("\n" + "=" * width)
    print("DATA SYNC DASHBOARD".center(width))
    print("=" * width)

    print("SOURCES")
    for r in results:
        status = f"OK, {len(r.data)} records" if r.ok else f"FAILED: {r.error}"
        print(f"  {r.name:<8} {r.seconds:>5.2f}s  {status}")

    print("\nCUSTOMERS (merged)")
    print("-" * width)
    print(f"{'ID':<4}{'Name':<14}{'City':<11}{'Billed':>10}{'Paid':>10}{'Tickets':>9}  Status")
    for c in rows:
        tickets = f"{c['open_tickets']}/{c['tickets']}"
        status = "DUE" if c["billed"] - c["paid"] > 0.005 else "OK"
        print(f"{c['customer_id']:<4}{c['name']:<14}{c['city']:<11}"
              f"{c['billed']:>10,.2f}{c['paid']:>10,.2f}{tickets:>9}  {status}")

    billed = sum(c["billed"] for c in rows)
    paid = sum(c["paid"] for c in rows)
    open_t = sum(c["open_tickets"] for c in rows)
    all_t = sum(c["tickets"] for c in rows)
    sequential = sum(r.seconds for r in results)

    print("\n" + "=" * width)
    print(f"Customers: {len(rows)} | Billed: Rs. {billed:,.2f} | Paid: Rs. {paid:,.2f} "
          f"| Outstanding: Rs. {billed - paid:,.2f}")
    print(f"Tickets: {open_t} open / {all_t} total | Unmatched records: {orphans}")
    print(f"Wall time: {wall:.2f}s | Sequential hota to: ~{sequential:.2f}s")
    print("=" * width)


def main() -> int:
    ensure_venv()
    try:
        settings = load_settings()
    except ConfigError as e:
        print(f"❌ Config error: {e}")
        return 2

    print(f"Config loaded from: {settings.env_file}\n")
    start = time.perf_counter()
    results = asyncio.run(run_sync(settings))
    wall = time.perf_counter() - start

    rows, orphans = merge(results)
    show_dashboard(results, rows, orphans, wall)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())