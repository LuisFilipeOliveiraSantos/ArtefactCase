"""Tools the agent can call, and the business rules behind them.

Each tool is a plain Python function returning a JSON-serializable dict, plus a
schema (name, description, input_schema) that tells the LLM when and how to call it.
The descriptions matter as much as the code: they are how the model decides which
tool fits a customer's question.

Business rules applied here (see docs/data_analysis.md):
- A product is "available" only when status is "active" AND stock > 0.
- Only promotions with is_active = 1 count; if a product had two, the larger wins
  (promotions do not stack, manual §6.2).
- The 5% PIX discount applies only to products without an active promotion (§6.2).
- Order data is shown only when the order number matches the customer's e-mail or phone (LGPD, §9).
"""

import re
from datetime import datetime, time, timedelta
from typing import Any, Callable

import pandas as pd

from emporio_agent.config import STORE_TZ
from emporio_agent.data_store import digits_only, get_store, normalize
from emporio_agent.policies import get_policy_index

PIX_DISCOUNT = 0.05

# Opening hours from manual §2 (weekday(): Monday = 0 ... Sunday = 6).
OPENING_HOURS = {d: (time(9), time(18)) for d in range(5)} | {5: (time(9), time(13))}
WEEKDAYS_PT = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

ORDER_STATUS_PT = {
    "pending": "aguardando pagamento/processamento",
    "confirmed": "confirmado, em separação",
    "shipped": "enviado",
    "delivered": "entregue",
    "cancelled": "cancelado",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stem(token: str) -> str:
    """Very light Portuguese stemming so singular and plural match ("violões" -> "violao")."""
    if token.endswith(("oes", "aes")):
        return token[:-3] + "ao"
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _stems(text: str) -> set[str]:
    return {_stem(t) for t in re.findall(r"[a-z0-9]+", normalize(text))}


def _money(value: float) -> float:
    return round(float(value), 2)


def _active_discounts() -> dict[int, dict[str, Any]]:
    """Best active promotion per product id."""
    promos = get_store().promotions
    active = promos[promos["is_active"]].sort_values("discount_percent", ascending=False)
    best = active.drop_duplicates("product_id")
    return {
        int(r.product_id): {"discount_percent": int(r.discount_percent), "campaign": r.description}
        for r in best.itertuples()
    }


def _availability(status: str, stock: int) -> str:
    if status == "discontinued":
        return "discontinued"
    if status == "coming_soon":
        return "coming_soon"
    return "available" if stock > 0 else "out_of_stock"


def _product_summary(row: pd.Series, discounts: dict[int, dict[str, Any]]) -> dict[str, Any]:
    price = _money(row["price_brl"])
    summary = {
        "product_id": int(row["product_id"]),
        "name": row["name"],
        "category": row["category"],
        "list_price_brl": price,
        "availability": _availability(row["status"], int(row["stock_quantity"])),
        "stock_quantity": int(row["stock_quantity"]),
    }
    promo = discounts.get(int(row["product_id"]))
    if promo:
        summary["promotion"] = {
            "campaign": promo["campaign"],
            "discount_percent": promo["discount_percent"],
            "promotional_price_brl": _money(price * (1 - promo["discount_percent"] / 100)),
        }
        summary["pix_price_brl"] = None  # PIX discount does not stack with promotions
    else:
        summary["pix_price_brl"] = _money(price * (1 - PIX_DISCOUNT))
    return summary


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def search_products(
    query: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    only_available: bool = True,
    limit: int = 10,
) -> dict[str, Any]:
    products = get_store().products
    mask = pd.Series(True, index=products.index)

    if category:
        wanted = _stems(category)
        mask &= products["category"].apply(lambda c: wanted <= _stems(c))
    if query:
        wanted = _stems(query)
        mask &= products["search_text"].apply(lambda t: wanted <= _stems(t))
    if min_price is not None:
        mask &= products["price_brl"] >= min_price
    if max_price is not None:
        mask &= products["price_brl"] <= max_price
    if only_available:
        mask &= (products["status"] == "active") & (products["stock_quantity"] > 0)

    found = products[mask].sort_values("price_brl")
    discounts = _active_discounts()
    return {
        "total_found": len(found),
        "products": [_product_summary(r, discounts) for _, r in found.head(limit).iterrows()],
    }


def get_product_details(product_id: int) -> dict[str, Any]:
    products = get_store().products.set_index("product_id", drop=False)
    if product_id not in products.index:
        return {"error": f"Produto {product_id} não encontrado no catálogo."}
    row = products.loc[product_id]
    details = _product_summary(row, _active_discounts())
    details["description"] = row["description"]
    details["specs"] = row["specs"]
    return details


def list_active_promotions() -> dict[str, Any]:
    products = get_store().products.set_index("product_id", drop=False)
    discounts = _active_discounts()
    items = [_product_summary(products.loc[pid], discounts) for pid in sorted(discounts)]
    return {"active_promotions": items}


def get_order_status(order_id: int, email_or_phone: str, now: datetime | None = None) -> dict[str, Any]:
    store = get_store()
    not_found = {
        "error": "Pedido não encontrado ou o contato informado não confere com o cadastro. "
        "Peça ao cliente para conferir o número do pedido e o e-mail ou telefone usado na compra."
    }
    orders = store.orders.set_index("order_id", drop=False)
    if order_id not in orders.index:
        return not_found  # same message as a contact mismatch, so order ids can't be probed

    order = orders.loc[order_id]
    customer = store.customers.set_index("customer_id").loc[order["customer_id"]]
    contact = email_or_phone.strip().lower()
    phone = digits_only(contact)
    email_ok = contact == customer["email_norm"]
    phone_ok = len(phone) >= 8 and customer["phone_digits"].endswith(phone[-8:])
    if not (email_ok or phone_ok):
        return not_found

    items = store.order_items[store.order_items["order_id"] == order_id].merge(
        store.products[["product_id", "name"]], on="product_id", how="left"
    )
    today = (now or datetime.now(STORE_TZ)).date()
    estimated = order["estimated_delivery"]
    result: dict[str, Any] = {
        "order_id": int(order_id),
        "customer_first_name": customer["name"].split()[0],
        "status": order["status"],
        "status_pt": ORDER_STATUS_PT.get(order["status"], order["status"]),
        "order_date": order["order_date"].date().isoformat(),
        "total_paid_brl": _money(order["total_brl"]),
        "payment_method": order["payment_method"],
        "items": [{"product": r.name, "quantity": int(r.quantity)} for r in items.itertuples()],
        "tracking_code": None if pd.isna(order["tracking_code"]) else order["tracking_code"],
        "estimated_delivery": None if pd.isna(estimated) else estimated.date().isoformat(),
        "today": today.isoformat(),
    }
    if not pd.isna(order["notes"]):
        result["notes"] = order["notes"]
    if not pd.isna(estimated):
        days = (today - estimated.date()).days
        result["days_since_estimated_delivery"] = days
        if order["status"] == "shipped" and days > 0:
            result["delayed"] = True
    return result


def search_policies(query: str) -> dict[str, Any]:
    results = get_policy_index().search(query, k=3)
    if not results:
        return {"sections": [], "note": "Nenhuma seção do manual trata desse assunto."}
    return {"sections": [{"title": s.title, "content": s.content} for s, _ in results]}


def get_store_status(now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(STORE_TZ)
    hours = OPENING_HOURS.get(now.weekday())
    is_open = bool(hours and hours[0] <= now.time() < hours[1])

    next_opening = None
    if not is_open:
        for offset in range(0, 8):
            day = now + timedelta(days=offset)
            h = OPENING_HOURS.get(day.weekday())
            if h and (offset > 0 or now.time() < h[0]):
                next_opening = f"{WEEKDAYS_PT[day.weekday()]} {day.date().isoformat()} às {h[0]:%H:%M}"
                break

    return {
        "now": now.strftime("%Y-%m-%d %H:%M"),
        "weekday": WEEKDAYS_PT[now.weekday()],
        "is_open_now": is_open,
        "today_hours": f"{hours[0]:%H:%M}–{hours[1]:%H:%M}" if hours else "fechado",
        "next_opening": next_opening,
        "note": "Feriados não estão cadastrados; em feriados a loja fica fechada (manual §2).",
    }


# ---------------------------------------------------------------------------
# Schemas shown to the LLM and dispatcher
# ---------------------------------------------------------------------------

CATEGORIES = [
    "Guitarras", "Baixos", "Baterias e Percussão", "Teclados e Pianos", "Violões",
    "Instrumentos de Sopro (Madeiras)", "Instrumentos de Sopro (Metais)", "Cordas Orquestrais", "Ukuleles",
]

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_products",
        "description": (
            "Search the instrument catalog. Use it for ANY question about price, availability, stock "
            "or recommendations — never state a price or availability without calling it. "
            "Returns list price, active promotion (if any), PIX price and availability "
            "(available, out_of_stock, discontinued, coming_soon). Results are sorted by price."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Brand, model or feature words, e.g. 'Takamine GD20', 'nylon', 'elétrico'."},
                "category": {"type": "string", "enum": CATEGORIES},
                "min_price": {"type": "number", "description": "Minimum list price in BRL."},
                "max_price": {"type": "number", "description": "Maximum list price in BRL."},
                "only_available": {
                    "type": "boolean",
                    "description": "Default true. Set false to also see out-of-stock, discontinued or coming-soon items (e.g. when the customer asks about a specific model).",
                },
                "limit": {"type": "integer", "description": "Max results (default 10)."},
            },
        },
    },
    {
        "name": "get_product_details",
        "description": "Full details of one product (description and technical specs such as top wood, strings, electronics). Use after search_products when the customer wants to know more about a specific item.",
        "input_schema": {
            "type": "object",
            "properties": {"product_id": {"type": "integer"}},
            "required": ["product_id"],
        },
    },
    {
        "name": "list_active_promotions",
        "description": "List all promotions active right now, with original price, discount and promotional price. Use when the customer asks about deals, discounts or a specific campaign (e.g. Black Friday).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_order_status",
        "description": (
            "Look up an order: status, items, total paid, tracking code and estimated delivery. "
            "Requires the order number AND the e-mail or phone used in the purchase — ask the customer "
            "for both before calling. Also use it before applying return/exchange rules to an order."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "email_or_phone": {"type": "string"},
            },
            "required": ["order_id", "email_or_phone"],
        },
    },
    {
        "name": "search_policies",
        "description": (
            "Search the store policy manual: address and contacts, opening hours, payment and installments, "
            "returns, exchanges, warranty, shipping, promotions rules, accessories, privacy. "
            "Write the query with the manual's vocabulary in Portuguese (e.g. 'entrega outras cidades prazo', "
            "'devolução arrependimento', 'parcelamento cartão')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_store_status",
        "description": "Current date and time in Campo Grande and whether the store is open now, with the next opening time. Use for 'are you open?' questions and whenever today's date matters (e.g. counting days for a return).",
        "input_schema": {"type": "object", "properties": {}},
    },
]

TOOL_FUNCTIONS: dict[str, Callable[..., dict[str, Any]]] = {
    "search_products": search_products,
    "get_product_details": get_product_details,
    "list_active_promotions": list_active_promotions,
    "get_order_status": get_order_status,
    "search_policies": search_policies,
    "get_store_status": get_store_status,
}


def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool requested by the LLM. Errors are returned, never raised."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return func(**arguments)
    except TypeError as exc:  # missing or unexpected arguments
        return {"error": f"Invalid arguments for {name}: {exc}"}
