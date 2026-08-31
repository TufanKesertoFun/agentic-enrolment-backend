import importlib.util
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_sees_authentication_schema_head() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    assert script.get_current_head() == "20260901_0003"


def test_core_domain_schema_migration_imports() -> None:
    migration_path = Path("migrations/versions/20260831_0002_core_domain_schema.py")
    spec = importlib.util.spec_from_file_location("core_domain_schema", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "20260831_0002"
    assert module.down_revision == "20260831_0001"


def test_authentication_schema_migration_imports() -> None:
    migration_path = Path("migrations/versions/20260901_0003_add_user_password_hash.py")
    spec = importlib.util.spec_from_file_location("authentication_schema", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "20260901_0003"
    assert module.down_revision == "20260831_0002"