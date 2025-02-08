from backend.database import engine, Base
from backend.models import User, ComputerInfoDB, SetupOptionsDB, SetupRequestDB, SetupProgressDB

def init_db():
    Base.metadata.create_all(bind=engine)
    print("データベースの初期化が完了しました。")

if __name__ == "__main__":
    init_db()