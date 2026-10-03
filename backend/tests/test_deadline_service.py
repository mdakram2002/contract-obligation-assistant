import asyncio
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deadlines import calculate_deadlines
from app.database import Base
from app.models.contract import Contract
from app.models.contract_version import ContractVersion
from app.models.extracted_item import ExtractedItem, ItemType, ReviewStatus
from app.models.obligation import Obligation
from app.schemas.deadlines import DeadlineCalculationRequest
from app.services.deadline_service import DeadlineService


TABLES = [
    Base.metadata.tables[table_name]
    for table_name in (
        "contracts",
        "contract_versions",
        "extracted_items",
        "obligations",
    )
]


async def with_database(test):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all, tables=TABLES)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await test(session)
    await engine.dispose()


async def make_version(db, name="Deadline contract"):
    contract = Contract(name=name, status="draft")
    db.add(contract)
    await db.flush()
    version = ContractVersion(
        contract_id=contract.id,
        version_number=1,
        file_name="sample_contract_deadlines_test.pdf",
        file_type="pdf",
        raw_text="Contract test content",
    )
    db.add(version)
    await db.flush()
    return contract, version


def test_expiry_and_sixty_day_renewal_appear_in_selected_window():
    async def test(db):
        contract, version = await make_version(db)
        db.add_all(
            [
                ExtractedItem(
                    contract_version_id=version.id,
                    item_type=ItemType.EXPIRY,
                    title="Expiry Clause",
                    value="31 March 2027",
                    description="Initial term ending on 31 March 2027",
                    date_value=None,
                    review_status=ReviewStatus.PENDING,
                    source_quote="term ending on 31 March 2027",
                ),
                ExtractedItem(
                    contract_version_id=version.id,
                    item_type=ItemType.RENEWAL,
                    title="Renewal Term",
                    description="Renewal discussion at least 60 days before expiry",
                    notice_period_days=60,
                    review_status=ReviewStatus.PENDING,
                ),
                ExtractedItem(
                    contract_version_id=version.id,
                    item_type=ItemType.NOTICE,
                    title="Notice Term",
                    description="Non-renewal notice",
                    notice_period_days=60,
                    purpose="non-renewal",
                    review_status=ReviewStatus.PENDING,
                ),
                Obligation(
                    contract_version_id=version.id,
                    description="Provide monthly report",
                    deadline_description="5 business days after month-end",
                    deadline=None,
                    review_status=ReviewStatus.PENDING,
                ),
                Obligation(
                    contract_version_id=version.id,
                    description="Notify outage",
                    deadline_description="24 hours after becoming aware of outage",
                    deadline=None,
                    review_status=ReviewStatus.PENDING,
                ),
                Obligation(
                    contract_version_id=version.id,
                    description="Pay invoice",
                    deadline_description="30 calendar days after invoice receipt",
                    deadline=None,
                    review_status=ReviewStatus.PENDING,
                ),
            ]
        )
        await db.commit()

        request = DeadlineCalculationRequest(
            contract_id=str(contract.id),
            contract_version_id=str(version.id),
        )
        short_window = await DeadlineService.calculate_for_version(
            contract_version_id=version.id,
            contract_id=contract.id,
            days_ahead=30,
            db=db,
            today=date(2026, 10, 3),
        )
        assert short_window.total == 0

        medium_window = await DeadlineService.calculate_for_version(
            contract_version_id=version.id,
            contract_id=contract.id,
            days_ahead=120,
            db=db,
            today=date(2026, 10, 3),
        )
        assert [
            (item.type, item.deadline) for item in medium_window.deadlines
        ] == [("renewal", date(2027, 1, 30))]
        assert medium_window.deadlines[0].description == (
            "Renewal discussion deadline (60 days before expiry)"
        )

        result = await DeadlineService.calculate_for_version(
            contract_version_id=version.id,
            contract_id=contract.id,
            days_ahead=365,
            db=db,
            today=date(2026, 10, 3),
        )
        assert result.total == 2
        assert {
            item.timing_kind for item in result.undated_obligations
        } == {"recurring", "trigger_dependent"}
        assert {
            item.timing_description for item in result.undated_obligations
        } == {
            "5 business days after month-end",
            "24 hours after becoming aware of outage",
            "30 calendar days after invoice receipt",
        }
        assert all(
            item.review_status == ReviewStatus.PENDING.value
            for item in result.undated_obligations
        )
        assert all(item.type != "obligation" for item in result.deadlines)
        assert all(
            item.review_status == ReviewStatus.PENDING.value
            for item in result.deadlines
        )
        actual = {(item.type, item.deadline) for item in result.deadlines}
        assert actual == {
            ("expiry", date(2027, 3, 31)),
            ("renewal", date(2027, 1, 30)),
        }
        assert all(item.days_remaining > 0 for item in result.deadlines)
        api_result = await calculate_deadlines(request, 365, db)
        assert api_result.total == 2
        assert {item.deadline for item in api_result.deadlines} == {
            date(2027, 1, 30),
            date(2027, 3, 31),
        }

    asyncio.run(with_database(test))


def test_recurring_obligations_are_shown_without_fabricated_dates():
    async def test(db):
        contract, version = await make_version(db)
        obligation = Obligation(
            contract_version_id=version.id,
            description="Send status reports",
            deadline_description="By the fifth business day of each month",
            deadline=None,
            review_status=ReviewStatus.PENDING,
        )
        db.add(obligation)
        await db.commit()

        result = await DeadlineService.calculate_for_version(
            contract_version_id=version.id,
            contract_id=contract.id,
            days_ahead=180,
            db=db,
            today=date(2026, 10, 3),
        )

        assert result.deadlines == []
        assert result.total == 0
        assert len(result.undated_obligations) == 1
        assert result.undated_obligations[0].timing_kind == "recurring"
        assert result.undated_obligations[0].timing_description == (
            "By the fifth business day of each month"
        )

    asyncio.run(with_database(test))


def test_conflicting_expiry_dates_keep_renewal_candidates_uncertain():
    async def test(db):
        contract, version = await make_version(db)
        for expiry_date in (date(2027, 10, 14), date(2027, 10, 15)):
            db.add(
                ExtractedItem(
                    contract_version_id=version.id,
                    item_type=ItemType.EXPIRY,
                    title="Expiry Clause",
                    value=expiry_date.isoformat(),
                    date_value=datetime.combine(expiry_date, datetime.min.time()),
                    description=f"Expiry on {expiry_date.isoformat()}",
                    review_status=ReviewStatus.PENDING,
                    source_quote=f"Agreement expires on {expiry_date.isoformat()}",
                )
            )
        db.add(
            ExtractedItem(
                contract_version_id=version.id,
                item_type=ItemType.RENEWAL,
                title="Renewal Term",
                description="Automatic renewal unless notice is given",
                notice_period_days=60,
                review_status=ReviewStatus.PENDING,
                source_quote="Give notice 60 days before expiry",
            )
        )
        await db.commit()

        result = await DeadlineService.calculate_for_version(
            contract_version_id=version.id,
            contract_id=contract.id,
            days_ahead=365,
            db=db,
            today=date(2027, 6, 1),
        )

        renewal_dates = {
            item.deadline: item
            for item in result.deadlines
            if item.type == "renewal"
        }
        assert set(renewal_dates) == {date(2027, 8, 15), date(2027, 8, 16)}
        assert all(item.certainty == "low" for item in renewal_dates.values())
        assert all(
            item.review_status == ReviewStatus.PENDING.value
            for item in renewal_dates.values()
        )
        assert all(
            item.description.startswith("Uncertain renewal notice deadline")
            for item in renewal_dates.values()
        )
        expiry_items = [item for item in result.deadlines if item.type == "expiry"]
        assert len(expiry_items) == 2
        assert all(item.certainty == "low" for item in expiry_items)

    asyncio.run(with_database(test))


def test_selected_contract_version_is_enforced():
    async def test(db):
        first_contract, first_version = await make_version(db, "First")
        second_contract, second_version = await make_version(db, "Second")
        db.add(
            ExtractedItem(
                contract_version_id=second_version.id,
                item_type=ItemType.EXPIRY,
                title="Expiry Clause",
                value="2027-03-31",
                date_value=datetime(2027, 3, 31),
                review_status=ReviewStatus.PENDING,
            )
        )
        await db.commit()

        wrong_contract_request = DeadlineCalculationRequest(
            contract_id=str(first_contract.id),
            contract_version_id=str(second_version.id),
        )
        try:
            await calculate_deadlines(wrong_contract_request, 365, db)
        except HTTPException as error:
            assert error.status_code == 404
        else:
            raise AssertionError("Mismatched contract/version should be rejected")

        correct_request = DeadlineCalculationRequest(
            contract_id=str(second_contract.id),
            contract_version_id=str(second_version.id),
        )
        result = await calculate_deadlines(correct_request, 365, db)
        assert result.total == 1
        assert result.deadlines[0].deadline == date(2027, 3, 31)
        assert first_version.id != second_version.id

    asyncio.run(with_database(test))


def test_parse_text_month_date_to_real_date():
    from app.services.analysis_service import parse_date_string
    from app.services.date_calculator import DateCalculator

    assert parse_date_string("31 March 2027") == date(2027, 3, 31)
    assert parse_date_string("Expiry: 31 March 2027") == date(2027, 3, 31)
    assert DateCalculator.parse_date_string(
        "within 30 calendar days of receipt"
    ) is None
    assert DateCalculator.parse_date_string(
        "within 5 business days after month-end"
    ) is None
