from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from config import get_config

# This script adds history columns to the Chamado table if they don't exist.
# Run: python scripts/add_chamado_history_columns.py

def get_engine():
    cfg = get_config()
    uri = getattr(cfg, 'SQLALCHEMY_DATABASE_URI', None) or getattr(cfg, 'DATABASE_URI', None)
    if not uri:
        raise RuntimeError('DATABASE URI not found in config')
    return create_engine(uri)

COLUMNS = [
    ('status_assumido_por_id', 'INTEGER'),
    ('status_assumido_em', 'DATETIME'),
    ('concluido_por_id', 'INTEGER'),
    ('concluido_em', 'DATETIME'),
    ('cancelado_por_id', 'INTEGER'),
    ('cancelado_em', 'DATETIME'),
]

ALTERS = [
    "ALTER TABLE chamado ADD COLUMN status_assumido_por_id INTEGER",
    "ALTER TABLE chamado ADD COLUMN status_assumido_em DATETIME",
    "ALTER TABLE chamado ADD COLUMN concluido_por_id INTEGER",
    "ALTER TABLE chamado ADD COLUMN concluido_em DATETIME",
    "ALTER TABLE chamado ADD COLUMN cancelado_por_id INTEGER",
    "ALTER TABLE chamado ADD COLUMN cancelado_em DATETIME",
]

def column_exists(inspector, table, column):
    for col in inspector.get_columns(table):
        if col['name'] == column:
            return True
    return False

if __name__ == '__main__':
    engine = get_engine()
    insp = inspect(engine)

    if not insp.has_table('chamado'):
        raise RuntimeError('Table "chamado" does not exist. Run the app to create tables first.')

    with engine.begin() as conn:
        for (name, _), stmt in zip(COLUMNS, ALTERS):
            try:
                if not column_exists(insp, 'chamado', name):
                    conn.execute(text(stmt))
                    print(f"Added column: {name}")
                else:
                    print(f"Column exists: {name}")
            except SQLAlchemyError as e:
                print(f"Error adding column {name}: {e}")
    print('Done.')
