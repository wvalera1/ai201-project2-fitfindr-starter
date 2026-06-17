# tests/test_tools.py
from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    # failure mode: no listings match → empty list, no exception
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

def test_search_size_filter():
    results = search_listings("jeans", size="M", max_price=None)
    assert all("m" in item["size"].lower() for item in results)

def test_search_sorted_by_relevance():
    # a more specific query should rank the closest match first
    results = search_listings("vintage denim jeans", max_price=None)
    assert len(results) > 1
    # first result must contain at least one of the keywords
    first = results[0]
    searchable = " ".join([
        first["title"], first["description"], first["category"],
        " ".join(first["style_tags"])
    ]).lower()
    assert any(kw in searchable for kw in ["vintage", "denim", "jeans"])

def test_search_returns_listing_fields():
    results = search_listings("jacket", max_price=None)
    assert len(results) > 0
    required_fields = {"id", "title", "description", "category", "style_tags",
                       "size", "condition", "price", "colors", "brand", "platform"}
    assert required_fields.issubset(results[0].keys())


# ── suggest_outfit ────────────────────────────────────────────────────────────

def _sample_item():
    return search_listings("vintage graphic tee", max_price=30.0)[0]

def test_suggest_outfit_returns_string():
    result = suggest_outfit(_sample_item(), get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result.strip()) > 0

def test_suggest_outfit_empty_wardrobe():
    # failure mode: wardrobe is empty → general styling advice, not a crash
    result = suggest_outfit(_sample_item(), get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result.strip()) > 0

def test_suggest_outfit_references_item():
    item = _sample_item()
    result = suggest_outfit(item, get_example_wardrobe())
    # LLM should mention something about the item — at minimum it shouldn't be blank
    assert len(result) > 50


# ── create_fit_card ───────────────────────────────────────────────────────────

def test_create_fit_card_returns_string():
    item = _sample_item()
    outfit = suggest_outfit(item, get_example_wardrobe())
    result = create_fit_card(outfit, item)
    assert isinstance(result, str)
    assert len(result.strip()) > 0

def test_create_fit_card_empty_outfit():
    # failure mode: empty outfit string → error message string, no exception
    item = _sample_item()
    result = create_fit_card("", item)
    assert isinstance(result, str)
    assert "outfit" in result.lower() or "error" in result.lower() or "missing" in result.lower()

def test_create_fit_card_whitespace_outfit():
    # failure mode: whitespace-only outfit string → same guard as empty
    item = _sample_item()
    result = create_fit_card("   ", item)
    assert isinstance(result, str)
    assert "outfit" in result.lower() or "error" in result.lower() or "missing" in result.lower()

def test_create_fit_card_mentions_price_and_platform():
    item = _sample_item()
    outfit = suggest_outfit(item, get_example_wardrobe())
    result = create_fit_card(outfit, item)
    assert str(item["price"]) in result or str(int(item["price"])) in result
    assert item["platform"].lower() in result.lower()
