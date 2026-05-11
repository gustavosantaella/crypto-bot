import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def check_db():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "3306"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASS", ""),
            database=os.getenv("DB_NAME", "crypto-bot")
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades")
        count = cursor.fetchone()[0]
        print(f"Total trades: {count}")
        
        cursor.execute("SELECT id, side, trade_type, message FROM trades LIMIT 5")
        rows = cursor.fetchall()
        for r in rows:
            print(r)
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
