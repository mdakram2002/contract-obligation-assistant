from datetime import datetime
from types import SimpleNamespace
import uuid

import asyncio

from app.models.ambiguity import Ambiguity
from app.models.clarification_question import ClarificationQuestion
from app.models.extracted_item import ExtractedItem, ItemType
from app.services.clarification_detection import ClarificationDetectionService


CONTRACT_TEXT = """\
2. TERM
The Agreement expires on 14 October 2027.
The Agreement expires on 15 October 2027.
2.2 RENEWAL
The Agreement automatically renews for one year.
2.3 RENEWAL
Any renewal requires written agreement signed by both parties.
3.2 TERMINATION
Termination notice must be provided 30 days before the intended
termination date.
Termination notice must be provided 45 days before the intended
termination date.
If a security incident is confirmed, the responsible party must notify the other party within 24 hours of
confirmation.
Operational notices must be sent by email to the designated contract contacts.
Termination notices must be sent by courier to the registered office.
The Agreement does not specify whether email delivery alone is sufficient for a termination notice.
The Agreement does not contain a public holiday calendar.
9. SLA CREDIT
If monthly service availability falls below 99.5%, the Service Provider shall issue the applicable service
credit within 15 business days after the monthly SLA report is finalized.
11. RESPONSIBLE PARTY AMBIGUITY
The Agreement does not identify the responsible business owner.
The Agreement does not identify a specific person as Service Governance Manager.
The Agreement also does not define what constitutes a "material change".
8. What is the applicable SLA service-credit amount?
"""


def make_item(
    item_type: str,
    quote: str,
    section: str,
    *,
    value: str | None = None,
    day: int | None = None,
    automatic: str | None = None,
) -> ExtractedItem:
    return ExtractedItem(
        contract_version_id=uuid.uuid4(),
        item_type=item_type,
        title=item_type,
        value=value,
        date_value=(
            datetime(2027, 10, day)
            if item_type == ItemType.EXPIRY.value and day
            else None
        ),
        notice_period_days=day if item_type == ItemType.TERMINATION.value else None,
        automatic=automatic,
        source_section=section,
        source_quote=quote,
    )


def current_contract_items() -> list[ExtractedItem]:
    return [
        make_item(
            ItemType.EXPIRY.value,
            "The Agreement expires on 14 October 2027.",
            "2.1",
            value="2027-10-14",
            day=14,
        ),
        make_item(
            ItemType.EXPIRY.value,
            "The Agreement expires on 15 October 2027.",
            "14. SCHEDULE A",
            value="2027-10-15",
            day=15,
        ),
        make_item(
            ItemType.RENEWAL.value,
            "The Agreement automatically renews for one year.",
            "2.2",
            automatic="true",
        ),
        make_item(
            ItemType.RENEWAL.value,
            "Any renewal requires written agreement signed by both parties.",
            "2.3",
            automatic="false",
        ),
        make_item(
            ItemType.TERMINATION.value,
            "Termination notice must be provided 30 days before the intended termination date.",
            "3.1",
            day=30,
        ),
        make_item(
            ItemType.TERMINATION.value,
            "Termination notice must be provided 45 days before the intended termination date.",
            "3.2",
            day=45,
        ),
        make_item(
            ItemType.NOTICE.value,
            "Operational notices must be sent by email to the designated contract contacts.",
            "4.1",
        ),
        make_item(
            ItemType.NOTICE.value,
            "Termination notices must be sent by courier to the registered office.",
            "4.2",
        ),
    ]


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, items):
        self.rows = {
            ExtractedItem: items,
            Ambiguity: [],
            ClarificationQuestion: [],
        }

    async def execute(self, statement):
        model = statement.column_descriptions[0]["entity"]
        return FakeResult(self.rows[model])

    async def flush(self):
        return None

    def add(self, row):
        self.rows[type(row)].append(row)


def test_detects_current_contract_conflicts_and_missing_information():
    findings = ClarificationDetectionService.detect(
        current_contract_items(), CONTRACT_TEXT
    )

    questions = {finding.question for finding in findings}
    assert len(findings) == 10
    assert any("2027-10-14" in question and "2027-10-15" in question for question in questions)
    assert "Does the agreement renew automatically, or only by signed written agreement?" in questions
    assert "Which termination notice period applies: 30 days or 45 days?" in questions
    assert "Is email delivery sufficient for termination notices, or is courier delivery mandatory?" in questions
    assert (
        "Which party is responsible for confirmed security-incident notifications?"
    ) in questions
    assert "Who is the responsible business owner?" in questions
    assert "Who is the Service Governance Manager?" in questions
    assert "What qualifies as a material change for the review obligation?" in questions
    assert "What public holiday calendar should be used for business-day calculations?" in questions
    assert "What is the applicable SLA service-credit amount?" in questions
    assert all(finding.sources and all(source.quote for source in finding.sources) for finding in findings)


def test_persists_clarifications_idempotently():
    version = SimpleNamespace(id=uuid.uuid4(), raw_text=CONTRACT_TEXT)
    db = FakeSession(current_contract_items())

    first = asyncio.run(
        ClarificationDetectionService.ensure_for_version(version, db)
    )
    second = asyncio.run(
        ClarificationDetectionService.ensure_for_version(version, db)
    )

    assert first == {"ambiguities_created": 10, "questions_created": 10}
    assert second == {"ambiguities_created": 0, "questions_created": 0}
    assert len(db.rows[Ambiguity]) == 10
    assert len(db.rows[ClarificationQuestion]) == 10
