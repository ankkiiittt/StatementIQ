"""Fake LLM client for fast, deterministic unit and integration tests."""
import json
from decimal import Decimal
from typing import Any

from api.services.llm.client import LLMClient
from api.services.llm.types import LLMResponse


class FakeLLMClient(LLMClient):
    """Fake LLM Client that provides pre-programmed or heuristic responses for testing."""

    def __init__(
        self,
        custom_responses: list[str] | None = None,
        fail_attempts: int = 0,
        invalid_response_text: str = "Invalid JSON {{{",
    ):
        self.custom_responses: list[str] = custom_responses or []
        self.fail_attempts = fail_attempts
        self.attempts = 0
        self.invalid_response_text = invalid_response_text
        self.call_history: list[dict[str, str]] = []

    def generate(
        self,
        prompt: str,
        prompt_version: str = "1.0",
        temperature: float = 0.0,
    ) -> LLMResponse:
        self.attempts += 1
        self.call_history.append({"prompt": prompt, "prompt_version": prompt_version})

        # Test failure/retry mechanism
        if self.attempts <= self.fail_attempts:
            return LLMResponse(
                text=self.invalid_response_text,
                input_tokens=150,
                output_tokens=20,
                latency_ms=45,
                estimated_cost=Decimal("0.0005"),
                model_name="fake-llm-failing",
                prompt_version=prompt_version,
            )

        # Custom responses queue
        if self.custom_responses:
            text = self.custom_responses.pop(0)
            return LLMResponse(
                text=text,
                input_tokens=200,
                output_tokens=150,
                latency_ms=60,
                estimated_cost=Decimal("0.0010"),
                model_name="fake-llm-custom",
                prompt_version=prompt_version,
            )

        # QuerySpec Translation handling
        if "financial query translator" in prompt.lower() or "queryspec" in prompt.lower():
            import re
            q_match = re.search(r'Question:\s*"""(.*?)"""', prompt, re.DOTALL)
            q_text = q_match.group(1).strip() if q_match else prompt.lower()
            q_lower = q_text.lower()

            # Check for refusal
            if any(w in q_lower for w in ["capital of france", "poem", "weather", "invest my money", "stock pick", "meaning of life"]):
                query_spec_dict = {
                    "is_refusal": True,
                    "refusal_reason": "I can't answer that from your data.",
                    "aggregation": "sum",
                    "direction": None,
                    "categories": None,
                    "search": None,
                    "start_date": None,
                    "end_date": None,
                    "group_by": None,
                    "top_n_limit": 10,
                    "order_by": None,
                }
            else:
                # Determine aggregation and limits
                if "top" in q_lower:
                    agg = "top_n"
                    # Check limit
                    num_match = re.search(r'top\s+(\d+)', q_lower)
                    limit = int(num_match.group(1)) if num_match else 5
                    order = "amount_desc"
                elif any(w in q_lower for w in ["how many", "count", "number of"]):
                    agg = "count"
                    limit = 10
                    order = None
                elif "average" in q_lower:
                    agg = "average"
                    limit = 10
                    order = None
                elif any(w in q_lower for w in ["list", "show all", "show me"]):
                    agg = "list"
                    limit = 20
                    order = "date_desc"
                else:
                    agg = "sum"
                    limit = 10
                    order = None

                # Determine direction
                if any(w in q_lower for w in ["income", "salary", "credit", "credited", "earned", "deposit"]):
                    direction = "credit"
                elif any(w in q_lower for w in ["spend", "spent", "expense", "expenses", "debit", "bought", "paid", "food", "groceries"]):
                    direction = "debit"
                else:
                    direction = None

                # Determine category
                cats = None
                if any(w in q_lower for w in ["food", "dining", "swiggy", "zomato", "restaurant"]):
                    cats = ["Food and Dining"]
                elif any(w in q_lower for w in ["grocer", "blinkit", "zepto", "instamart"]):
                    cats = ["Groceries"]
                elif "rent" in q_lower:
                    cats = ["Rent and Housing"]
                elif any(w in q_lower for w in ["electric", "water", "utility", "bill"]):
                    cats = ["Utilities and Bills"]
                elif any(w in q_lower for w in ["transport", "uber", "ola", "fuel", "petrol"]):
                    cats = ["Transport"]
                elif any(w in q_lower for w in ["shopping", "amazon", "flipkart"]):
                    cats = ["Shopping"]
                elif any(w in q_lower for w in ["income", "salary"]):
                    cats = ["Income"]

                # Determine date range
                start_d = None
                end_d = None
                if "september" in q_lower or "sep" in q_lower:
                    start_d = "2026-09-01"
                    end_d = "2026-09-30"
                elif "january" in q_lower or "jan" in q_lower:
                    start_d = "2026-01-01"
                    end_d = "2026-01-31"
                elif "february" in q_lower or "feb" in q_lower:
                    start_d = "2026-02-01"
                    end_d = "2026-02-28"

                # Search term
                search = None
                if "swiggy" in q_lower:
                    search = "Swiggy"
                elif "amazon" in q_lower:
                    search = "Amazon"
                elif "uber" in q_lower:
                    search = "Uber"

                query_spec_dict = {
                    "is_refusal": False,
                    "refusal_reason": None,
                    "aggregation": agg,
                    "direction": direction,
                    "categories": cats,
                    "search": search,
                    "start_date": start_d,
                    "end_date": end_d,
                    "group_by": None,
                    "top_n_limit": limit,
                    "order_by": order,
                }

            return LLMResponse(
                text=json.dumps(query_spec_dict),
                input_tokens=len(prompt) // 4,
                output_tokens=80,
                latency_ms=40,
                estimated_cost=Decimal("0.0006"),
                model_name="fake-llm-queryspec",
                prompt_version=prompt_version,
            )

        # Answer wording handling
        if "personal finance assistant" in prompt.lower() or "query results:" in prompt.lower():
            import re
            res_match = re.search(r'Query Results:\s*"""(.*?)"""', prompt, re.DOTALL)
            results_text = res_match.group(1).strip() if res_match else "{}"
            try:
                res_data = json.loads(results_text)
                if res_data.get("is_refusal"):
                    ans = res_data.get("refusal_reason", "I can't answer that from your data.")
                elif res_data.get("count", 0) == 0:
                    ans = "No matching transactions were found for your query."
                elif res_data.get("aggregation") == "sum":
                    amt = res_data.get("total_amount", 0)
                    ans = f"You spent ₹{amt:,.2f} according to your statements."
                elif res_data.get("aggregation") == "count":
                    c = res_data.get("count", 0)
                    ans = f"There were {c} matching transactions found."
                elif res_data.get("aggregation") == "average":
                    avg_amt = res_data.get("average_amount", 0)
                    ans = f"Your average transaction amount was ₹{avg_amt:,.2f}."
                elif res_data.get("aggregation") in ["top_n", "list"]:
                    rows = res_data.get("rows", [])
                    ans = f"Here are your top {len(rows)} transactions:\n" + "\n".join(
                        f"• {r.get('date')}: {r.get('description')} — ₹{r.get('amount'):,.2f}"
                        for r in rows
                    )
                else:
                    ans = "Here are the query results from your statements."
            except Exception:
                ans = "I processed your spending query from your statements."

            return LLMResponse(
                text=ans,
                input_tokens=len(prompt) // 4,
                output_tokens=60,
                latency_ms=35,
                estimated_cost=Decimal("0.0005"),
                model_name="fake-llm-wording",
                prompt_version=prompt_version,
            )

        # Categorization handling
        if "categorize" in prompt.lower() or "transactions to categorize" in prompt.lower():
            categories_result: list[dict[str, Any]] = []
            import re
            tx_match = re.search(r'"""\s*(\[\s*\{.*?\}\s*\])\s*"""', prompt, re.DOTALL)
            if tx_match:
                try:
                    tx_list = json.loads(tx_match.group(1))
                    for tx in tx_list:
                        row_idx = tx.get("row_index", 1)
                        desc = str(tx.get("description", "")).upper()
                        if any(w in desc for w in ["SWIGGY", "ZOMATO", "RESTAURANT", "FOOD", "CAFE", "DINING", "BAKERY", "TEA"]):
                            cat = "Food and Dining"
                        elif any(w in desc for w in ["BLINKIT", "GROCERY", "GROCERIES", "INSTAMART", "ZEPTO", "BIGBASKET", "DMART", "SUPERMARKET"]):
                            cat = "Groceries"
                        elif any(w in desc for w in ["RENT", "HOUSING", "HOUSE_OWNER", "MAINTENANCE"]):
                            cat = "Rent and Housing"
                        elif any(w in desc for w in ["ELECTRICITY", "BESCOM", "WATER", "GAS", "BILL", "RECHARGE", "AIRTEL", "JIO", "VODAFONE", "BROADBAND", "WIFI"]):
                            cat = "Utilities and Bills"
                        elif any(w in desc for w in ["UBER", "OLA", "RIDE", "PETROL", "FUEL", "METRO", "RAPIDO", "INDIANOIL", "HPCL", "BPCL"]):
                            cat = "Transport"
                        elif any(w in desc for w in ["AMAZON", "FLIPKART", "SHOPPING", "RETAIL", "MYNTRA", "MEESHO"]):
                            cat = "Shopping"
                        elif any(w in desc for w in ["APOLLO", "PHARMACY", "HOSPITAL", "HEALTH", "MEDS", "MEDICAL", "CLINIC", "1MG", "NETMEDS"]):
                            cat = "Health"
                        elif any(w in desc for w in ["NETFLIX", "SPOTIFY", "HOTSTAR", "MOVIE", "ENTERTAINMENT"]):
                            cat = "Entertainment"
                        elif any(w in desc for w in ["FLIGHT", "HOTEL", "MAKEMYTRIP", "TRAVEL", "IRCTC", "AIRLINE", "AIRWAYS"]):
                            cat = "Travel"
                        elif any(w in desc for w in ["COURSERA", "COLLEGE", "TUITION", "COURSE", "EDUCATION", "UDEMY"]):
                            cat = "Education"
                        elif any(w in desc for w in ["SALARY", "ACH/SALARY", "FREELANCE", "DIVIDEND", "INTEREST", "INCOME"]):
                            cat = "Income"
                        elif any(w in desc for w in ["TRANSFER", "UPI", "IMPS", "NEFT", "RTGS", "P2P", "P2A", "SENT TO"]):
                            cat = "Transfers"
                        elif any(w in desc for w in ["CHARGE", "FEE", "SMS ALERT", "PENALTY", "TAX", "GST"]):
                            cat = "Fees and Charges"
                        else:
                            cat = "Other"
                        categories_result.append({"row_index": row_idx, "category": cat, "confidence": 0.95})
                except Exception:
                    pass

            if not categories_result:
                categories_result = [{"row_index": 1, "category": "Other", "confidence": 0.50}]

            return LLMResponse(
                text=json.dumps({"categories": categories_result}),
                input_tokens=len(prompt) // 4,
                output_tokens=len(categories_result) * 20,
                latency_ms=50,
                estimated_cost=Decimal("0.0008"),
                model_name="fake-llm-categorizer",
                prompt_version=prompt_version,
            )

        # Dynamic layout statement parser for real statements
        from api.services.llm.statement_parser import parse_statement_from_text

        data = parse_statement_from_text(prompt)

        # Fallback to mock data only if this was an empty generic test prompt (not statement page extraction)
        if "Statement text:" not in prompt and not data.get("transactions"):
            data = {
                "header": {
                    "bank_name": "Generic Bank",
                    "account_last4": "0000",
                    "currency": "INR",
                    "period_start": "2026-09-01",
                    "period_end": "2026-09-30",
                    "opening_balance": 1000.00,
                    "closing_balance": 1000.00,
                },
                "transactions": [],
            }

        return LLMResponse(
            text=json.dumps(data),
            input_tokens=len(prompt) // 4,
            output_tokens=max(len(data.get("transactions", [])) * 25, 80),
            latency_ms=75,
            estimated_cost=Decimal("0.0012"),
            model_name="fake-llm-heuristic",
            prompt_version=prompt_version,
        )
