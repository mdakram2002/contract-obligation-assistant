def get_analysis_prompt(contract_text: str) -> str:
    """
    Generate the prompt for contract analysis.
    """
    return f"""Analyze the following contract and extract structured information.

IMPORTANT RULES:
1. Extract ONLY information that is clearly stated in the contract.
2. If information is unclear, conflicting, or ambiguous, mark it with low certainty and explain why.
3. For EVERY extracted item, provide the exact source section and quote.
4. Use page numbers if available (from the text structure), otherwise use null.
5. Never invent or guess information.
6. If a field cannot be determined from the contract, set it to null or empty and note the uncertainty.
7. Distinguish between explicitly stated terms and inferred terms.

CONTRACT TEXT:
{contract_text}

Return a JSON object with this exact structure:
{{
  "parties": [
    {{
      "name": "exact party name",
      "role": "e.g., 'Supplier', 'Customer', 'Licensor' if specified",
      "source": {{
        "section": "section number or heading",
        "page": page_number_or_null,
        "quote": "exact quote from contract"
      }}
    }}
  ],
  "effective_date": {{
    "date": "YYYY-MM-DD or null if unclear",
    "certainty": "high|medium|low",
    "source": {{
      "section": "section number or heading",
      "page": page_number_or_null,
      "quote": "exact quote"
    }},
    "notes": "explanation if uncertain"
  }},
  "expiry_clauses": [
    {{
      "date": "YYYY-MM-DD or null",
      "description": "description of expiry terms",
      "certainty": "high|medium|low",
      "source": {{
        "section": "section number",
        "page": page_number_or_null,
        "quote": "exact quote"
      }},
      "notes": "any ambiguity explanation"
    }}
  ],
  "renewal_terms": [
    {{
      "description": "renewal terms description",
      "notice_period_days": number_or_null,
      "automatic": true_or_false_or_null,
      "certainty": "high|medium|low",
      "source": {{
        "section": "section number",
        "page": page_number_or_null,
        "quote": "exact quote"
      }},
      "notes": "ambiguity explanation"
    }}
  ],
  "termination_terms": [
    {{
      "description": "termination terms description",
      "notice_period_days": number_or_null,
      "conditions": "conditions for termination or null",
      "certainty": "high|medium|low",
      "source": {{
        "section": "section number",
        "page": page_number_or_null,
        "quote": "exact quote"
      }},
      "notes": "ambiguity explanation"
    }}
  ],
  "notice_terms": [
    {{
      "description": "notice term description",
      "notice_period_days": number_or_null,
      "purpose": "e.g., 'renewal', 'termination' or null",
      "certainty": "high|medium|low",
      "source": {{
        "section": "section number",
        "page": page_number_or_null,
        "quote": "exact quote"
      }},
      "notes": "ambiguity explanation"
    }}
  ],
  "obligations": [
    {{
      "description": "obligation description",
      "responsible_party": "party name or null",
      "deadline": "YYYY-MM-DD or null",
      "deadline_description": "deadline description if not a specific date or null",
      "certainty": "high|medium|low",
      "source": {{
        "section": "section number",
        "page": page_number_or_null,
        "quote": "exact quote"
      }},
      "notes": "ambiguity explanation"
    }}
  ],
  "ambiguities": [
    {{
      "description": "description of ambiguity or conflict",
      "conflicting_clauses": ["list of conflicting clause references"],
      "certainty": "high|medium|low",
      "source": [
        {{
          "section": "section number",
          "page": page_number_or_null,
          "quote": "exact quote"
        }}
      ],
      "notes": "explanation"
    }}
  ],
  "clarification_questions": [
    {{
      "question": "specific question to clarify ambiguity",
      "related_clauses": ["clause references"],
      "context": "context for the question",
      "source": [
        {{
          "section": "section number",
          "page": page_number_or_null,
          "quote": "exact quote"
        }}
      ]
    }}
  ]
}}
"""
