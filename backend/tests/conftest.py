import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.organization.models import Tenant


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

    try:
        yield session
    finally:
        session.close()

        if transaction.is_active:
            transaction.rollback()

        connection.close()



