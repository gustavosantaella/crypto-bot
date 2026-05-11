from src.utils.db import engine
from sqlalchemy import text

def add_column():
    try:
        with engine.connect() as conn:
            conn.execute(text('ALTER TABLE trades ADD COLUMN message VARCHAR(255) AFTER trade_type'))
            conn.commit()
            print("Columna 'message' añadida exitosamente.")
    except Exception as e:
        print(f"Error o columna ya existe: {e}")

if __name__ == "__main__":
    add_column()
