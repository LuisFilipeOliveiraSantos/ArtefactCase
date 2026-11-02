import pandas as pd
import pytest

from emporio_agent.data_store import digits_only, get_store, normalize


@pytest.fixture(scope="module")
def store():
    return get_store()


def test_normalize_strips_accents_and_spaces():
    assert normalize("  Violão   Elétrico ") == "violao eletrico"


def test_digits_only():
    assert digits_only("(67) 99812-3456") == "67998123456"


def test_all_tables_load_with_expected_sizes(store):
    assert len(store.products) == 65
    assert len(store.categories) == 9
    assert len(store.promotions) == 25
    assert len(store.orders) == 20
    assert len(store.order_items) == 22
    assert len(store.customers) == 50


def test_every_product_has_a_category_name(store):
    assert store.products["category"].notna().all()
    takamine = store.products.set_index("product_id").loc[95]
    assert takamine["category"] == "Violões"


def test_specs_are_parsed_into_dicts(store):
    specs = store.products.set_index("product_id").loc[81, "specs"]
    assert isinstance(specs, dict)
    assert specs["strings"] == "nylon"


def test_search_text_is_accent_free_and_includes_specs(store):
    text = store.products.set_index("product_id").loc[81, "search_text"]
    assert "violoes" in text  # category, without the accent
    assert "spruce" in text  # spec value


def test_products_are_sorted_by_id(store):
    assert store.products["product_id"].is_monotonic_increasing


def test_known_data_issues_are_preserved(store):
    """Cleaning must not hide the inconsistencies the tools need to handle."""
    products = store.products.set_index("product_id")
    assert products.loc[96, "status"] == "active" and products.loc[96, "stock_quantity"] == 0
    assert products.loc[136, "status"] == "discontinued" and products.loc[136, "stock_quantity"] > 0
    assert products.loc[130, "status"] == "coming_soon"


def test_only_four_promotions_are_active(store):
    active = store.promotions[store.promotions["is_active"]]
    assert sorted(active["product_id"]) == [90, 94, 121, 127]


def test_order_dates_are_parsed(store):
    assert pd.api.types.is_datetime64_any_dtype(store.orders["order_date"])
    assert pd.api.types.is_datetime64_any_dtype(store.orders["estimated_delivery"])


def test_orders_without_tracking_have_missing_code(store):
    orders = store.orders.set_index("order_id")
    assert orders.loc[1, "tracking_code"] == "BRAB1234567BR"
    assert pd.isna(orders.loc[13, "tracking_code"])  # pending order


def test_customer_contact_fields_are_normalized(store):
    lucas = store.customers.set_index("customer_id").loc[1]
    assert lucas["email_norm"] == "lucas.mendes@jmail.com"
    assert lucas["phone_digits"] == "67998123456"
