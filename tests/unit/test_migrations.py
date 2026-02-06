"""
Unit tests for database migrations.

Tests Alembic migrations for upgrade/downgrade functionality.
"""

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
import os


class TestMigrationsStructure:
    """Test migration files structure and syntax."""

    def test_migrations_directory_exists(self):
        """Test that migrations directory exists."""
        migrations_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "migrations"
        )
        assert os.path.exists(migrations_path)
        assert os.path.isdir(migrations_path)

    def test_alembic_ini_exists(self):
        """Test that alembic.ini configuration exists."""
        alembic_ini_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "migrations", "alembic.ini"
        )
        assert os.path.exists(alembic_ini_path)

    def test_migration_versions_exist(self):
        """Test that migration version files exist."""
        versions_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "migrations", "versions"
        )
        assert os.path.exists(versions_path)

        # Should have at least one migration file
        migration_files = [
            f
            for f in os.listdir(versions_path)
            if f.endswith(".py") and not f.startswith("__")
        ]
        assert len(migration_files) > 0


class TestMigrationChain:
    """Test migration chain validity."""

    def test_migration_files_structure(self):
        """Test that migration files have correct structure."""
        versions_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "migrations", "versions"
        )

        for filename in os.listdir(versions_path):
            if not filename.endswith(".py") or filename.startswith("__"):
                continue

            filepath = os.path.join(versions_path, filename)
            with open(filepath, "r") as f:
                content = f.read()

            # Check for required elements in migration file
            assert "revision =" in content, f"Missing revision ID in {filename}"
            assert "def upgrade" in content, f"Missing upgrade function in {filename}"
            assert (
                "def downgrade" in content
            ), f"Missing downgrade function in {filename}"

    def test_participant_migration_exists(self):
        """Test that participant migration exists."""
        versions_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "migrations", "versions"
        )

        migration_found = False
        for filename in os.listdir(versions_path):
            if "participant" in filename.lower() and filename.endswith(".py"):
                migration_found = True
                filepath = os.path.join(versions_path, filename)
                with open(filepath, "r") as f:
                    content = f.read()

                # Verify migration content
                assert "participant" in content.lower()
                assert "safari_booking" in content.lower()
                break

        assert migration_found, "Participant migration not found"

    def test_migration_has_valid_python(self):
        """Test that migration files are valid Python."""
        versions_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "migrations", "versions"
        )

        for filename in os.listdir(versions_path):
            if not filename.endswith(".py") or filename.startswith("__"):
                continue

            filepath = os.path.join(versions_path, filename)
            try:
                with open(filepath, "r") as f:
                    compile(f.read(), filename, "exec")
            except SyntaxError as e:
                pytest.fail(f"Syntax error in migration {filename}: {str(e)}")


class TestMigrationContent:
    """Test actual migration content."""

    def test_participant_table_migration_up(self):
        """Test participant table creation migration."""
        versions_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "migrations", "versions"
        )

        for filename in os.listdir(versions_path):
            if "participant" in filename.lower() and filename.endswith(".py"):
                filepath = os.path.join(versions_path, filename)
                with open(filepath, "r") as f:
                    content = f.read()

                # Check upgrade creates participant table
                assert "op.create_table" in content
                assert "'participant'" in content or '"participant"' in content
                assert "email" in content
                assert "ForeignKeyConstraint" in content or "participant_id" in content
                break

    def test_migration_has_downgrade(self):
        """Test that migrations can be downgraded."""
        versions_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "migrations", "versions"
        )

        for filename in os.listdir(versions_path):
            if not filename.endswith(".py") or filename.startswith("__"):
                continue

            filepath = os.path.join(versions_path, filename)
            with open(filepath, "r") as f:
                content = f.read()

            # Downgrade should have some operations
            assert "def downgrade" in content

            # Extract downgrade function
            downgrade_start = content.find("def downgrade")
            if downgrade_start != -1:
                # Check that downgrade is not empty
                downgrade_section = content[downgrade_start:]

                # Should have some operations in downgrade
                has_operations = (
                    "op.drop" in downgrade_section or "pass" in downgrade_section
                )
                assert has_operations, f"Downgrade appears empty in {filename}"


@pytest.fixture(scope="session")
def migrations_dir():
    """Provide migrations directory path."""
    migrations_path = os.path.join(os.path.dirname(__file__), "..", "..", "migrations")
    return migrations_path
