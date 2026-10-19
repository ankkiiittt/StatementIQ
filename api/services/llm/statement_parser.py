"""Heuristic rule-based bank statement parser.

Parses text extracted from Indian bank statements (Union Bank, HDFC, ICICI, SBI, Axis, etc.)
into structured header and transaction dictionaries.
"""
import re
from typing import Any

MONTHS_MAP = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}


def normalize_date(d_str: str) -> str:
    """Normalize DD/MM/YYYY, DD-MM-YYYY, DD-Mon-YYYY to YYYY-MM-DD."""
    d_str = d_str.strip()
    if "-" in d_str and len(d_str.split("-")[0]) == 4:
        return d_str
    sep = "/" if "/" in d_str else "-"
    pts = d_str.split(sep)
    if len(pts) == 3:
        m = pts[1].upper()
        m_num = MONTHS_MAP.get(m[:3], m if len(m) == 2 else "01")
        # Handle 2-digit vs 4-digit year
        year = pts[2] if len(pts[2]) == 4 else f"20{pts[2]}"
        day = pts[0].zfill(2)
        return f"{year}-{m_num.zfill(2)}-{day}"
    return d_str


def to_float_or_none(tok: str | None) -> float | None:
    """Convert string amount to float, returning None if invalid or dash."""
    if not tok or tok.strip() in ["-", "--", "None", "", "null"]:
        return None
    try:
        return float(tok.replace(",", "").strip())
    except ValueError:
        return None


def detect_bank_name(text: str) -> str | None:
    """Accurately detect the bank name from statement header or IFSC code without false matching transactions."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    date_regex = re.compile(r"^\d{2}[-/][A-Za-z0-9]{2,3}[-/]\d{2,4}|^\d{4}-\d{2}-\d{2}")

    header_lines: list[str] = []
    for line in lines[:35]:
        if date_regex.match(line):
            break
        header_lines.append(line)
    header_text = " ".join(header_lines).upper()

    bank_patterns: list[tuple[str, list[str]]] = [
        ("State Bank of India", ["STATE BANK OF INDIA", "STATE BANK OF BIKANER", "STATE BANK OF HYDERABAD"]),
        ("Union Bank of India", ["UNION BANK OF INDIA", "UNION BANK"]),
        ("HDFC Bank", ["HDFC BANK LIMITED", "HDFC BANK", "HDFC"]),
        ("ICICI Bank", ["ICICI BANK LIMITED", "ICICI BANK", "ICICI"]),
        ("Axis Bank", ["AXIS BANK LIMITED", "AXIS BANK", "UTIB"]),
        ("Kotak Mahindra Bank", ["KOTAK MAHINDRA BANK", "KOTAK BANK", "KOTAK"]),
        ("Punjab National Bank", ["PUNJAB NATIONAL BANK", "PNB"]),
        ("Bank of Baroda", ["BANK OF BARODA"]),
        ("Canara Bank", ["CANARA BANK"]),
        ("Bank of India", ["BANK OF INDIA"]),
        ("IndusInd Bank", ["INDUSIND BANK"]),
        ("IDFC FIRST Bank", ["IDFC FIRST BANK", "IDFC BANK"]),
        ("Yes Bank", ["YES BANK"]),
        ("Federal Bank", ["FEDERAL BANK"]),
        ("Indian Bank", ["INDIAN BANK"]),
        ("Central Bank of India", ["CENTRAL BANK OF INDIA"]),
        ("UCO Bank", ["UCO BANK"]),
        ("Indian Overseas Bank", ["INDIAN OVERSEAS BANK"]),
    ]

    # 1. Match from header lines before transactions start
    for bank_name, keywords in bank_patterns:
        if any(k in header_text for k in keywords):
            return bank_name

    # 2. Check official account IFSC Code (e.g. "IFSC Code : SBIN0002011")
    ifsc_m = re.search(r"(?:IFSC|RTGS/NEFT\s+IFSC)\s*(?:Code)?\s*[:.\s]*([A-Z]{4})0[A-Z0-9]{6}", text, re.I)
    if ifsc_m:
        prefix = ifsc_m.group(1).upper()
        ifsc_map = {
            "SBIN": "State Bank of India",
            "UBIN": "Union Bank of India",
            "HDFC": "HDFC Bank",
            "ICIC": "ICICI Bank",
            "UTIB": "Axis Bank",
            "KKBK": "Kotak Mahindra Bank",
            "PUNB": "Punjab National Bank",
            "BARB": "Bank of Baroda",
            "CNRB": "Canara Bank",
            "BKID": "Bank of India",
            "INDB": "IndusInd Bank",
            "IDFB": "IDFC FIRST Bank",
            "YESB": "Yes Bank",
            "FDRL": "Federal Bank",
            "IDIB": "Indian Bank",
            "CBIN": "Central Bank of India",
            "UCBA": "UCO Bank",
            "IOBA": "Indian Overseas Bank",
        }
        if prefix in ifsc_map:
            return ifsc_map[prefix]

    # 3. Clean line in header lines containing 'BANK' (excluding disclaimers and branch noise)
    for line in header_lines[:10]:
        u_line = line.upper()
        if "BANK" in u_line:
            noise_words = [
                "EMAIL", "STATEMENT", "DISCLAIMER", "PASSWORD", "MEDIUM",
                "BRANCH", "ACCOUNT", "SUMMARY", "WELCOME", "DEPOSIT",
                "WITHDRAWAL", "SHARE", "CALL", "SMS", "POWER OF ATTORNEY",
            ]
            if not any(w in u_line for w in noise_words):
                return line.strip()

    # 4. Check short prompts / test queries
    for bank_name, keywords in bank_patterns:
        if any(k in text.upper() for k in keywords):
            if len(text) < 200 or "BANK" in text.upper():
                return bank_name

    return None


def parse_statement_from_text(prompt_text: str) -> dict[str, Any]:
    """Parse raw statement text or LLM extraction prompt into header and transactions."""
    text_match = re.search(r'Statement text:\s*"""(.*?)"""', prompt_text, re.DOTALL)
    text = text_match.group(1).strip() if text_match else prompt_text
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    header: dict[str, Any] = {
        "bank_name": detect_bank_name(text),
        "account_last4": None,
        "currency": "INR",
        "period_start": None,
        "period_end": None,
        "opening_balance": None,
        "closing_balance": None,
    }

    acc_m = re.search(r'(?:Account|A/c|A/C)\s*(?:Number|No)?\s*[:.\s]*([0-9Xx*]{4,25})', text, re.I)
    if acc_m:
        digits = re.sub(r'[^0-9]', '', acc_m.group(1))
        if len(digits) >= 4:
            header["account_last4"] = digits[-4:]

    p_m = re.search(
        r'(\d{2}[-/][A-Za-z0-9]{2,3}[-/]\d{2,4}|\d{4}-\d{2}-\d{2})\s*(?:to|-)\s*(\d{2}[-/][A-Za-z0-9]{2,3}[-/]\d{2,4}|\d{4}-\d{2}-\d{2})',
        text,
        re.I,
    )
    if p_m:
        header["period_start"] = normalize_date(p_m.group(1))
        header["period_end"] = normalize_date(p_m.group(2))

    op_m = re.search(r'Opening\s*Balance[.:\s]*(?:INR\s*)?([0-9,]+(?:\.[0-9]{2})?)', text, re.I)
    if op_m:
        header["opening_balance"] = float(op_m.group(1).replace(',', ''))
    else:
        bf_m = re.search(r'Brought\s*Forward[^\n]*\n\s*([0-9,]+(?:\.[0-9]{2})?)\s*(?:CR|DR)?', text, re.I)
        if bf_m:
            header["opening_balance"] = float(bf_m.group(1).replace(',', ''))

    cl_m = re.search(r'Closing\s*Balance[.:\s]*(?:INR\s*)?([0-9,]+(?:\.[0-9]{2})?)', text, re.I)
    if cl_m:
        header["closing_balance"] = float(cl_m.group(1).replace(',', ''))
    else:
        cb_m = re.search(r'Closing\s*Balance[^\n]*\n(?:[^\n]*\s+)?([0-9,]+(?:\.[0-9]{2})?)\s*(?:CR|DR)?', text, re.I)
        if cb_m:
            header["closing_balance"] = float(cb_m.group(1).replace(',', ''))

    txns: list[dict[str, Any]] = []
    date_regex = re.compile(r'^(\d{2}[-/][A-Za-z0-9]{2,3}[-/]\d{2,4}|\d{4}-\d{2}-\d{2})')

    for line in lines:
        dm = date_regex.match(line)
        if not dm:
            continue
        raw_date = dm.group(1)
        iso_date = normalize_date(raw_date)
        rest = line[len(raw_date):].strip()

        # Format A: amount(Dr/Cr) balance(Cr/Dr) (e.g. Union Bank, PNB)
        dr_cr_m = re.search(r'([0-9,.]+)\s*\((Dr|Cr)\)\s*([0-9,.]+)?\s*(?:\((?:Dr|Cr)\))?$', rest, re.I)
        if dr_cr_m:
            amt = float(dr_cr_m.group(1).replace(',', ''))
            direction = 'debit' if dr_cr_m.group(2).lower() == 'dr' else 'credit'
            bal = float(dr_cr_m.group(3).replace(',', '')) if dr_cr_m.group(3) else None
            desc = rest[:dr_cr_m.start()].strip()
            # If description begins with transaction ref ID (e.g. Y9522656), clean it for nicer display
            parts = desc.split(None, 1)
            if len(parts) > 1 and re.match(r'^[A-Z0-9]{6,14}$', parts[0]):
                desc = parts[1]
            txns.append({
                'date': iso_date,
                'description': desc,
                'amount': amt,
                'direction': direction,
                'balance': bal,
            })
            continue

        # Format B: ICICI style: [Desc] [DEBIT/CREDIT] [Amount] [Balance]
        type_m = re.search(r'\s+(DEBIT|CREDIT)\s+([0-9,.]+)\s+([0-9,.]+)$', rest, re.I)
        if type_m:
            direction = type_m.group(1).lower()
            amt = float(type_m.group(2).replace(',', ''))
            bal = float(type_m.group(3).replace(',', ''))
            desc = rest[:type_m.start()].strip()
            txns.append({
                'date': iso_date,
                'description': desc,
                'amount': amt,
                'direction': direction,
                'balance': bal,
            })
            continue

        # Format C: Standard 3 columns [Withdrawal, Deposit, Balance] (HDFC, SBI)
        tokens = rest.split()
        if len(tokens) >= 3:
            b_num = to_float_or_none(tokens[-1])
            d_num = to_float_or_none(tokens[-2])
            w_num = to_float_or_none(tokens[-3])

            if b_num is not None and (w_num is not None or d_num is not None):
                if w_num is not None and w_num > 0:
                    amt = w_num
                    direction = 'debit'
                else:
                    amt = d_num or 0.0
                    direction = 'credit'
                desc = ' '.join(tokens[:-3])
                # Remove trailing value date if present (e.g. 02/09/2026)
                desc = re.sub(r'\s+\d{2}[-/]\d{2}[-/]\d{4}$', '', desc)
                txns.append({
                    'date': iso_date,
                    'description': desc,
                    'amount': amt,
                    'direction': direction,
                    'balance': b_num,
                })
                continue

        # Format D: 2 columns [Amount, Balance] with (Dr)/(Cr) suffix or direction token
        two_col_m = re.search(r'\s+([0-9,.]+)\s+([0-9,.]+)\s*(Dr|Cr|DR|CR)$', rest)
        if two_col_m:
            amt = float(two_col_m.group(1).replace(',', ''))
            bal = float(two_col_m.group(2).replace(',', ''))
            direction = 'debit' if two_col_m.group(3).lower() == 'dr' else 'credit'
            desc = rest[:two_col_m.start()].strip()
            txns.append({
                'date': iso_date,
                'description': desc,
                'amount': amt,
                'direction': direction,
                'balance': bal,
            })
            continue

    # Heuristic opening balance calculation if not found in header
    if header['opening_balance'] is None and txns and txns[0]['balance'] is not None:
        first = txns[0]
        if first['direction'] == 'debit':
            header['opening_balance'] = round(first['balance'] + first['amount'], 2)
        else:
            header['opening_balance'] = round(first['balance'] - first['amount'], 2)

    # Heuristic closing balance calculation if not found in header
    if header['closing_balance'] is None and txns and txns[-1]['balance'] is not None:
        header['closing_balance'] = txns[-1]['balance']

    return {'header': header, 'transactions': txns}
