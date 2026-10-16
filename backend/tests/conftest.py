import pytest
from app.db import get_engine


@pytest.fixture
def db():
    # Cada teste usa uma transação revertida; não apaga nem recria o banco.
    with get_engine().connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()
