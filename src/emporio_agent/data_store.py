"""Loading and cleaning of the store's CSV files.

The CSVs are tiny (tens of rows), so they are kept in memory as pandas DataFrames.
This module only loads and cleans: correct types, parsed JSON specs, category name
joined to each product, and accent-free columns for searching and identity checks.
Business rules (what counts as "available", which price to show) live in the tools.
"""

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from emporio_agent.config import RAW_DIR


def normalize(text: str) -> str:
    """Lowercase, strip accents and collapse whitespace — used for text search."""
    text = unicodedata.normalize("NFKD", str(text).lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def digits_only(text: str) -> str:
    return re.sub(r"\D", "", str(text))


@dataclass(frozen=True)
class DataStore:
    products: pd.DataFrame
    categories: pd.DataFrame
    promotions: pd.DataFrame
    orders: pd.DataFrame
    order_items: pd.DataFrame
    customers: pd.DataFrame


def _spec_terms(specs: dict) -> list[str]:
    """Words customers use for features that the specs only encode as values."""
    terms = []
    if specs.get("electronics") == "yes":
        terms += ["elétrico", "eletroacústico", "captação", "captador"]
    if specs.get("strings") == "steel":
        terms.append("aço")
    return terms


def _load_products(raw_dir: Path, categories: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(raw_dir / "products.csv")
    df["specs"] = df["specs"].apply(lambda s: json.loads(s) if isinstance(s, str) and s else {})
    df["created_at"] = pd.to_datetime(df["created_at"])
    df = df.merge(
        categories[["category_id", "name"]].rename(columns={"name": "category"}),
        on="category_id",
        how="left",
    )
    # Search text: name + category + spec values (e.g. "nylon", "Spruce"). The description is left
    # out on purpose: some contradict the product (product 135, "Music Man Bass 1X", is described
    # as a Fender Jazz Bass), so searching "Fender" would return it.
    # Customer words for features are derived from the specs instead (e.g. electronics = yes).
    df["search_text"] = df.apply(
        lambda r: normalize(
            " ".join([r["name"], r["category"], *map(str, r["specs"].values()), *_spec_terms(r["specs"])])
        ),
        axis=1,
    )
    return df.sort_values("product_id").reset_index(drop=True)


def _load_promotions(raw_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_dir / "promotions.csv")
    df["is_active"] = df["is_active"].astype(bool)
    return df


def _load_orders(raw_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_dir / "orders.csv", dtype={"tracking_code": "string", "notes": "string"})
    for col in ("order_date", "estimated_delivery"):
        df[col] = pd.to_datetime(df[col])
    return df


def _load_customers(raw_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_dir / "customers.csv")
    df["email_norm"] = df["email"].str.strip().str.lower()
    df["phone_digits"] = df["phone"].apply(digits_only)
    return df


def load_data(raw_dir: Path = RAW_DIR) -> DataStore:
    categories = pd.read_csv(raw_dir / "categories.csv")
    return DataStore(
        products=_load_products(raw_dir, categories),
        categories=categories,
        promotions=_load_promotions(raw_dir),
        orders=_load_orders(raw_dir),
        order_items=pd.read_csv(raw_dir / "order_items.csv"),
        customers=_load_customers(raw_dir),
    )


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    """Load the data once and reuse it for the whole session."""
    return load_data()
