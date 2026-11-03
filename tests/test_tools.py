from datetime import datetime

import pytest

from emporio_agent.config import STORE_TZ
from emporio_agent.tools import (
    TOOL_FUNCTIONS,
    TOOL_SCHEMAS,
    _stem,
    get_order_status,
    get_product_details,
    get_store_status,
    list_active_promotions,
    run_tool,
    search_policies,
    search_products,
)


def at(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=STORE_TZ)


# --- search_products --------------------------------------------------------


def test_stem_matches_singular_and_plural():
    assert _stem("violoes") == _stem("violao") == "violao"
    assert _stem("guitarras") == "guitarra"


def test_guitars_up_to_1000_are_available_and_sorted():
    result = search_products(category="Violões", max_price=1000)
    prices = [p["list_price_brl"] for p in result["products"]]
    assert result["total_found"] > 0
    assert prices == sorted(prices)
    assert all(p <= 1000 for p in prices)
    assert all(p["availability"] == "available" for p in result["products"])


def test_search_by_model_name():
    result = search_products(query="Takamine GD20")
    assert [p["product_id"] for p in result["products"]] == [95]
    assert result["products"][0]["list_price_brl"] == 2199.0


def test_query_without_accents_finds_accented_products():
    assert search_products(query="violao nylon", max_price=500)["total_found"] == 2


def test_out_of_stock_product_is_hidden_by_default_but_reported_when_asked():
    assert search_products(query="Giannini GF-3D")["total_found"] == 0
    result = search_products(query="Giannini GF-3D", only_available=False)
    assert result["products"][0]["availability"] == "out_of_stock"


def test_discontinued_and_coming_soon_are_labelled():
    assert get_product_details(136)["availability"] == "discontinued"  # has stock, but discontinued
    assert get_product_details(130)["availability"] == "coming_soon"


def test_limit_caps_results_but_total_is_kept():
    result = search_products(category="Violões", limit=3)
    assert len(result["products"]) == 3
    assert result["total_found"] > 3


def test_default_limit_shows_15_and_notes_the_total():
    result = search_products(category="Violões")
    assert len(result["products"]) == 15
    assert result["total_found"] > 15
    assert str(result["total_found"]) in result["note"]


def test_no_note_when_everything_is_shown():
    result = search_products(category="Violões", max_price=1000)
    assert len(result["products"]) == result["total_found"] == 12
    assert "note" not in result


@pytest.mark.parametrize(
    "category", ["Instrumentos de Sopro (Madeiras)", "Instrumentos de Sopro (Metais)", "Cordas Orquestrais"]
)
def test_empty_categories_say_so_explicitly(category):
    result = search_products(category=category)
    assert result["total_found"] == 0
    assert "não tem nenhum produto" in result["note"]


def test_contradicting_descriptions_do_not_affect_search():
    # Product 135 is a "Music Man Bass 1X" whose description calls it a Fender Jazz Bass.
    fender = {p["product_id"] for p in search_products(query="Fender", only_available=False)["products"]}
    assert 135 not in fender
    assert {134, 145} <= fender  # the real Fender guitars are still found by name
    music_man = {p["product_id"] for p in search_products(query="Music Man", only_available=False)["products"]}
    assert 135 in music_man


def test_feature_words_come_from_specs():
    with_pickup = search_products(query="captação", only_available=False)["products"]
    assert with_pickup and all(get_product_details(p["product_id"])["specs"]["electronics"] == "yes" for p in with_pickup)
    assert search_products(query="eletroacústico", only_available=False)["total_found"] > 0


def test_product_details_warn_that_descriptions_can_be_wrong():
    details = get_product_details(135)
    assert "Fender" in details["description"]  # raw data is kept as is
    assert "confie no nome e nas specs" in details["note"]


def test_unknown_product_returns_nothing():
    assert search_products(query="trompete dourado")["total_found"] == 0


# --- prices and promotions --------------------------------------------------


def test_pix_discount_applies_without_promotion():
    product = get_product_details(95)
    assert "promotion" not in product
    assert product["pix_price_brl"] == 2089.05


def test_pix_price_is_rounded_exactly_to_the_cent():
    # 429.90 * 0.95 = 408.405 -> 408.41 (float round() would give 408.40)
    assert get_product_details(83)["pix_price_brl"] == 408.41


def test_promotion_shows_original_price_discount_and_no_pix_stacking():
    product = get_product_details(90)
    assert product["list_price_brl"] == 2399.0
    assert product["promotion"]["discount_percent"] == 18
    assert product["promotion"]["promotional_price_brl"] == 1967.18
    assert product["pix_price_brl"] is None


def test_inactive_promotions_are_ignored():
    assert "promotion" not in get_product_details(102)  # only has an inactive Black Friday promo


def test_list_active_promotions():
    ids = [p["product_id"] for p in list_active_promotions()["active_promotions"]]
    assert ids == [90, 94, 121, 127]


def test_product_details_include_specs():
    details = get_product_details(81)
    assert details["specs"]["strings"] == "nylon"
    assert "description" in details


def test_missing_product_details():
    assert "error" in get_product_details(9999)


# --- orders -----------------------------------------------------------------


def test_order_requires_matching_email():
    order = get_order_status(4, "Lucas.Mendes@jmail.com ", now=at(2025, 12, 25, 10))
    assert order["status"] == "delivered"
    assert order["items"] == [{"product": "Giannini GF-3D Dreadnought Sunburst", "quantity": 1}]
    assert order["days_since_estimated_delivery"] == 3


def test_order_accepts_phone_in_any_format():
    assert get_order_status(4, "67 99812 3456")["order_id"] == 4


def test_wrong_contact_and_missing_order_give_the_same_error():
    wrong_contact = get_order_status(4, "someone@else.com")
    missing_order = get_order_status(999, "lucas.mendes@jmail.com")
    assert "error" in wrong_contact
    assert wrong_contact == missing_order


def test_shared_email_does_not_leak_other_customers_orders():
    # Customers 11 and 43 share bruno.martins@jmail.com; order 10 belongs to customer 11.
    assert get_order_status(10, "bruno.martins@jmail.com")["order_id"] == 10
    assert "error" in get_order_status(10, "(67) 99456-3456")  # phone of customer 43


def test_shipped_order_past_estimate_is_flagged_as_delayed():
    order = get_order_status(8, "anacarol.ferreira@coldmail.com", now=at(2026, 3, 5, 10))
    assert order["status"] == "shipped"
    assert order["delayed"] is True


def test_cancelled_order_includes_reason_and_no_tracking():
    order = get_order_status(18, "gustavo.nunes@inlook.com")
    assert order["status"] == "cancelled"
    assert order["tracking_code"] is None
    assert "fora de estoque" in order["notes"]


def test_order_total_is_the_amount_paid_not_recomputed():
    # Items add up to R$ 1,488 but the order records R$ 1,400.
    assert get_order_status(20, "thiago.barbosa@jmail.com")["total_paid_brl"] == 1400.0


# --- policies and store status ---------------------------------------------


def test_search_policies_returns_sections():
    sections = search_policies("devolução arrependimento")["sections"]
    assert sections[0]["title"].startswith("4.")
    assert "7 (sete) dias" in sections[0]["content"]


def test_search_policies_out_of_scope():
    assert search_policies("capital da França")["sections"] == []


@pytest.mark.parametrize(
    "now, is_open, next_opening",
    [
        (at(2026, 11, 3, 10), True, None),  # Tuesday morning
        (at(2026, 11, 3, 18, 30), False, "quarta-feira 2026-11-04 às 09:00"),  # after closing
        (at(2026, 11, 7, 12, 59), True, None),  # Saturday before 13:00
        (at(2026, 11, 7, 14), False, "segunda-feira 2026-11-09 às 09:00"),  # Saturday afternoon
        (at(2026, 11, 8, 10), False, "segunda-feira 2026-11-09 às 09:00"),  # Sunday
        (at(2026, 11, 9, 7), False, "segunda-feira 2026-11-09 às 09:00"),  # Monday before opening
    ],
)
def test_store_status(now, is_open, next_opening):
    status = get_store_status(now)
    assert status["is_open_now"] is is_open
    assert status["next_opening"] == next_opening


# --- schemas and dispatcher -------------------------------------------------


def test_every_schema_has_a_function_and_vice_versa():
    assert {s["name"] for s in TOOL_SCHEMAS} == set(TOOL_FUNCTIONS)
    for schema in TOOL_SCHEMAS:
        assert schema["description"]
        assert schema["input_schema"]["type"] == "object"


def test_run_tool_dispatches():
    assert run_tool("search_products", {"query": "Takamine GD20"})["total_found"] == 1


def test_run_tool_reports_errors_instead_of_raising():
    assert "error" in run_tool("does_not_exist", {})
    assert "error" in run_tool("get_order_status", {"order_id": 1})
