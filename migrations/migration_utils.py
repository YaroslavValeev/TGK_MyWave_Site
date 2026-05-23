"""Helpers for idempotent Alembic upgrades on legacy prod DBs."""


def table_names(connection) -> set[str]:
    from sqlalchemy import inspect

    return set(inspect(connection).get_table_names())


def column_names(connection, table: str) -> set[str]:
    from sqlalchemy import inspect

    if table not in table_names(connection):
        return set()
    return {col["name"] for col in inspect(connection).get_columns(table)}


def has_unique_constraint(connection, table: str, name: str) -> bool:
    from sqlalchemy import inspect

    if table not in table_names(connection):
        return False
    for uc in inspect(connection).get_unique_constraints(table):
        if uc.get("name") == name:
            return True
    return False
