from openai import AsyncOpenAI
from app.config import settings
from app.ai.schemas import ContractAnalysis
import json
import logging

logger = logging.getLogger(__name__)


class AIClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_BASE_URL
        )
        self.model = settings.GROQ_MODEL

    async def analyze_contract(self, contract_text: str) -> ContractAnalysis:
        """
        Analyze contract text using LLM and return structured output.
        """
        from app.ai.prompts import get_analysis_prompt

        prompt = get_analysis_prompt(contract_text)

        try:
            logger.info(f"Starting AI analysis with model: {self.model}")

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a contract analysis assistant. Extract structured information from contracts. Always provide source evidence for every extracted item. Mark uncertain information appropriately. Never invent information that is not in the contract."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            content = response.choices[0].message.content
            logger.info("AI analysis completed successfully")

            # Parse and validate
            data = json.loads(content)
            analysis = ContractAnalysis(**data)

            return analysis

        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            raise
