import asyncio
import uuid
from types import SimpleNamespace

from app.models.obligation import Obligation
from app.models.extracted_item import ReviewStatus
from app.services.obligation_detection import ObligationDetectionService


CONTRACT_TEXT = """\
5.2 Critical Service Outage
If a security incident is confirmed, the responsible party must notify the other party within 24 hours of
confirmation.
6.3 Invoice Payment
The Client shall pay each undisputed invoice within 30 calendar days after receipt.
9. SLA CREDIT
If monthly service availability falls below 99.5%, the Service Provider shall issue the applicable service
credit within 15 business days after the monthly SLA report is finalized.
11. RESPONSIBLE PARTY AMBIGUITY
The responsible business owner shall review material changes within 5 business days.
12. DATA RETENTION DEADLINE
The seven-year service-record retention period begins after termination or expiry, whichever occurs later.
"""


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self):
        self.obligations = []

    async def execute(self, statement):
        return FakeResult(self.obligations)

    async def flush(self):
        return None

    def add(self, obligation):
        self.obligations.append(obligation)


def test_persists_omitted_trigger_obligations_without_dates_idempotently():
    version = SimpleNamespace(id=uuid.uuid4(), raw_text=CONTRACT_TEXT)
    db = FakeSession()

    first = asyncio.run(ObligationDetectionService.ensure_for_version(version, db))
    second = asyncio.run(ObligationDetectionService.ensure_for_version(version, db))

    assert first == 5
    assert second == 0
    assert len(db.obligations) == 5
    assert all(item.deadline is None for item in db.obligations)
    assert all(item.review_status == ReviewStatus.PENDING for item in db.obligations)
    assert all(item.source_quote for item in db.obligations)
    assert {
        item.responsible_party for item in db.obligations
    } == {None, "Client", "Service Provider"}
    assert any(
        item.deadline_description == "within 30 calendar days after receipt"
        for item in db.obligations
    )
    assert any(
        item.deadline_description
        and "within 24 hours" in item.deadline_description
        for item in db.obligations
    )
