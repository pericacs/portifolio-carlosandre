"""Read-only consistent PostgreSQL snapshot and verified media copy. Never prints data."""
import argparse
import hashlib
import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID
import sqlalchemy as sa
from app.models import metadata
from app.db import get_engine

def encode(value):
    if isinstance(value, (datetime, date)): return value.isoformat()
    if isinstance(value, UUID): return str(value)
    raise TypeError(type(value).__name__)

def export(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    with get_engine().connect().execution_options(isolation_level='REPEATABLE READ') as connection:
        with connection.begin():
            connection.execute(sa.text('SET TRANSACTION READ ONLY'))
            rows = {table.name:[dict(r) for r in connection.execute(sa.select(table)).mappings()] for table in metadata.sorted_tables}
            revision = connection.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one()
            media=[]
            for asset in rows['media_assets']:
                key=asset['storage_key']
                if Path(key).name != key: raise ValueError('Unsafe storage key')
                source=Path('/app/uploads')/key
                if not source.is_file():
                    if asset['archived_at']: continue
                    raise ValueError('Active media missing; snapshot aborted')
                raw=source.read_bytes()
                if hashlib.sha256(raw).hexdigest()!=asset['sha256']: raise ValueError('Media hash mismatch')
                target=destination/'media'/key
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(raw)
                media.append({'key':key,'sha256':asset['sha256'],'size':len(raw)})
            raw=json.dumps(rows,default=encode,ensure_ascii=False,sort_keys=True).encode()
            (destination/'snapshot.json').write_bytes(raw)
            manifest={'format':1,'revision':revision,'created_at':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(raw).hexdigest(),'counts':{name:len(items) for name,items in rows.items()},'media':media}
            (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Read-only export complete; tables:',len(rows),'media:',len(media))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('destination'); export(parser.parse_args().destination)
