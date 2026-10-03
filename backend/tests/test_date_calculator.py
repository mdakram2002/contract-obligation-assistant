import pytest
from datetime import date, timedelta
from app.services.date_calculator import DateCalculator


class TestDateCalculator:
    """Tests for deterministic date calculations."""

    def test_calculate_notice_deadline(self):
        """Test notice deadline calculation."""
        expiry_date = date(2028, 12, 31)
        notice_period_days = 90

        deadline = DateCalculator.calculate_notice_deadline(expiry_date, notice_period_days)

        expected_deadline = date(2028, 10, 2)
        assert deadline == expected_deadline

    def test_calculate_notice_deadline_30_days(self):
        """Test notice deadline calculation with 30 days."""
        expiry_date = date(2028, 12, 31)
        notice_period_days = 30

        deadline = DateCalculator.calculate_notice_deadline(expiry_date, notice_period_days)

        expected_deadline = date(2028, 12, 1)
        assert deadline == expected_deadline

    def test_calculate_notice_deadline_missing_expiry(self):
        """Test notice deadline calculation with missing expiry date."""
        with pytest.raises(ValueError, match="Both expiry_date and notice_period_days are required"):
            DateCalculator.calculate_notice_deadline(None, 90)

    def test_calculate_notice_deadline_missing_period(self):
        """Test notice deadline calculation with missing notice period."""
        expiry_date = date(2028, 12, 31)
        with pytest.raises(ValueError, match="Both expiry_date and notice_period_days are required"):
            DateCalculator.calculate_notice_deadline(expiry_date, None)

    def test_calculate_renewal_deadline(self):
        """Test renewal deadline calculation."""
        expiry_date = date(2028, 12, 31)
        renewal_notice_period = 120

        deadline = DateCalculator.calculate_renewal_deadline(expiry_date, renewal_notice_period)

        expected_deadline = date(2028, 9, 2)
        assert deadline == expected_deadline

    def test_days_until_deadline_future(self):
        """Test days until deadline for future date."""
        # Use a date far in the future
        future_date = date.today() + timedelta(days=100)
        days_remaining = DateCalculator.days_until_deadline(future_date)

        assert days_remaining == 100

    def test_days_until_deadline_past(self):
        """Test days until deadline for past date."""
        past_date = date.today() - timedelta(days=10)
        days_remaining = DateCalculator.days_until_deadline(past_date)

        assert days_remaining == -10

    def test_days_until_deadline_today(self):
        """Test days until deadline for today."""
        today = date.today()
        days_remaining = DateCalculator.days_until_deadline(today)

        assert days_remaining == 0

    def test_parse_date_string_standard(self):
        """Test parsing standard date string."""
        date_str = "2028-12-31"
        parsed_date = DateCalculator.parse_date_string(date_str)

        assert parsed_date == date(2028, 12, 31)

    def test_parse_date_string_slashes(self):
        """Test parsing date string with slashes."""
        date_str = "12/31/2028"
        parsed_date = DateCalculator.parse_date_string(date_str)

        assert parsed_date == date(2028, 12, 31)

    def test_parse_date_string_month_name(self):
        """Test parsing date string with month name."""
        date_str = "December 31, 2028"
        parsed_date = DateCalculator.parse_date_string(date_str)

        assert parsed_date == date(2028, 12, 31)

    def test_parse_date_string_invalid(self):
        """Test parsing invalid date string returns None."""
        date_str = "invalid date"
        parsed_date = DateCalculator.parse_date_string(date_str)
        assert parsed_date is None

    def test_parse_date_string_none(self):
        """Test parsing None date string returns None."""
        parsed_date = DateCalculator.parse_date_string(None)
        assert parsed_date is None

    def test_parse_date_string_empty(self):
        """Test parsing empty date string returns None."""
        parsed_date = DateCalculator.parse_date_string("")
        assert parsed_date is None

    def test_get_upcoming_deadlines(self):
        """Test getting upcoming deadlines."""
        today = date.today()
        deadlines = [
            ("Deadline 1", today + timedelta(days=30)),
            ("Deadline 2", today + timedelta(days=100)),
            ("Deadline 3", today + timedelta(days=60)),
            ("Deadline 4", today - timedelta(days=10)),  # Past deadline
        ]

        upcoming = DateCalculator.get_upcoming_deadlines(deadlines, days_ahead=90)

        assert len(upcoming) == 2
        assert upcoming[0][0] == "Deadline 1"
        assert upcoming[1][0] == "Deadline 3"

    def test_get_upcoming_deadlines_empty(self):
        """Test getting upcoming deadlines with empty list."""
        upcoming = DateCalculator.get_upcoming_deadlines([], days_ahead=90)
        assert len(upcoming) == 0

    def test_calculate_termination_deadline(self):
        """Test termination deadline calculation."""
        effective_date = date(2026, 1, 1)
        notice_period_days = 30

        deadline = DateCalculator.calculate_termination_deadline(effective_date, notice_period_days)

        expected_deadline = date(2026, 1, 31)
        assert deadline == expected_deadline

    def test_calculate_termination_deadline_missing_effective(self):
        """Test termination deadline calculation with missing effective date."""
        with pytest.raises(ValueError, match="Both effective_date and notice_period_days are required"):
            DateCalculator.calculate_termination_deadline(None, 30)

    def test_calculate_termination_deadline_missing_period(self):
        """Test termination deadline calculation with missing notice period."""
        effective_date = date(2026, 1, 1)
        with pytest.raises(ValueError, match="Both effective_date and notice_period_days are required"):
            DateCalculator.calculate_termination_deadline(effective_date, None)

