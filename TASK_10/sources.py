"""sources.py: teen mock data sources (real APIs ke liye yahi file badlein)."""
import asyncio


class SourceError(Exception):
    """Source ne error diya."""


def _authenticate(source: str, key: str, prefix: str) -> None:
    if not key.startswith(prefix):
        raise SourceError(f"{source}: 401 Unauthorized (API key galat hai)")


async def fetch_crm(api_key: str) -> list[dict]:
    await asyncio.sleep(1.2)
    _authenticate("CRM", api_key, "crm-")
    return [
        {"customer_id": 1, "name": "Ali Khan",    "city": "Lahore"},
        {"customer_id": 2, "name": "Sara Ahmed",  "city": "Karachi"},
        {"customer_id": 3, "name": "Bilal Raza",  "city": "Islamabad"},
        {"customer_id": 4, "name": "Hina Malik",  "city": "Lahore"},
        {"customer_id": 5, "name": "Usman Tariq", "city": "Multan"},
    ]


async def fetch_billing(api_key: str) -> list[dict]:
    await asyncio.sleep(0.8)
    _authenticate("Billing", api_key, "bill-")
    return [
        {"customer_id": 1,  "amount": "1200.50", "status": "paid"},
        {"customer_id": 1,  "amount": "800",     "status": "pending"},
        {"customer_id": 2,  "amount": "2500.00", "status": "paid"},
        {"customer_id": 3,  "amount": "450.25",  "status": "pending"},
        {"customer_id": 4,  "amount": "3000",    "status": "paid"},
        {"customer_id": 4,  "amount": "1500",    "status": "paid"},
        {"customer_id": 99, "amount": "700",     "status": "paid"},   # CRM mein nahi (orphan)
    ]


async def fetch_support(api_key: str) -> list[dict]:
    await asyncio.sleep(1.6)
    _authenticate("Support", api_key, "sup-")
    return [
        {"customer_id": 1, "priority": "high",   "status": "open"},
        {"customer_id": 2, "priority": "low",    "status": "closed"},
        {"customer_id": 2, "priority": "medium", "status": "open"},
        {"customer_id": 3, "priority": "high",   "status": "open"},
        {"customer_id": 3, "priority": "low",    "status": "open"},
        {"customer_id": 3, "priority": "medium", "status": "closed"},
        {"customer_id": 5, "priority": "low",    "status": "closed"},
    ]