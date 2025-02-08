from database import Base, engine, SessionLocal
from models import User

def init_db():
    # データベースのテーブルを作成
    Base.metadata.create_all(bind=engine)
    
    # 管理者ユーザーを作成
    db = SessionLocal()
    try:
        # 既存の管理者ユーザーを確認
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin_user = User(
                username="admin",
                email="admin@example.com",
                role="admin"
            )
            admin_user.hashed_password = User.get_password_hash("adminpassword")
            db.add(admin_user)
            db.commit()
            print("管理者ユーザーを作成しました")
        else:
            print("管理者ユーザーは既に存在します")
    finally:
        db.close()

if __name__ == "__main__":
    print("データベースを初期化します...")
    init_db()
    print("データベースの初期化が完了しました")