import sqlalchemy
from app.db.session import engine

def add_index():
    with engine.connect() as conn:
        try:
            print("Intentando agregar indice a price_logs(timestamp)...")
            # En SQLAlchemy 2.0 se usa text()
            conn.execute(sqlalchemy.text("ALTER TABLE price_logs ADD INDEX ix_price_logs_timestamp (timestamp)"))
            print("Indice agregado exitosamente.")
        except Exception as e:
            if "Duplicate key name" in str(e) or "already exists" in str(e).lower():
                print("El indice ya existe o la tabla ya lo tiene.")
            else:
                print(f"Error al agregar indice: {e}")

if __name__ == "__main__":
    add_index()
