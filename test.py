import sqlite3
import os

DB_FILE = "app.db"

def inspect_database():
    if not os.path.exists(DB_FILE):
        print(f"❌ Database file '{DB_FILE}' does not exist yet.")
        print("💡 Run main.py and register a user to initialize the database.")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Fetch all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall() if row["name"] != "sqlite_sequence"]

    print("=" * 60)
    print(f"      DATABASE INSPECTION REPORT: '{DB_FILE}'")
    print("=" * 60)
    print(f"Found Tables: {tables}\n")

    if not tables:
        print("⚠️ No user-created tables found in the database.")
        conn.close()
        return

    # 2. Inspect each table
    for table in tables:
        print(f"------------------------------------------------------------")
        print(f"📋 TABLE: {table}")
        print(f"------------------------------------------------------------")

        # Get Schema
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        print("Columns:")
        for col in columns:
            print(f"  - {col['name']} ({col['type']}) {'[PK]' if col['pk'] else ''}")

        # Get Row Count
        cursor.execute(f"SELECT COUNT(*) AS total FROM {table}")
        count = cursor.fetchone()["total"]
        print(f"\nTotal Records: {count}\n")

        # Get All Records
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()

        if rows:
            print("Data Rows:")
            for row in rows:
                row_dict = dict(row)
                # Mask hashed password for clean console output
                if "hashed_password" in row_dict:
                    pwd = row_dict["hashed_password"]
                    row_dict["hashed_password"] = f"{pwd[:12]}... (truncated)"
                
                print(f"  {row_dict}")
        else:
            print("  (Table is currently empty)")

        print("\n")

    conn.close()

if __name__ == "__main__":
    inspect_database()
