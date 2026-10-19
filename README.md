# StatementIQ 💳

> **AI-Powered Bank Statement Analyzer & Spending Intelligence**  
> Converts text-based PDF bank statements (English, INR) into verified, categorized transactions with balance reconciliation checks, visual spending insights, and natural language chat exploration.

---

## 1. System Architecture

```mermaid
flowchart TD
    subgraph UI ["Streamlit Frontend (Port 8501)"]
        U1["Upload View (Drag & Drop)"]
        U2["Statements List & Management"]
        U3["Transaction Review & Inline Edits"]
        U4["Spending Insights Dashboard"]
        U5["Ask Your Statements Chat"]
    end

    subgraph API ["FastAPI Backend (Port 8001)"]
        R1["/statements"]
        R2["/transactions"]
        R3["/insights"]
        R4["/chat"]
        R5["/categories"]
    end

    subgraph Services ["Core Services Pipeline"]
        S1["PDF Intake & Text Extraction (pdfplumber)"]
        S2["Smart Layout Parser & LLM Extraction"]
        S3["Cross-Page Overlap Deduplication"]
        S4["Balance Reconciliation Engine"]
        S5["Batch Transaction Categorization"]
        S6["QuerySpec Builder & Chat Coordinator"]
    end

    subgraph Data ["Database & Storage"]
        DB[("PostgreSQL / SQLite")]
        FS[("PDF File Storage (UUID paths)")]
    end

    subgraph LLM ["Extraction & LLM Interface"]
        L1["OCI Generative AI (Optional Cloud LLM)"]
        L2["Smart Heuristic Statement Parser (Built-in Zero-Config)"]
    end

    UI --> API
    API --> Services
    Services --> DB
    Services --> FS
    Services --> LLM
```

---

## 2. Core Features

- **F1 Upload & Intake:** Drag-and-drop intake validating text-based PDFs (up to 10 MB and 30 pages) with scanned PDF detection and guidance.
- **F2 Smart Multi-Layout Extraction:** Robust layout parser (`api/services/llm/statement_parser.py`) supporting diverse Indian banking formats with zero external API key requirements:
  - **Amount(Dr/Cr) Balance(Cr/Dr)** (Union Bank of India, Punjab National Bank, etc.)
  - **3-Column Tabular** `Withdrawal Deposit Balance` (State Bank of India, HDFC Bank)
  - **Type-Flagged Columns** `[Desc] [DEBIT/CREDIT] [Amount] [Balance]` (ICICI Bank)
  - Cross-page transaction deduplication preventing duplicate boundary rows.
- **F3 Header-Scoped Bank & Account Identification:**
  - Isolates header lines prior to transaction tables to accurately extract bank names and account numbers.
  - Matches official bank IFSC prefixes (`SBIN`, `UBIN`, `HDFC`, `ICIC`, `UTIB`, `KKBK`, `BARB`, `PUNB`, `CNRB`, etc.) without false positive interference from UPI transfer narration handles.
- **F4 Balance Reconciliation Engine:** Automatically verifies:
  $$\text{Opening Balance} + \sum \text{Credits} - \sum \text{Debits} == \text{Closing Balance}$$
  Displays **Passed** (green badge with ₹0.00 diff), **Failed with difference** (red badge with delta), or **Not Available** (grey badge). Supports statement summary blocks (`Brought Forward` / `Closing Balance`).
- **F5 14 Fixed Expense Categories:** Batches categorization into 14 distinct categories (*Food and Dining, Groceries, Rent and Housing, Utilities and Bills, Transport, Shopping, Health, Entertainment, Travel, Education, Transfers, Income, Fees and Charges, Other*). Protects manual user edits (`category_source = 'user'`).
- **F6 Review & Interactive Edits:** Live editable transaction table. Edit cleaned descriptions, reassign categories, delete erroneous rows with auto-recalculated reconciliation, and confirm statements.
- **F7 Spending Insights Dashboard:** 4 executive KPI cards (Spend, Income, Net Savings, Counts), monochromatic Altair category bar charts, monthly spend vs. income trend charts, and top 10 merchants breakdown.
- **F8 Ask Your Statements (Chat):** Safe conversational exploration converting user questions into strongly-typed `QuerySpec` parameters (protects against raw model-generated SQL) with human-readable applied filters.
- **F9 Privacy & Data Hygiene:** Full cascade deletion removing statement records, transactions, extraction run logs, and the physical PDF file. Masked account numbers (last 4 digits only).

---

## 3. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| **Language** | Python 3.11+ | Optimal ecosystem for PDF parsing, data science, and LLM orchestration |
| **Backend** | FastAPI + Pydantic v2 | High-performance async REST API with typed request/response validation |
| **Frontend** | Streamlit | Rapid, rich editorial UI with custom CSS design tokens |
| **Database** | SQLite (Default) / PostgreSQL | Zero-config standalone SQLite with WAL mode; extensible to PostgreSQL |
| **Migrations** | Alembic | Version-controlled schema migrations and category seed runner |
| **PDF Extraction**| `pdfplumber` | Layout-aware text extraction across varied banking column formats |
| **Extraction Engine**| Smart Layout Parser + OCI GenAI | Zero-config local heuristic extraction; swappable cloud LLM interface |

---

## 4. Design System & Aesthetics

Adheres to *Understated Editorial Finance*:
- **Background:** Warm off-white canvas (`#F7F6F2`)
- **Surface:** Clean white surface cards (`#FFFFFF`) with 1 px hairline borders (`#E1DED6`)
- **Primary:** Deep forest green (`#0F5C4D`)
- **Accents:** Muted warning amber (`#C8872B`), success green (`#2E7D4F`), destructive red (`#B3261E`)
- **Typography:** **Inter** font family with tabular numeric figures (`font-variant-numeric: tabular-nums`)
- **Currency:** Indian numbering system formatting (e.g., `₹12,34,567.89`)

---

## 5. Deployment on Streamlit Community Cloud

StatementIQ supports self-contained, zero-configuration deployment directly on [Streamlit Community Cloud](https://share.streamlit.io):

1. **Push your code to GitHub:**
   ```bash
   git add -A
   git commit -m "feat: deploy StatementIQ on Streamlit Cloud"
   git push origin main
   ```

2. **Deploy on Streamlit Community Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io) and click **"New app"**.
   - Select your repository (`<your-username>/StatementIQ`).
   - Set **Branch** to `main` (or `master`).
   - Set **Main file path** to `streamlit_app.py`.
   - Click **Deploy!**

> **How it works on Streamlit Cloud:**  
> `streamlit_app.py` automatically initializes the local database, seeds the 14 standard expense categories, and auto-launches the background FastAPI service with zero external server configuration required.

### Optional Cloud Secrets:
If connecting to an external PostgreSQL database (e.g. Supabase, Neon) or OCI Generative AI, add these in Streamlit Cloud > Settings > Secrets:
```toml
# Optional: External PostgreSQL
DATABASE_URL = "postgresql+psycopg2://user:pass@host:5432/dbname"

# Optional: OCI GenAI Cloud Model
LLM_PROVIDER = "oci"
OCI_COMPARTMENT_ID = "ocid1.compartment.oc1..example"
OCI_MODEL_ID = "ocid1.generativeaimodel.oc1..example"
```

---

## 6. Local Quick Start

1. **Activate virtual environment:**
   ```bash
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Streamlit (Standalone):**
   ```bash
   streamlit run streamlit_app.py
   ```
   *StatementIQ will automatically launch the backend API on port 8001 and open the web UI on port 8501.*

---

## 7. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `POST` | `/statements` | Upload PDF statement and initiate extraction pipeline |
| `GET` | `/statements` | List statements with status and reconciliation outcomes |
| `GET` | `/statements/{id}` | Detailed statement metadata |
| `GET` | `/statements/{id}/transactions` | Paginated transactions with category, date, and text filters |
| `POST` | `/statements/{id}/confirm` | Confirm statement data |
| `POST` | `/statements/{id}/retry` | Re-run extraction pipeline on failed statement |
| `DELETE` | `/statements/{id}` | Cascade delete statement, rows, logs, and stored PDF |
| `PATCH` | `/transactions/{id}` | Update category (`category_source = 'user'`) or cleaned description |
| `DELETE` | `/transactions/{id}` | Delete transaction row with reconciliation recalculation |
| `GET` | `/insights` | Totals, category breakdown, monthly trends, and top 10 merchants |
| `POST` | `/chat` | Natural language spending queries via validated `QuerySpec` |
| `GET` | `/chat/{session_id}` | Retrieve conversation history for a chat session |
| `GET` | `/categories` | List the 14 standard expense categories in sort order |
