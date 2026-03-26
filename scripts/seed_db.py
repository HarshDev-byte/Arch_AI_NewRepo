"""Database seeder – populates demo data."""
import sys
sys.path.insert(0, "../backend")

from database import engine, Base, SessionLocal

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    print("Database tables created. Add seed data here.")
    db.close()

if __name__ == "__main__":
    seed()
