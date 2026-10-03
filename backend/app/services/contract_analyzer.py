from app.ai.client import AIClient
from app.ai.schemas import ContractAnalysis
import logging

logger = logging.getLogger(__name__)


class ContractAnalyzer:
    """Orchestrate contract analysis workflow."""

    def __init__(self):
        self.ai_client = AIClient()

    async def analyze(self, contract_text: str) -> ContractAnalysis:
        """
        Analyze contract text using AI.
        """
        logger.info("Starting contract analysis")
        analysis = await self.ai_client.analyze_contract(contract_text)
        logger.info("Contract analysis completed")
        return analysis
