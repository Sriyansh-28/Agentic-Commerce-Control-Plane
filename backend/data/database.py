import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(
    r"E:\Resumes\Razorpay\agentic-commerce-control-plane"
)

DATABASE_PATH = PROJECT_ROOT / "backend" / "data" / "agentguard.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                authority_id TEXT NOT NULL,
                action TEXT NOT NULL,
                product_id TEXT NOT NULL,
                merchant_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                state TEXT NOT NULL,
                razorpay_order_id TEXT,
                razorpay_payment_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                state TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.commit()

    finally:
        connection.close()