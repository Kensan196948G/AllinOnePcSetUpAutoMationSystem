from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.database import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def update_admin_role():
    db = SessionLocal()
    try:
        db.execute(text("UPDATE users SET role = 'admin' WHERE username = 'admin'"))
        db.commit()
        print("Adminユーザーのroleを'admin'に更新しました。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_admin_role()