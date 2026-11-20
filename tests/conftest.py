"""Pytest Configuration and Shared Fixtures."""

import os
from pathlib import Path
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine

from src.db.connection import DatabaseManager
from src.db.seed import seed_database
from src.db.schema import DatabaseInspector
from src.security.ast_validator import ASTSQLValidator
from src.security.nemo_guard import NeMoInputGuard


@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    """Create a temporary SQLite database for testing."""
    tmp_dir = tmp_path_factory.mktemp("test_db")
    db_file = tmp_dir / "test_analytics.db"
    db_url = f"sqlite:///{db_file}"
    
    db_manager = DatabaseManager(database_url=db_url)
    seed_database(db_manager, force=True)
    
    yield db_url
    
    db_manager.close()


@pytest.fixture
def db_manager(test_db_path):
    """Return DatabaseManager connected to test database."""
    return DatabaseManager(database_url=test_db_path)


@pytest.fixture
def db_inspector(db_manager):
    """Return DatabaseInspector connected to test database."""
    return DatabaseInspector(db_manager=db_manager)


@pytest.fixture
def ast_validator():
    """Return ASTSQLValidator instance."""
    return ASTSQLValidator()


@pytest.fixture
def nemo_guard():
    """Return NeMoInputGuard instance."""
    return NeMoInputGuard()
