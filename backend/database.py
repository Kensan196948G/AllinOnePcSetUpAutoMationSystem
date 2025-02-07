from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# データベースファイルのパスを設定
DATABASE_URL = f"sqlite:///{Path(__file__).parent.parent}/data.db"

# SQLAlchemyエンジンを作成
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# セッションファクトリを作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデルのベースクラスを作成
Base = declarative_base()

# 依存性注入のためのセッション取得関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()