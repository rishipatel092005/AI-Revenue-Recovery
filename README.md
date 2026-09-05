# RecoverAI

RecoverAI is a deterministic revenue-recovery control center for failed payments. It diagnoses each failure, selects the lowest-cost eligible intervention, applies execution-time safety rules, and records every decision and outcome in Supabase.

Built for the Razorpay Buildathon 2026, Track 3.

## 🔄 RecoverAI Recovery Workflow

RecoverAI follows a controlled revenue recovery loop:

**Detect → Diagnose → Decide → Validate → Intervene → Verify → Audit**

```mermaid
flowchart TD
    A["Payment Failure Event"] --> B["Transaction + Customer Data"]

    B --> C["AI Diagnosis"]

    C --> D{"Failure Type"}

    D -->|"Retryable"| E["Recovery Decision"]
    D -->|"Customer Action"| E
    D -->|"Fraud / Risk"| F["Block / Escalate"]

    E --> G["Deterministic Policy Gates"]

    G -->|"Approved"| H["Recovery Intervention"]
    G -->|"Blocked"| F

    H --> I["Outcome Tracking"]

    I -->|"Recovered"| J["Revenue Recovered"]
    I -->|"Pending / Failed"| K["Fallback / Review"]

    C --> L["AI Recovery Assistant"]
    E --> L
    I --> L

    J --> M["Audit Trail"]
    K --> M
    F --> M

    M --> N["RecoverAI Control Center"]

## What It Does

- Analyzes failed payments and their failure reasons
- Selects `auto_retry`, `whatsapp`, `voice_call`, or manual review
- Blocks fraud-risk contact and enforces a three-contact cap
- Defers voice actions outside the 9:00-21:00 calling window
- Simulates retry, WhatsApp, and voice actions safely by default
- Maintains an append-only audit trail
- Provides a Streamlit control center with queue, decisions, customers, health, and Copilot views

The bundled dataset contains 30 synthetic customers and 120 synthetic failed transactions. All contact data is synthetic or masked.

## Safety First

`DRY_RUN=true` is the default and recommended demo configuration. In this mode:

- No WhatsApp message is sent
- No voice call is placed
- No real payment is retried
- Provider actions are composed or simulated and written to `audit_log`

Razorpay credentials are not required for the current demo. The payment-link and gateway integrations are intentionally simulated.

## Requirements

- Python 3.11 or newer
- A Supabase project for the full pipeline and dashboard
- Supabase Project URL
- Supabase Secret key, formerly called the service-role key

Twilio, Bolna, Vapi, and Razorpay credentials are optional and are not needed while dry-run mode is enabled.

## Windows PowerShell Setup

Run commands from the repository root.

### 1. Create and activate the virtual environment

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in only the Supabase values:

```powershell
Copy-Item .env.example .env
```

Set these values in `.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-secret-key
DRY_RUN=true
```

Never commit `.env` or paste secret keys into the repository.

### 4. Create the database tables

Open the Supabase SQL Editor, paste the complete contents of `schema.sql`, and run it. Keep Row Level Security enabled. The application uses the Supabase Secret key for its server-side demo operations.

### 5. Load the synthetic dataset

The current CSVs contain 30 customers and 120 transactions. To replace existing demo data with the CSVs:

```powershell
.venv\Scripts\python.exe setup_database.py --force
```

### 6. Run the recovery pipeline

```powershell
.venv\Scripts\python.exe run_pipeline.py
```

### 7. Start the dashboard

```powershell
.venv\Scripts\python.exe -m streamlit run dashboard.py
```

Open [http://localhost:8501](http://localhost:8501).

## Frontend Pages

- **Overview**: KPIs, recovery funnel, revenue exposure, failure breakdown, and recent activity
- **Revenue at Risk**: ranked failed payments and exposure
- **Recovery Queue**: filters, selected-payment detail, policy gate, and recovery timeline
- **AI Decisions**: transparent rule-based decisions without hidden chain-of-thought
- **AI Recovery Assistant**: evidence-grounded answers from current Supabase records
- **Transactions**: complete transaction view
- **Customers**: customer exposure and recovery state
- **Audit Trail**: chronological decision and outcome evidence
- **System Health**: database, recovery engine, simulator, and safety status

## Common Commands

```powershell
# Reset interventions and audit records for a fresh run
.venv\Scripts\python.exe reset_demo.py --yes

# Run one complete safe recovery round
.venv\Scripts\python.exe run_pipeline.py

# Run only the decision engine against local CSV files
$env:SUPABASE_URL=""; $env:SUPABASE_KEY=""; .venv\Scripts\python.exe recovery\decision_engine.py

# Run the WhatsApp simulator directly
.venv\Scripts\python.exe -m channels.whatsapp_notifier

# Verify database connection and table counts
.venv\Scripts\python.exe setup_database.py --check

# Run the built-in tests without pytest
$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_agent.py
```

## Project Structure

```text
dashboard.py                 Streamlit control center
config.py                    Environment and dry-run configuration
db.py                        Supabase reads, writes, and audit helpers
run_pipeline.py              End-to-end recovery round
setup_database.py            Schema verification and CSV seeding
generate_synthetic_data.py   Reproducible 30/120 synthetic dataset
reset_demo.py                Reset demo interventions and audit events
schema.sql                   Supabase tables and recovery_metrics view
data/                       Synthetic customers and transactions
recovery/                    Decision engine, stopping rules, retry, outcomes
channels/                    WhatsApp and voice channel executors
ui/                         Theme, components, and evidence-grounded assistant
tests/                      Credential-free regression suite
```

## Testing

The project includes 56 credential-free tests. They verify rule precedence, stopping rules, call windows, contact accounting, dry-run channels, voice normalization, and dashboard theme constraints.

```powershell
$env:PYTHONPATH=(Get-Location).Path
.venv\Scripts\python.exe tests\test_agent.py
```

`pytest` is optional; it is not required by the project.

## Going Live

Live sending is intentionally outside the demo path. Only set `DRY_RUN=false` after adding verified provider credentials and reviewing the safety rules.

- WhatsApp requires Twilio credentials and an approved sending setup.
- Voice requires Bolna or Vapi credentials.
- Payment links require a real payment-link service.
- A production deployment should add webhook signature verification, idempotency, authentication, rate limits, and operational monitoring.

## License

MIT. See [LICENSE](LICENSE).
