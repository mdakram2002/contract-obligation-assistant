import uuid
from app.models.extracted_item import ItemType
from app.services.analysis_service import (
    normalize_text,
    get_item_dedup_key
)


def test_normalize_text():
    """Test text normalization for deduplication."""
    assert normalize_text("  hello  world  ") == "hello world"
    assert normalize_text("hello    world") == "hello world"
    assert normalize_text("") == ""
    assert normalize_text(None) == ""
    assert normalize_text("Hello World") == "Hello World"


def test_get_item_dedup_key():
    """Test deduplication key generation."""
    contract_version_id = uuid.uuid4()
    key1 = get_item_dedup_key(
        contract_version_id,
        ItemType.EFFECTIVE_DATE,
        value="2026-04-01",
        source_section="1.1"
    )
    key2 = get_item_dedup_key(
        contract_version_id,
        ItemType.EFFECTIVE_DATE,
        value="2026-04-01",
        source_section="1.1"
    )
    key3 = get_item_dedup_key(
        contract_version_id,
        ItemType.EFFECTIVE_DATE,
        value="2026-04-02",
        source_section="1.1"
    )

    assert key1 == key2
    assert key1 != key3


def test_get_item_dedup_key_with_whitespace():
    """Test that deduplication key normalizes whitespace."""
    contract_version_id = uuid.uuid4()
    key1 = get_item_dedup_key(
        contract_version_id,
        ItemType.RENEWAL,
        description="Renewal by mutual agreement",
        source_section="3.1"
    )
    key2 = get_item_dedup_key(
        contract_version_id,
        ItemType.RENEWAL,
        description="  Renewal   by   mutual  agreement  ",
        source_section="3.1"
    )
    assert key1 == key2


def test_get_item_dedup_key_ignores_source_section_formatting():
    """Section labels identify evidence location, not a distinct extracted fact."""
    contract_version_id = uuid.uuid4()
    key1 = get_item_dedup_key(
        contract_version_id,
        ItemType.TERMINATION,
        description="30 day notice",
        source_section="4.1"
    )
    key2 = get_item_dedup_key(
        contract_version_id,
        ItemType.TERMINATION,
        description="30 day notice",
        source_section="4.2"
    )
    assert key1 == key2
