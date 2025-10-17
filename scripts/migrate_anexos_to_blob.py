#!/usr/bin/env python3
"""
Script to add the `arquivo_blob` column to `anexos_arquivos` (if missing) and migrate files from disk
into the database column. Designed to run against the app database (works with MySQL, PostgreSQL, SQLite).

Run:
    python scripts/migrate_anexos_to_blob.py

The script will:
- Add the arquivo_blob column (appropriate type per dialect) if it doesn't exist
- Find rows where caminho_arquivo IS NOT NULL and arquivo_blob IS NULL
- Read the file from disk (path is relative to project root) and store its bytes into arquivo_blob
- Update tamanho_bytes and mime_type when possible; set caminho_arquivo to NULL after successful migration

Make a DB backup before running in production.
"""

import os
import sys
import mimetypes
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from config import get_config


def get_engine():
    cfg = get_config()
    uri = getattr(cfg, 'SQLALCHEMY_DATABASE_URI', None) or getattr(cfg, 'DATABASE_URI', None)
    if not uri:
        raise RuntimeError('DATABASE URI not found in config')
    return create_engine(uri)


def add_blob_column_if_missing(engine, inspector):
    table = 'anexos_arquivos'
    cols = [c['name'] for c in inspector.get_columns(table)]
    if 'arquivo_blob' in cols:
        print('Column arquivo_blob already exists')
        return

    dialect = engine.dialect.name
    if dialect == 'postgresql':
        col_type = 'BYTEA'
    elif dialect in ('mysql', 'mariadb'):
        col_type = 'LONGBLOB'
    else:
        # sqlite and others
        col_type = 'BLOB'

    alter = f"ALTER TABLE {table} ADD COLUMN arquivo_blob {col_type}"
    print('Adding column arquivo_blob with type', col_type)
    with engine.begin() as conn:
        conn.execute(text(alter))
    print('Column added')


def migrate_files_to_blob(engine, inspector, dry_run=False):
    table = 'anexos_arquivos'
    cols = [c['name'] for c in inspector.get_columns(table)]
    if 'caminho_arquivo' not in cols:
        print('Table does not have caminho_arquivo column; nothing to migrate')
        return

    # Select rows that have caminho_arquivo and no arquivo_blob
    sel_sql = text(f"SELECT id, caminho_arquivo, nome_original FROM {table} WHERE caminho_arquivo IS NOT NULL AND (arquivo_blob IS NULL OR arquivo_blob = '')")
    migrated = 0
    skipped = 0
    failed = 0

    with engine.begin() as conn:
        results = conn.execute(sel_sql).fetchall()
        print(f'Found {len(results)} rows to consider')
        for row in results:
            anexo_id = row[0]
            caminho = row[1]
            nome = row[2] or ''
            if not caminho:
                skipped += 1
                continue

            # Normalizar caminho e localizar arquivo em disco
            # Remove leading slash if present
            rel_path = caminho.lstrip('/')
            file_path = os.path.normpath(os.path.join(os.getcwd(), rel_path))

            if not os.path.exists(file_path):
                print(f'WARNING: file not found for anexo.id={anexo_id}: {file_path} (nome={nome})')
                skipped += 1
                continue

            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                tamanho = len(data)
                mime, _ = mimetypes.guess_type(nome or file_path)
                mime = mime or 'application/octet-stream'

                if dry_run:
                    print(f'[dry-run] Would update id={anexo_id} size={tamanho} mime={mime}')
                    migrated += 1
                    continue

                upd_sql = text(f"UPDATE {table} SET arquivo_blob = :blob, caminho_arquivo = NULL, tamanho_bytes = :tamanho, mime_type = :mime WHERE id = :id")
                conn.execute(upd_sql, {'blob': data, 'tamanho': tamanho, 'mime': mime, 'id': anexo_id})

                # Optionally remove the file from disk after successful migration
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f'Notice: could not remove file {file_path}: {e}')

                migrated += 1
                print(f'Migrated anexo.id={anexo_id} ({nome})')

            except Exception as e:
                print(f'Error migrating anexo.id={anexo_id}: {e}')
                failed += 1

    print('\nSummary:')
    print('  migrated:', migrated)
    print('  skipped:', skipped)
    print('  failed :', failed)


if __name__ == '__main__':
    engine = get_engine()
    insp = inspect(engine)

    # Sanity checks
    if not insp.has_table('anexos_arquivos'):
        print('ERROR: Table anexos_arquivos does not exist. Ensure you are pointing to the correct database and that the app has created tables.')
        sys.exit(1)

    try:
        add_blob_column_if_missing(engine, insp)
    except SQLAlchemyError as e:
        print('Error while adding column:', e)
        sys.exit(1)

    # Allow optional dry-run flag
    dry = '--dry-run' in sys.argv or '-n' in sys.argv
    if dry:
        print('Running in dry-run mode; no changes will be written')

    migrate_files_to_blob(engine, insp, dry_run=dry)

    print('Done.')
