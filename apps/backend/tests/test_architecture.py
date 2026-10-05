import ast
from pathlib import Path


def test_inner_layers_do_not_import_frameworks_or_adapters():
    root = Path(__file__).parents[1] / "src" / "homate" / "modules" / "catalog"
    for file, allowed in [("domain.py", {"zoneinfo"}), ("application.py", {"typing", "uuid", "homate.modules.catalog.domain"})]:
        tree = ast.parse((root / file).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module in allowed, f"Unexpected dependency in {file}: {node.module}"
            elif isinstance(node, ast.Import):
                assert all(alias.name in allowed for alias in node.names)


def test_software_inner_layers_have_no_transport_or_database_dependency():
    root = Path(__file__).parents[1] / "src" / "homate"
    files = list((root / "application").glob("*.py"))
    files += [file for file in (root / "modules").rglob("*.py")
              if "domain" in file.parts or "application" in file.parts]
    forbidden = ("fastapi", "sqlalchemy", "psycopg", "sqlite3", "homate.infrastructure", "homate.presentation")
    for file in files:
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            modules = [node.module or ""] if isinstance(node, ast.ImportFrom) else (
                [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
            assert not any(module == prefix or module.startswith(prefix + ".")
                           for module in modules for prefix in forbidden), str(file)
