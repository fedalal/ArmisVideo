from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from settings import settings

# создаём движок SQLAlchemy для PostgreSQL
engine = create_engine(
    settings.POSTGRES_DSN,
    echo=False,           # для отладки SQL-запросов
    future=True           # использование SQLAlchemy 2.0 style
)

# базовый класс для моделей
Base = declarative_base()

# фабрика сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True
)

# вспомогательная функция для использования с контекстом
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# при первом запуске создаются все таблицы, если их нет
def init_db():
    Base.metadata.create_all(bind=engine)

# вызываем инициализацию базы при старте приложения
init_db()
