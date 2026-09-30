import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.dependencies import get_db
from app.main import app


TEST_DATABASE_URL = (
    "postgresql+psycopg://kifaru:kifaru_dev_password@localhost:5432/kifaru"
)

engine = create_engine(TEST_DATABASE_URL)

TestingSession = sessionmaker(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()

    session = TestingSession(bind=connection)

    app.dependency_overrides[get_db] = lambda: session

    try:
        yield session
    finally:
        app.dependency_overrides.clear()

        session.close()

        if transaction.is_active:
            transaction.rollback()

        connection.close()