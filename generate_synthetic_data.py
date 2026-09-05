"""
Generates a reproducible synthetic batch for the AI Revenue Recovery Agent.

Purpose:
- Create synthetic customers and revenue-at-risk events
- Provide enough variation for batch evaluation
- Support failed payments, checkout abandonment, subscriptions and overdue invoices
- Keep all contact information synthetic
- Avoid any real customer/payment communication

Run:
    python generate_synthetic_data.py

Output:
    data/customers.csv
    data/transactions.csv
"""

import csv
import os
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)

# ---------------------------------------------------------------------------
# FAILURE / DIAGNOSIS DATA
# ---------------------------------------------------------------------------

REASON_CATEGORY_MAP = {
    "insufficient_funds": "customer_action",
    "card_expired": "customer_action",
    "invalid_otp": "customer_action",
    "bank_timeout": "retryable",
    "processing_error": "retryable",
    "network_error": "retryable",
    "risk_flagged": "fraud_risk",
}

REASON_CODES = list(REASON_CATEGORY_MAP.keys())

REASON_WEIGHTS = [
    0.28,  # insufficient_funds
    0.18,  # card_expired
    0.08,  # invalid_otp
    0.20,  # bank_timeout
    0.15,  # processing_error
    0.06,  # network_error
    0.05,  # risk_flagged
]

FIRST_NAMES = [
    "Aarav", "Diya", "Kabir", "Ananya", "Vihaan",
    "Ishita", "Reyansh", "Myra", "Advik", "Kiara",
    "Ayaan", "Meera", "Dhruv", "Saanvi", "Yuvan",
    "Riya", "Dev", "Tara", "Arnav", "Nisha",
    "Rudra", "Aditi", "Kunal", "Mihika", "Raghav"
]

LAST_NAMES = [
    "Mehta", "Shah", "Malhotra", "Joshi", "Kapoor",
    "Rao", "Verma", "Sethi", "Bansal", "Khanna",
    "Iyer", "Arora", "Desai", "Singhania", "Nair"
]


# ---------------------------------------------------------------------------
# CUSTOMER GENERATION
# ---------------------------------------------------------------------------

def generate_masked_phone(index: int) -> str:
    """
    Generate a clearly synthetic phone identifier.

    We intentionally do not generate real-looking customer phone numbers.
    """
    return f"3547{1000 + index:04d}"


def gen_customers(n: int = 30):
    customers = []

    for i in range(n):
        segment = random.choices(
            ["b2c_subscription", "b2b_invoice"],
            weights=[0.65, 0.35],
            k=1,
        )[0]

        ltv_tier = random.choices(
            ["low", "mid", "high"],
            weights=[0.35, 0.45, 0.20],
            k=1,
        )[0]

        customers.append(
            {
                "id": str(uuid.uuid4()),
                "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                "phone": generate_masked_phone(i + 1),
                "email": f"demo_customer_{i + 1}@example.com",
                "segment": segment,
                "ltv_tier": ltv_tier,
            }
        )

    return customers


# ---------------------------------------------------------------------------
# TRANSACTION GENERATION
# ---------------------------------------------------------------------------

def amount_for_tier(tier: str) -> float:
    if tier == "low":
        return round(random.uniform(200, 999), 2)

    if tier == "mid":
        return round(random.uniform(1000, 4999), 2)

    return round(random.uniform(5000, 25000), 2)


def gen_transactions(customers, n: int = 120):
    """
    Generate a realistic-looking batch.

    We intentionally create:
    - retryable failures
    - customer-action failures
    - fraud-risk cases
    - multiple retry attempts
    - high-value transactions
    - varied timestamps
    """

    transactions = []

    for _ in range(n):
        customer = random.choice(customers)

        reason = random.choices(
            REASON_CODES,
            weights=REASON_WEIGHTS,
            k=1,
        )[0]

        category = REASON_CATEGORY_MAP[reason]

        amount = amount_for_tier(customer["ltv_tier"])

        attempt_count = random.choices(
            [0, 1, 2, 3],
            weights=[0.45, 0.30, 0.17, 0.08],
            k=1,
        )[0]

        # Create realistic historical timestamps
        created = datetime.now() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

        transactions.append(
            {
                "id": str(uuid.uuid4()),
                "customer_id": customer["id"],
                "amount": amount,
                "currency": "INR",
                "failure_reason_code": reason,
                "diagnosis_category": category,
                "attempt_count": attempt_count,
                "status": "failed",
                "created_at": created.isoformat(),
            }
        )

    return transactions


# ---------------------------------------------------------------------------
# CSV WRITER
# ---------------------------------------------------------------------------

def write_csv(rows, path, fieldnames):
    """
    Write to a temporary file first and then replace the target.

    This prevents a partially-written CSV if something fails.
    """

    tmp = f"{path}.tmp"

    with open(
        tmp,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    # Larger batch for Track 03 evaluation
    customers = gen_customers(30)
    transactions = gen_transactions(customers, 120)

    write_csv(
        customers,
        "data/customers.csv",
        [
            "id",
            "name",
            "phone",
            "email",
            "segment",
            "ltv_tier",
        ],
    )

    write_csv(
        transactions,
        "data/transactions.csv",
        [
            "id",
            "customer_id",
            "amount",
            "currency",
            "failure_reason_code",
            "diagnosis_category",
            "attempt_count",
            "status",
            "created_at",
        ],
    )

    total_at_risk = sum(
        transaction["amount"]
        for transaction in transactions
    )

    print("=" * 60)
    print("Synthetic Revenue Recovery Dataset")
    print("=" * 60)

    print(f"Customers generated   : {len(customers)}")
    print(f"Transactions generated : {len(transactions)}")
    print(f"Total amount at risk  : Rs {total_at_risk:,.2f}")

    print("\nFailure distribution:")

    counts = {}

    for transaction in transactions:
        reason = transaction["failure_reason_code"]
        counts[reason] = counts.get(reason, 0) + 1

    for reason, count in sorted(counts.items()):
        print(f"  {reason:20s}: {count}")

    print("\nFiles written:")
    print("  data/customers.csv")
    print("  data/transactions.csv")