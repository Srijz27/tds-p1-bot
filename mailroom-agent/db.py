import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "mailroom.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS dossier_cache (
            fingerprint TEXT PRIMARY KEY,
            decision TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            eval_id TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS receipts (
            receipt_key TEXT PRIMARY KEY,
            outcome TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()


def get_cached_decision(fp):
    conn = get_connection()
    row = conn.execute(
        "SELECT decision, payload FROM dossier_cache WHERE fingerprint = ?",
        (fp,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_decision(fp, decision):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO dossier_cache (fingerprint, decision, payload) VALUES (?, ?, ?)",
        (fp, decision["decision"], str(decision)),
    )
    conn.commit()
    conn.close()


def get_evaluation(eval_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT eval_id, fingerprint, response FROM evaluations WHERE eval_id = ?",
        (eval_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_evaluation(eval_id, fp, response):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO evaluations (eval_id, fingerprint, response) VALUES (?, ?, ?)",
        (eval_id, fp, str(response)),
    )
    conn.commit()
    conn.close()


def get_receipt(key):
    conn = get_connection()
    row = conn.execute(
        "SELECT receipt_key, outcome FROM receipts WHERE receipt_key = ?",
        (key,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_receipt(key, outcome):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO receipts (receipt_key, outcome) VALUES (?, ?)",
        (key, str(outcome)),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Initialized database:", DB_PATH)
    conn = get_connection()
    print(conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall())
    conn.close()
