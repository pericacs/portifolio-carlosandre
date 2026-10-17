"""Generate an additive SQLite/D1 schema from the existing metadata (no database access)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
import sqlalchemy as sa
from app.models import metadata

def schema():
    statements = ['PRAGMA foreign_keys = ON;']
    for table in metadata.sorted_tables:
        parts = []
        for c in table.columns:
            kind = 'INTEGER' if isinstance(c.type, (sa.Integer, sa.Boolean)) else 'REAL' if isinstance(c.type, (sa.Float, sa.Numeric)) else 'TEXT'
            line = f'"{c.name}" {kind}'
            if c.primary_key: line += ' PRIMARY KEY'
            if not c.nullable: line += ' NOT NULL'
            if c.name == 'id': line += " DEFAULT (lower(hex(randomblob(16))))"
            elif c.server_default is not None:
                value = str(c.server_default.arg)
                if value == 'now()': value = "(strftime('%Y-%m-%dT%H:%M:%fZ','now'))"
                elif '::jsonb' in value: value = value.replace('::jsonb', '')
                elif value.lower() in ('true', 'false'): value = '1' if value.lower() == 'true' else '0'
                elif value not in ('0', '1') and not value.startswith(("'", '(')): value = "'" + value.replace("'", "''") + "'"
                line += ' DEFAULT ' + value
            parts.append(line)
        for constraint in table.constraints:
            if isinstance(constraint, sa.UniqueConstraint):
                parts.append('UNIQUE (' + ','.join('"'+c.name+'"' for c in constraint.columns) + ')')
            if isinstance(constraint, sa.CheckConstraint):
                check = str(constraint.sqltext)
                if '~' not in check and '::' not in check: parts.append('CHECK ('+check+')')
        for fk in table.foreign_keys:
            parts.append(f'FOREIGN KEY ("{fk.parent.name}") REFERENCES "{fk.column.table.name}" ("{fk.column.name}") ON DELETE RESTRICT')
        statements.append(f'CREATE TABLE IF NOT EXISTS "{table.name}" (\n  ' + ',\n  '.join(parts) + '\n);')
        for index in table.indexes:
            columns = ','.join('"'+c.name+'"' for c in index.columns)
            statements.append(f'CREATE {"UNIQUE " if index.unique else ""}INDEX IF NOT EXISTS "{index.name}" ON "{table.name}" ({columns});')
    statements += [
        'CREATE TABLE IF NOT EXISTS migration_receipts (snapshot_id TEXT PRIMARY KEY, imported_at TEXT NOT NULL, manifest TEXT NOT NULL);',
        'ALTER TABLE contact_notifications ADD COLUMN lease_until TEXT;',
        'ALTER TABLE contact_notifications ADD COLUMN provider_id TEXT;',
        'ALTER TABLE contact_notifications ADD COLUMN last_error TEXT;',
        'ALTER TABLE contact_tickets ADD COLUMN message_id TEXT;',
        'CREATE INDEX IF NOT EXISTS ix_cms_refs_public ON cms_media_refs(media_id,scope);',
        'CREATE INDEX IF NOT EXISTS ix_cms_public ON cms_entries(module,deleted_at,status);',
    ]
    return '\n\n'.join(statements)+'\n'

if __name__ == '__main__':
    path = Path(__file__).resolve().parents[2]/'frontend/cloudflare/migrations/0001_portfolio.sql'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(schema(),encoding='utf-8',newline='\n')
