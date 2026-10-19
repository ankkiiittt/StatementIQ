"""Versioned prompts for LLM operations."""

EXTRACTION_PROMPT_V1 = """You are a financial document extractor.
Extract all banking details and transactions from the following bank statement page text.

Return ONLY a JSON object with this exact structure:
{
  "header": {
    "bank_name": "string or null",
    "account_last4": "last 4 digits of account number or null",
    "currency": "INR",
    "period_start": "YYYY-MM-DD or null",
    "period_end": "YYYY-MM-DD or null",
    "opening_balance": number or null,
    "closing_balance": number or null
  },
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "description": "raw transaction text exactly as in statement",
      "amount": positive decimal number,
      "direction": "debit" or "credit",
      "balance": balance after transaction as decimal or null
    }
  ]
}

Rules:
1. Always normalize transaction dates to ISO format: YYYY-MM-DD.
2. The amount must always be a positive number (> 0).
3. The direction must strictly be either "debit" (money out / withdrawal) or "credit" (money in / deposit).
4. Do not invent transactions. If no transactions are found on this page, return an empty list for "transactions".
5. Return ONLY the raw JSON object, without any explanatory text or markdown formatting.

Statement text:
\"\"\"
{statement_text}
\"\"\"
"""

RETRY_PROMPT_TEMPLATE = """Your previous response failed validation with the following error:
{error_message}

Please fix the error and re-extract the data.
Ensure your response is valid JSON matching the exact schema requested.
Do not include markdown fences or extra explanations.

Statement text:
\"\"\"
{statement_text}
\"\"\"
"""

CATEGORIZATION_PROMPT_V1 = """You are a bank transaction categorization assistant.
Assign each transaction one of the following 14 fixed categories based on its description:
1. Food and Dining (restaurants, swiggy, zomato, cafes, dining)
2. Groceries (supermarkets, blinkit, instamart, zepto, bigbasket)
3. Rent and Housing (rent payments, maintenance, society dues)
4. Utilities and Bills (electricity, water, gas, internet, mobile recharge)
5. Transport (fuel, petrol, uber, ola, metro, parking, toll)
6. Shopping (amazon, flipkart, clothing, electronics, retail stores)
7. Health (pharmacy, hospitals, doctors, apollo, diagnostic tests)
8. Entertainment (movies, netflix, spotify, hotstar, gaming, events)
9. Travel (flights, hotels, irctc, makemytrip, vacations)
10. Education (school/college tuition, courses, books, coursera)
11. Transfers (UPI/NEFT/IMPS transfers to individuals or other accounts)
12. Income (salary, interest, dividends, freelance income, bonuses)
13. Fees and Charges (annual card fees, bank charges, penalties, taxes)
14. Other (unclear or uncategorized transactions)

Return ONLY a JSON object with this exact structure:
{
  "categories": [
    {
      "row_index": integer,
      "category": "exact category name from the list above",
      "confidence": float between 0.0 and 1.0
    }
  ]
}

Transactions to categorize:
\"\"\"
{transactions_json}
\"\"\"
"""

QUERY_SPEC_PROMPT_V1 = """You are a financial query translator for StatementIQ.
Convert the user's natural language question into a structured QuerySpec JSON object.
Never invent SQL or SQL code.

Available Categories:
1. Food and Dining
2. Groceries
3. Rent and Housing
4. Utilities and Bills
5. Transport
6. Shopping
7. Health
8. Entertainment
9. Travel
10. Education
11. Transfers
12. Income
13. Fees and Charges
14. Other

Current reference date: {current_date}

Return ONLY a JSON object with this exact structure:
{
  "is_refusal": false,
  "refusal_reason": null,
  "aggregation": "sum",
  "direction": "debit",
  "categories": ["Food and Dining"],
  "search": null,
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "group_by": null,
  "top_n_limit": 10,
  "order_by": "amount_desc"
}

Field instructions:
1. "is_refusal": true if the question is non-financial, unrelated to banking/transactions, chit-chat, or asking for financial advice/speculation. In that case, set "refusal_reason": "I can't answer that from your data."
2. "aggregation": one of "sum", "count", "average", "list", "top_n".
   - "how much did I spend..." -> "sum"
   - "how many transactions..." -> "count"
   - "what was my average spend..." -> "average"
   - "what were my top 5 largest expenses..." -> "top_n", top_n_limit: 5, order_by: "amount_desc"
   - "show me / list transactions..." -> "list"
3. "direction":
   - "debit" for spending, expenses, purchases, payments out.
   - "credit" for income, salary, deposits, earnings, refunds.
   - null if inquiring about both directions or overall count.
4. "categories": list of exact matching category names from the 14 available categories, or null.
5. "search": merchant or keyword substring (e.g. "Swiggy", "Amazon", "Uber"), or null.
6. "start_date" & "end_date": ISO date strings (YYYY-MM-DD) or null. Resolve relative dates like "in September", "last month", "2026" using the reference date {current_date}.
7. "group_by": "category", "month", "merchant", or null.
8. "top_n_limit": integer for top_n or list queries (default 10).
9. "order_by": "amount_desc", "amount_asc", "date_desc", or "date_asc", or null.

Question:
\"\"\"
{question}
\"\"\"
"""

ANSWER_WORDING_PROMPT_V1 = """You are a helpful and precise personal finance assistant.
Wording a concise, accurate answer to the user's question based strictly on the query results.
Do not invent or assume any figures not present in the results.

Question: {question}
Query Results:
\"\"\"
{result_json}
\"\"\"

Guidelines:
1. Format all currency figures in Indian Rupees (e.g. ₹1,250.00).
2. Be polite, direct, and concise (1-2 sentences unless listing items).
3. If listing top transactions or items, provide a clear bulleted list with date, merchant/description, and formatted amount.
4. If the results contain 0 matching transactions or zero amount, politely state that no matching transactions were found.
"""
