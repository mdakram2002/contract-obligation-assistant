from datetime import date, timedelta
from typing import Optional, Tuple
from dateutil import parser
import re
import logging

logger = logging.getLogger(__name__)


class DateCalculator:
    """Deterministic date calculations for reminders and deadlines."""

    @staticmethod
    def calculate_notice_deadline(
        expiry_date: date,
        notice_period_days: int
    ) -> date:
        """
        Calculate the deadline for providing notice before expiry.
        deadline = expiry_date - notice_period_days
        """
        if not expiry_date or not notice_period_days:
            raise ValueError("Both expiry_date and notice_period_days are required")

        deadline = expiry_date - timedelta(days=notice_period_days)
        logger.info(f"Notice deadline calculated: {deadline} (expiry: {expiry_date}, notice: {notice_period_days} days)")
        return deadline

    @staticmethod
    def calculate_renewal_deadline(
        expiry_date: date,
        notice_period_days: int
    ) -> date:
        """
        Calculate the deadline for renewal notice.
        This is typically the same as notice deadline.
        """
        return DateCalculator.calculate_notice_deadline(expiry_date, notice_period_days)

    @staticmethod
    def parse_date_string(date_str: str) -> Optional[date]:
        """
        Parse an explicit calendar date embedded in a date string.
        Relative periods are not dates and must not be resolved against today.
        """
        if not date_str:
            return None

        month = (
            r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
            r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
            r"Nov(?:ember)?|Dec(?:ember)?)"
        )
        patterns = (
            r"(?<!\d)\d{4}-\d{1,2}-\d{1,2}(?!\d)",
            r"(?<!\d)\d{1,2}[/-]\d{1,2}[/-]\d{4}(?!\d)",
            rf"(?<!\w)\d{{1,2}}(?:st|nd|rd|th)?\s+{month}\s*,?\s+\d{{4}}(?!\d)",
            rf"(?<!\w){month}\s+\d{{1,2}}(?:st|nd|rd|th)?[,]?\s+\d{{4}}(?!\d)",
        )
        for pattern in patterns:
            match = re.search(pattern, date_str, flags=re.IGNORECASE)
            if not match:
                continue
            try:
                return parser.parse(match.group(), fuzzy=False).date()
            except (ValueError, OverflowError) as error:
                logger.warning("Failed to parse explicit date '%s': %s", match.group(), error)
                return None
        return None

    @staticmethod
    def days_until_deadline(deadline: date) -> int:
        """
        Calculate days remaining until a deadline.
        Returns negative number if deadline has passed.
        """
        today = date.today()
        delta = deadline - today
        return delta.days

    @staticmethod
    def get_upcoming_deadlines(
        deadlines: list[Tuple[str, date]],
        days_ahead: int = 90
    ) -> list[Tuple[str, date, int]]:
        """
        Get deadlines within the next N days.
        Returns list of (description, deadline, days_remaining).
        """
        today = date.today()
        upcoming = []

        for description, deadline in deadlines:
            if deadline:
                days_remaining = DateCalculator.days_until_deadline(deadline)
                if 0 <= days_remaining <= days_ahead:
                    upcoming.append((description, deadline, days_remaining))

        # Sort by days remaining
        upcoming.sort(key=lambda x: x[2])
        return upcoming

    @staticmethod
    def calculate_termination_deadline(
        effective_date: date,
        notice_period_days: int
    ) -> date:
        """
        Calculate the earliest termination deadline from effective date.
        deadline = effective_date + notice_period_days
        """
        if not effective_date or not notice_period_days:
            raise ValueError("Both effective_date and notice_period_days are required")

        deadline = effective_date + timedelta(days=notice_period_days)
        logger.info(f"Termination deadline calculated: {deadline} (effective: {effective_date}, notice: {notice_period_days} days)")
        return deadline
