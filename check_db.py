import asyncio
from app.core.database import engine
from app.models.historial_lectura import HistorialLectura
from sqlalchemy import select, func
from datetime import date

async def main():
    async with engine.connect() as conn:
        print("--- Last 5 records ---")
        res = await conn.execute(select(HistorialLectura).limit(5))
        for row in res.fetchall():
            print(row)
            
        today = date.today()
        print(f"\n--- Checking for today: {today} ---")
        res = await conn.execute(select(HistorialLectura).where(HistorialLectura.fecha == today))
        rows = res.fetchall()
        print(f"Found {len(rows)} records for today.")
        for row in rows:
            print(row)

        print("\n--- Count by date ---")
        res = await conn.execute(select(HistorialLectura.fecha, func.count(HistorialLectura.id_lectura)).group_by(HistorialLectura.fecha).order_by(HistorialLectura.fecha.desc()))
        for row in res.fetchall():
            print(f"Date: {row[0]}, Count: {row[1]}")

        print("\n--- All completed records ---")
        res = await conn.execute(select(HistorialLectura).where(HistorialLectura.status == "completado"))
        rows = res.fetchall()
        print(f"Found {len(rows)} completed records in total.")
        for row in rows:
            print(row)

if __name__ == "__main__":
    asyncio.run(main())
