import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.ai_run import AIRun
from app.models.contract import Contract
from app.models.contract_extraction import ContractExtraction
from app.models.contract_version import ContractVersion
from app.models.extracted_item import ExtractedItem, ItemType, ReviewStatus
from app.models.obligation import Obligation
from app.models.party import Party
from app.models.review_action import ReviewAction
from app.ai.schemas import (
    CertaintyLevel,
    ContractAnalysis,
    EffectiveDate,
    ExpiryClause,
    Obligation as ObligationData,
    Party as PartyData,
    RenewalTerm,
    SourceEvidence,
    TerminationTerm,
    NoticeTerm,
)
from app.services.analysis_service import AnalysisService
from app.services.stale_detection import StaleDetectionService


TABLES = [
    Base.metadata.tables[table_name]
    for table_name in (
        "contracts",
        "contract_versions",
        "contract_extractions",
        "ai_runs",
        "parties",
        "extracted_items",
        "obligations",
        "review_actions",
    )
]


async def with_analysis_db(test):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all, tables=TABLES)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await test(session)
    await engine.dispose()


def evidence(section: str, quote: str) -> SourceEvidence:
    return SourceEvidence(section=section, quote=quote)


def sample_analysis() -> ContractAnalysis:
    parties = [
        PartyData(name="Acme Ltd.", role="Provider", source=evidence("1.1", "Acme Ltd.")),
        PartyData(name="Acme Ltd.", role="Provider", source=evidence("Section 1.1", "Acme Ltd.")),
        PartyData(name="Buyer Inc.", role="Customer", source=evidence("1.1", "Buyer Inc.")),
    ]
    renewals = [
        RenewalTerm(
            description=f"Renewal fact {number}",
            notice_period_days=30 + number,
            automatic=None,
            certainty=CertaintyLevel.HIGH,
            source=evidence(f"3.{number}", f"Renewal clause {number}"),
        )
        for number in range(1, 4)
    ]
    renewals.append(
        RenewalTerm(
            description="Automatic renewal occurs annually",
            notice_period_days=31,
            automatic=True,
            certainty=CertaintyLevel.MEDIUM,
            source=evidence("Section 3.1", "Renewal clause 1"),
        )
    )
    obligations = [
        ObligationData(
            description=f"Obligation {number}: deliver service output",
            responsible_party="Provider",
            certainty=CertaintyLevel.HIGH,
            source=evidence(f"5.{number}", f"Exact evidence for obligation {number}"),
        )
        for number in range(1, 8)
    ]
    obligations.append(
        ObligationData(
            description="OBLIGATION 1: deliver service output.",
            responsible_party="Provider",
            certainty=CertaintyLevel.MEDIUM,
            source=evidence("Section 5.1", "Exact evidence for obligation 1"),
        )
    )
    return ContractAnalysis(
        parties=parties,
        effective_date=EffectiveDate(
            date="2026-01-01",
            certainty=CertaintyLevel.HIGH,
            source=evidence("1.2", "Effective January 1, 2026"),
        ),
        expiry_clauses=[
            ExpiryClause(
                date="2026-12-31",
                description="Expires December 31, 2026",
                certainty=CertaintyLevel.HIGH,
                source=evidence("2.1", "Expires December 31, 2026"),
            ),
            ExpiryClause(
                date="2026-12-31",
                description="The contract ends on December 31, 2026",
                certainty=CertaintyLevel.MEDIUM,
                source=evidence("Section 2.1", "Expires December 31, 2026"),
            ),
        ],
        renewal_terms=renewals,
        termination_terms=[
            TerminationTerm(
                description="Either party may terminate on 30 days' written notice",
                notice_period_days=30,
                certainty=CertaintyLevel.HIGH,
                source=evidence("4.1", "Terminate with 30 days' written notice"),
            ),
            TerminationTerm(
                description="Either party may terminate on 30 days written notice.",
                notice_period_days=30,
                certainty=CertaintyLevel.MEDIUM,
                source=evidence("Section 4.1", "Terminate with 30 days' written notice"),
            ),
        ],
        notice_terms=[
            NoticeTerm(
                description="Provide notice at least 60 days before renewal",
                notice_period_days=60,
                purpose="non-renewal",
                certainty=CertaintyLevel.HIGH,
                source=evidence("4.2", "60 days' notice before renewal"),
            ),
            NoticeTerm(
                description="Give notice at least sixty days before renewal.",
                notice_period_days=60,
                purpose="non-renewal",
                certainty=CertaintyLevel.MEDIUM,
                source=evidence("Section 4.2", "60 days' notice before renewal"),
            ),
        ],
        obligations=obligations,
    )


async def create_contract_version(db: AsyncSession) -> ContractVersion:
    contract = Contract(name="Sample contract", status="draft")
    db.add(contract)
    await db.flush()
    version = ContractVersion(
        contract_id=contract.id,
        version_number=1,
        raw_text="Sample contract text",
    )
    db.add(version)
    await db.commit()
    return version


async def _test_repeated_loads_create_one_extraction_and_unique_items(analysis_db):
    version = await create_contract_version(analysis_db)
    service = AnalysisService()
    service.analyzer.analyze = AsyncMock(return_value=sample_analysis())

    for _ in range(3):
        await service.analyze_contract_version(version.id, analysis_db)

    assert service.analyzer.analyze.await_count == 1
    parties = (await analysis_db.execute(
        select(Party).where(Party.contract_version_id == version.id)
    )).scalars().all()
    items = (await analysis_db.execute(
        select(ExtractedItem).where(ExtractedItem.contract_version_id == version.id)
    )).scalars().all()
    obligations = (await analysis_db.execute(
        select(Obligation).where(Obligation.contract_version_id == version.id)
    )).scalars().all()
    extraction_count = (await analysis_db.execute(
        select(ContractExtraction).where(
            ContractExtraction.contract_version_id == version.id
        )
    )).scalars().all()

    assert len(parties) == 2
    assert sum(item.item_type == ItemType.EFFECTIVE_DATE for item in items) == 1
    assert sum(item.item_type == ItemType.EXPIRY for item in items) == 1
    assert sum(item.item_type == ItemType.RENEWAL for item in items) == 3
    assert sum(item.item_type == ItemType.TERMINATION for item in items) == 1
    assert sum(item.item_type == ItemType.NOTICE for item in items) == 1
    assert len(obligations) == 7
    assert len(extraction_count) == 1

    retained = next(item for item in items if item.item_type == ItemType.EFFECTIVE_DATE)
    retained.review_status = ReviewStatus.APPROVED
    retained.source_quote = "User-confirmed exact quote"
    await analysis_db.commit()
    await service.analyze_contract_version(version.id, analysis_db)
    await analysis_db.refresh(retained)
    assert retained.review_status == ReviewStatus.APPROVED
    assert retained.source_quote == "User-confirmed exact quote"
    assert service.analyzer.analyze.await_count == 1


def test_repeated_loads_create_one_extraction_and_unique_items():
    asyncio.run(with_analysis_db(_test_repeated_loads_create_one_extraction_and_unique_items))


async def _test_legacy_duplicates_are_collapsed_without_rerunning_analysis(analysis_db):
    version = await create_contract_version(analysis_db)
    duplicate_party = Party(
        contract_version_id=version.id,
        name="Acme Ltd.",
        role="Provider",
        source_section="Section 1.1",
        source_quote="Acme Ltd.",
    )
    party = Party(
        contract_version_id=version.id,
        name="ACME Ltd",
        role="Provider",
        source_section="1.1",
        source_quote="Acme Ltd.",
    )
    first_item = ExtractedItem(
        contract_version_id=version.id,
        item_type=ItemType.RENEWAL,
        title="Renewal Term",
        description="Renews annually",
        source_section="3.1",
        source_quote="Renews annually with 30 days' notice",
        review_status=ReviewStatus.PENDING,
    )
    reviewed_item = ExtractedItem(
        contract_version_id=version.id,
        item_type=ItemType.RENEWAL,
        title="Renewal Term",
        description="Renews annually",
        source_section="Section 3.1",
        source_quote="Renews annually with 30 days' notice",
        notice_period_days=30,
        review_status=ReviewStatus.APPROVED,
        user_edited="true",
    )
    first_obligation = Obligation(
        contract_version_id=version.id,
        description="Provider must send the monthly service report",
        responsible_party="Provider",
        source_section="5.1",
        source_quote="Provider sends the monthly service report",
    )
    duplicate_obligation = Obligation(
        contract_version_id=version.id,
        description="Provider must send the monthly service report",
        responsible_party="Provider",
        source_section="Section 5.1",
        source_quote="Provider sends the monthly service report",
    )
    analysis_db.add_all(
        [
            duplicate_party,
            party,
            first_item,
            reviewed_item,
            first_obligation,
            duplicate_obligation,
        ]
    )
    await analysis_db.flush()
    review_action = ReviewAction(
        action_type="approved",
        extracted_item_id=reviewed_item.id,
        created_at=datetime.utcnow(),
    )
    analysis_db.add(review_action)
    await analysis_db.commit()

    service = AnalysisService()
    service.analyzer.analyze = AsyncMock()
    await service.analyze_contract_version(version.id, analysis_db)

    parties = (await analysis_db.execute(
        select(Party).where(Party.contract_version_id == version.id)
    )).scalars().all()
    items = (await analysis_db.execute(
        select(ExtractedItem).where(ExtractedItem.contract_version_id == version.id)
    )).scalars().all()
    obligations = (await analysis_db.execute(
        select(Obligation).where(Obligation.contract_version_id == version.id)
    )).scalars().all()
    retained_action = await analysis_db.get(ReviewAction, review_action.id)

    assert len(parties) == 1
    assert len(items) == 1
    assert items[0].review_status == ReviewStatus.APPROVED
    assert items[0].user_edited == "true"
    assert items[0].source_quote == "Renews annually with 30 days' notice"
    assert len(obligations) == 1
    assert retained_action.extracted_item_id == items[0].id
    service.analyzer.analyze.assert_not_awaited()


def test_legacy_duplicates_are_collapsed_without_rerunning_analysis():
    asyncio.run(with_analysis_db(_test_legacy_duplicates_are_collapsed_without_rerunning_analysis))


async def _test_stale_detection_waits_for_new_version_analysis(db):
    first_version = await create_contract_version(db)
    original = ExtractedItem(
        contract_version_id=first_version.id,
        item_type=ItemType.EXPIRY,
        title="Expiry Clause",
        value="2027-10-14",
        date_value=datetime(2027, 10, 14),
        description="User-confirmed expiry date",
        review_status=ReviewStatus.APPROVED,
        user_edited="true",
    )
    db.add(original)
    second_version = ContractVersion(
        contract_id=first_version.contract_id,
        version_number=2,
        raw_text="Updated sample contract text",
    )
    db.add(second_version)
    await db.commit()

    upload_result = await StaleDetectionService.detect_stale_items(
        second_version.id, db
    )
    await db.refresh(original)
    assert upload_result["stale_count"] == 0
    assert original.is_stale == "false"

    service = AnalysisService()
    service.analyzer.analyze = AsyncMock(return_value=sample_analysis())
    await service.analyze_contract_version(second_version.id, db)

    await db.refresh(original)
    assert original.is_stale == "true"
    assert original.review_status == ReviewStatus.APPROVED
    assert original.user_edited == "true"
    assert original.description == "User-confirmed expiry date"


def test_stale_detection_waits_for_new_version_analysis():
    asyncio.run(with_analysis_db(_test_stale_detection_waits_for_new_version_analysis))


async def _test_extraction_marker_is_unique_per_version(db):
    version = await create_contract_version(db)
    version_id = version.id
    db.add(ContractExtraction(contract_version_id=version_id, status="completed"))
    await db.commit()

    db.add(ContractExtraction(contract_version_id=version_id, status="completed"))
    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()

    markers = (await db.execute(
        select(ContractExtraction).where(
            ContractExtraction.contract_version_id == version_id
        )
    )).scalars().all()
    assert len(markers) == 1


def test_extraction_marker_is_unique_per_version():
    asyncio.run(with_analysis_db(_test_extraction_marker_is_unique_per_version))
