import logging
import sys
from app.config import settings


def setup_logging():
    """Configure structured logging."""
    logging.basicConfig(
        level=logging.INFO if settings.DEBUG else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
