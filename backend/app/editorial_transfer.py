"""Offline package verification and explicit, guarded editorial import. No schema migrations.

Database connections are made ONLY by plan/apply/rollback CLI commands, never on import
or verify. Production writes require a bound reviewed plan and explicit confirmation.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

if not __package__:
    sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path.cwd())]
import sqlalchemy as sa
from app.models import metadata

EXCLUDED = {'admin_users','admin_sessions','password_resets','auth_rate_limits','audit_logs','contact_messages','contact_notifications','contact_tickets'}
TABLES = [t for t in metadata.sorted_tables if t.name not in EXCLUDED]
NAMES = {t.name for t in TABLES}
AUTH_COLUMNS = {t.name:{fk.parent.name for fk in t.foreign_keys if fk.column.table.name=='admin_users'} for t in TABLES}
RECEIPT_PREFIX = 'editorial_import:'

class Conflict(Exception): pass

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=lambda v:v.isoformat() if isinstance(v,(date,datetime)) else str(v))

def digest(value): return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def normalize_row(table,row):
    out=dict(row)
    for column in table.columns:
        v=out.get(column.name)
        if v is None:continue
        if isinstance(column.type,sa.DateTime):out[column.name]=datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc).isoformat(timespec='microseconds')
        elif isinstance(column.type,sa.Date):out[column.name]=str(v)[:10]
        elif isinstance(column.type,sa.UUID):out[column.name]=str(uuid.UUID(str(v)))
    return out

def state_hash(state):
    return digest({t.name:sorted((normalize_row(t,r) for r in state[t.name]),key=lambda r:r['id']) for t in TABLES})

def write_private(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)

def verify(directory):
    directory=Path(directory).resolve()
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format_version')!=1:raise Conflict('Unsupported package format')
    if set(manifest.get('excluded_tables',[]))!=EXCLUDED:raise Conflict('Excluded table policy mismatch')
    expected_files=set(manifest['files'])
    actual_files={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    if actual_files!=expected_files|{'manifest.json','SHA256SUMS'}:raise Conflict('Unexpected or missing package file')
    if any(p.is_symlink() for p in directory.rglob('*')):raise Conflict('Symlinks are forbidden')
    for name,info in manifest['files'].items():
        p=(directory/name).resolve()
        if not p.is_relative_to(directory) or not p.is_file() or p.stat().st_size!=info['bytes'] or file_hash(p)!=info['sha256']:raise Conflict('Package checksum mismatch: '+name)
    checks={}
    for line in (directory/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        h,name=line.split('  ',1)
        if name in checks:raise Conflict('Duplicate checksum')
        checks[name]=h
    if set(checks)!=expected_files|{'manifest.json'}:raise Conflict('Checksum catalog mismatch')
    for name,h in checks.items():
        p=(directory/name).resolve()
        if not p.is_relative_to(directory) or file_hash(p)!=h:raise Conflict('Checksum mismatch')
    if manifest['package_id']!=digest({k:v for k,v in manifest.items() if k!='package_id'}):raise Conflict('Package identity mismatch')
    data=json.loads((directory/'editorial.json').read_text(encoding='utf-8'))
    rows=data['rows']
    if set(rows)!=NAMES:raise Conflict('Unexpected editorial tables')
    for table in TABLES:
        ids=set()
        for row in rows[table.name]:
            if set(row)!={c.name for c in table.columns}:raise Conflict('Unexpected columns in '+table.name)
            if row['id'] in ids:raise Conflict('Duplicate primary key')
            uuid.UUID(row['id']);ids.add(row['id'])
            normalize_row(table,row)
            if any(row[k] is not None for k in AUTH_COLUMNS[table.name]):raise Conflict('Local administrative identity in package')
            for c in table.columns:
                if row[c.name] is None and not c.nullable:raise Conflict('Required field missing')
        for constraint in table.constraints:
            if isinstance(constraint,sa.UniqueConstraint):
                seen=set()
                for row in rows[table.name]:
                    key=tuple(row[c.name] for c in constraint.columns)
                    if None in key:continue
                    if key in seen:raise Conflict('Duplicate natural key in '+table.name)
                    seen.add(key)
    for table in TABLES:
        for fk in table.foreign_keys:
            if fk.column.table.name=='admin_users':continue
            known={r[fk.column.name] for r in rows[fk.column.table.name]}
            if any(r[fk.parent.name] is not None and r[fk.parent.name] not in known for r in rows[table.name]):raise Conflict('Broken foreign key in '+table.name)
    if any(r['key']!='cms_initialized' for r in rows['site_settings']):raise Conflict('Non-editorial setting in package')
    if len(rows['cms_entries'])!=122 or len(rows['media_assets'])!=28:raise Conflict('Audited counts changed')
    modules={}
    for r in rows['cms_entries']:
        if r['status'] not in {'draft','published','archived','scheduled'} or r['version']<1:raise Conflict('Invalid editorial state')
        if r['status']=='published' and r['published_data'] is None:raise Conflict('Published snapshot missing')
        if r['status']=='scheduled' and (r['scheduled_data'] is None or r['scheduled_at'] is None):raise Conflict('Scheduled snapshot missing')
        modules[r['module']]=modules.get(r['module'],0)+1
    if modules!=manifest['modules']:raise Conflict('Module counts differ')
    if {t:len(v) for t,v in rows.items()}!=manifest['counts']:raise Conflict('Table counts differ')
    for asset in rows['media_assets']:
        key=asset['storage_key']
        if not re.fullmatch(r'[a-f0-9-]{36}\.(png|webp|jpg|jpeg|pdf|docx)',key):raise Conflict('Unsafe media key')
        if key.rsplit('.',1)[0]!=asset['id']:raise Conflict('Media key/UUID mismatch')
        p=directory/'media'/key
        if file_hash(p)!=asset['sha256'] or p.stat().st_size!=asset['size_bytes']:raise Conflict('Media metadata mismatch')
    if {p.name for p in (directory/'media').iterdir()}!={r['storage_key'] for r in rows['media_assets']}:raise Conflict('Unexpected media')
    # Detect direct credential fields/PEM/known authentication hashes. Editorial drafts
    # and professional contact details remain private and require human review.
    raw=canonical(rows)
    if re.search(r'\$argon2(?:id|i|d)\$|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|"(?:password_hash|token_hash|csrf_hash|smtp_password|session_token|access_token|api_key)"\s*:',raw,re.I):raise Conflict('Credential marker in editorial payload')
    baseline=json.loads((directory/'baseline.json').read_text(encoding='utf-8'))
    if len(baseline)!=117 or len({r['source_key'] for r in baseline})!=117:raise Conflict('Invalid initial baseline')
    return directory,manifest,data,baseline

def normalized_data(module,data):
    from app.cms_schema import validate
    v=validate(module,data)
    v.update({k:x for k,x in data.items() if k not in v})
    return v

def initial_rows(baseline):
    ids={r['source_key']:str(uuid.uuid5(uuid.NAMESPACE_URL,'portfolio-cms:'+r['source_key'])) for r in baseline}
    result={}
    for seed in baseline:
        d=dict(seed['data'])
        for k,v in d.items():
            if isinstance(v,str) and v.startswith('SOURCE:'):d[k]=ids[v[7:]]
        # Match app.import_cms exactly: schema validation drops legacy source-only
        # keys, except the explicitly retained _legacy field. Retaining every raw
        # key here falsely rejects genuine untouched PostgreSQL seeds.
        from app.cms_schema import validate
        validated=validate(seed['module'],d)
        if '_legacy' in d:validated['_legacy']=d['_legacy']
        result[ids[seed['source_key']]]={**seed,'data':validated}
    return result

def pristine(row,baseline):
    seed=baseline.get(row['id'])
    return bool(seed and row['source_key']==seed['source_key'] and row['module']==seed['module'] and row['slug']==seed['data'].get('slug','main') and row['title']==seed['data']['title'] and row['version']==1 and row['status']=='draft' and row['editor_id'] is None and all(row[k] is None for k in ['published_data','scheduled_data','published_at','scheduled_at','deleted_at']) and normalized_data(row['module'],row['data'])==seed['data'])

def build_plan(state,rows,baseline):
    """Pure planning: rejects divergent target state. Does not execute SQL."""
    seeds=initial_rows(baseline)
    target_entries={r['id']:r for r in state['cms_entries']}
    pristine_ids={key for key,r in target_entries.items() if pristine(r,seeds)}
    source_entries={r['id'] for r in rows['cms_entries']}
    for name,keys in [('cms_links',('entry_id','target_id','scope')),('cms_media_refs',('entry_id','media_id','scope'))]:
        desired={tuple(r[k] for k in keys) for r in rows[name]}
        if any(r['entry_id'] in source_entries and tuple(r[k] for k in keys) not in desired for r in state[name]):raise Conflict('Unexpected destination references: '+name)
    operations=[]
    for table in TABLES:
        existing={r['id']:r for r in state[table.name]}
        unique=[tuple(c.name for c in constraint.columns) for constraint in table.constraints if isinstance(constraint,sa.UniqueConstraint)]
        for row in rows[table.name]:
            same=existing.get(row['id'])
            collisions=[old for old in existing.values() if old['id']!=row['id'] and any(all(row[k] is not None for k in keys) and all(old[k]==row[k] for k in keys) for keys in unique)]
            if len(collisions)>1:raise Conflict('Ambiguous natural key in '+table.name)
            old=same or (collisions[0] if collisions else None)
            if same and collisions:raise Conflict('Natural/primary key collision in '+table.name)
            if old and normalize_row(table,old)==normalize_row(table,row):continue
            permitted=False
            if old:
                if table.name=='cms_entries':permitted=old['id'] in pristine_ids and old['id']==row['id']
                elif table.name=='cms_revisions':
                    seed=seeds.get(old['entry_id'])
                    permitted=bool(seed and old['entry_id'] in pristine_ids and old['version']==row['version']==1 and old['action']==row['action']=='import' and old['editor_id'] is None and normalized_data(seed['module'],old['snapshot'])==seed['data'])
                elif table.name in {'cms_links','cms_media_refs'}:permitted=old['entry_id'] in pristine_ids
                elif table.name=='site_settings':permitted=old['key']==row['key']=='cms_initialized' and old['value']==row['value']
                if not permitted:raise Conflict('Destination changed or not a pristine baseline: '+table.name)
                if old['id']!=row['id']:
                    operations.append({'kind':'delete','table':table.name,'before':old,'after':None})
                    existing.pop(old['id'])
                    operations.append({'kind':'insert','table':table.name,'before':None,'after':row})
                else:operations.append({'kind':'update','table':table.name,'before':old,'after':row})
            else:operations.append({'kind':'insert','table':table.name,'before':None,'after':row})
            existing[row['id']]=row
    return operations

def simulate(state,operations):
    state=json.loads(canonical(state))
    for op in operations:
        rows={r['id']:r for r in state[op['table']]}
        if op['kind']=='delete':rows.pop(op['before']['id'])
        else:rows[op['after']['id']]=op['after']
        state[op['table']]=list(rows.values())
    return state

def inverse(operations):
    return [{'kind':{'insert':'delete','delete':'insert','update':'update'}[op['kind']],'table':op['table'],'before':op['after'],'after':op['before']} for op in reversed(operations)]

def read_state(db,receipt_key):
    state={}
    receipt=None
    for table in TABLES:
        if table.name=='site_settings':
            values=[r[0] for r in db.execute(sa.text('SELECT row_to_json(t) FROM site_settings t WHERE key=:initial OR key=:receipt'),{'initial':'cms_initialized','receipt':receipt_key})]
            receipt=next((r for r in values if r['key']==receipt_key),None)
            state[table.name]=[r for r in values if r['key']=='cms_initialized']
        else:state[table.name]=[r[0] for r in db.execute(sa.text('SELECT row_to_json(t) FROM "'+table.name+'" t'))]
    return state,receipt

def typed(table,row):
    result=dict(row)
    for c in table.columns:
        v=result[c.name]
        if v is None:continue
        if isinstance(c.type,sa.UUID):result[c.name]=uuid.UUID(v)
        elif isinstance(c.type,sa.DateTime):result[c.name]=datetime.fromisoformat(v.replace('Z','+00:00'))
        elif isinstance(c.type,sa.Date):result[c.name]=date.fromisoformat(v)
    return result

def execute_operations(db,operations):
    for op in operations:
        if op['table'] not in NAMES or op['kind'] not in {'insert','update','delete'}:raise Conflict('Operation outside editorial allowlist')
        table=metadata.tables[op['table']]
        if op['kind']=='delete':statement=table.delete().where(table.c.id==uuid.UUID(op['before']['id']))
        elif op['kind']=='insert':statement=table.insert().values(**typed(table,op['after']))
        else:statement=table.update().where(table.c.id==uuid.UUID(op['before']['id'])).values(**typed(table,op['after']))
        # psycopg may report -1 for rowcount with implicit INSERT RETURNING.
        # Explicit returned primary keys prove the affected count consistently.
        if len(db.execute(statement.returning(table.c.id)).all())!=1:raise Conflict('Unexpected affected row count')

def check_media(directory,rows,root):
    root=Path(root)
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():raise Conflict('Expected an existing absolute upload volume directory')
    for r in rows['media_assets']:
        p=root/r['storage_key']
        if p.is_symlink() or (p.exists() and (not p.is_file() or file_hash(p)!=r['sha256'])):raise Conflict('Destination media conflict')

def copy_media(directory,rows,root,created):
    for r in rows['media_assets']:
        destination=Path(root)/r['storage_key']
        if destination.exists():continue
        # Stage on the same filesystem; publish verified bytes atomically without
        # replacement. A failed/ambiguous DB commit must never remove final files.
        temporary=Path(root)/('.editorial-'+str(uuid.uuid4())+'.part')
        try:
            with (directory/'media'/r['storage_key']).open('rb') as source, temporary.open('xb') as target:
                shutil.copyfileobj(source,target);target.flush();os.fsync(target.fileno())
            if file_hash(temporary)!=r['sha256']:raise Conflict('Copied media checksum mismatch')
            os.link(temporary,destination)
            created.append(destination)
            if os.name!='nt':
                fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
                try:os.fsync(fd)
                finally:os.close(fd)
        finally:temporary.unlink(missing_ok=True)

def connect(expected_database):
    from app.config import get_settings
    settings=get_settings()
    if settings.app_env!='production' or settings.postgres_db!=expected_database or settings.db_host!='db':raise Conflict('Production Compose configuration and explicit expected database required')
    return sa.create_engine(settings.database_url,hide_parameters=True,pool_pre_ping=True)

def target_check(db,expected_database):
    if db.execute(sa.text('SELECT current_database()')).scalar_one()!=expected_database:raise Conflict('Unexpected database')
    if db.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one()!='0003':raise Conflict('Unexpected schema revision; no migrations are executed by this tool')
    version=int(db.execute(sa.text('SHOW server_version_num')).scalar_one())
    if not 160000<=version<170000:raise Conflict('Expected PostgreSQL 16')
    db.execute(sa.text("SET LOCAL TIME ZONE 'UTC'"))

def guard_receipt(receipt,current_hash,package_id):
    if not receipt:return False
    value=receipt['value']
    if value.get('package_id')!=package_id or value.get('status')!='applied' or current_hash!=value.get('after_hash'):raise Conflict('Destination changed after this package was applied; no overwrite allowed')
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['verify','plan','apply','rollback'])
    parser.add_argument('directory');parser.add_argument('--expected-database');parser.add_argument('--output');parser.add_argument('--approved-plan');parser.add_argument('--uploads-root',default='/app/uploads');parser.add_argument('--confirm-production-write',action='store_true');parser.add_argument('--confirm-rollback',action='store_true')
    args=parser.parse_args()
    directory,manifest,payload,baseline=verify(args.directory)
    rows=payload['rows'];package_id=manifest['package_id'];receipt_key=RECEIPT_PREFIX+package_id
    if args.mode=='verify':print(canonical({'verified':True,'package_id':package_id,'modules':manifest['modules'],'media':len(rows['media_assets'])}));return
    if not args.expected_database:raise Conflict('--expected-database required')
    if args.mode=='plan' and not args.output:raise Conflict('--output required for private reviewed plan')
    if args.mode in {'apply','rollback'} and (not args.approved_plan or not args.confirm_production_write):raise Conflict('Reviewed plan and --confirm-production-write required')
    if args.mode=='rollback' and not args.confirm_rollback:raise Conflict('--confirm-rollback required')
    reviewed=json.loads(Path(args.approved_plan).read_text(encoding='utf-8')) if args.approved_plan else None
    if reviewed and (reviewed.get('package_id')!=package_id or reviewed.get('database')!=args.expected_database):raise Conflict('Plan bound to another package/database')
    check_media(directory,rows,args.uploads_root)
    engine=connect(args.expected_database);created=[]
    try:
        # Reads use a stable snapshot. Writes acquire table locks under READ COMMITTED
        # before reading, so a pre-lock snapshot cannot hide a concurrent commit.
        with engine.connect().execution_options(isolation_level='REPEATABLE READ' if args.mode=='plan' else 'READ COMMITTED') as db:
            with db.begin():
                if args.mode=='plan':db.execute(sa.text('SET TRANSACTION READ ONLY'))
                else:
                    db.execute(sa.text("SET LOCAL lock_timeout='10s'"));db.execute(sa.text("SET LOCAL statement_timeout='5min'"))
                    db.execute(sa.text('SELECT pg_advisory_xact_lock(734018231)'))
                    db.execute(sa.text('LOCK TABLE '+','.join('"'+t.name+'"' for t in TABLES)+' IN SHARE ROW EXCLUSIVE MODE'))
                target_check(db,args.expected_database)
                state,receipt=read_state(db,receipt_key);before_hash=state_hash(state)
                if args.mode=='rollback':
                    if not receipt or receipt['value'].get('plan_sha256')!=digest(reviewed):raise Conflict('Matching import receipt/plan required')
                    if receipt['value']['status']=='rolled_back':print(canonical({'status':'already_rolled_back'}));return
                    if before_hash!=receipt['value']['after_hash']:raise Conflict('Destination changed after import; rollback refused')
                    execute_operations(db,inverse(reviewed['operations']))
                    if state_hash(read_state(db,receipt_key)[0])!=reviewed['before_hash']:raise Conflict('Rollback verification failed')
                    value={**receipt['value'],'status':'rolled_back','rolled_back_at':datetime.now(timezone.utc).isoformat()}
                    db.execute(metadata.tables['site_settings'].update().where(metadata.tables['site_settings'].c.id==uuid.UUID(receipt['id'])).values(value=value))
                    print(canonical({'status':'rollback_prepared_in_transaction','media_retained':True}))
                else:
                    if guard_receipt(receipt,before_hash,package_id):
                        print(canonical({'status':'already_applied_no_writes','package_id':package_id}));return
                    operations=build_plan(state,rows,baseline)
                    planned={'format_version':1,'package_id':package_id,'database':args.expected_database,'before_hash':before_hash,'operations':operations,'after_hash':state_hash(simulate(state,operations))}
                    if args.mode=='plan':write_private(args.output,planned);print(canonical({'status':'plan_ready_no_writes','operations':len(operations),'plan_sha256':digest(planned)}));return
                    if reviewed!=planned:raise Conflict('Destination/plan changed; create and review a new plan')
                    copy_media(directory,rows,args.uploads_root,created)
                    execute_operations(db,operations)
                    after=state_hash(read_state(db,receipt_key)[0])
                    if after!=planned['after_hash']:raise Conflict('Post-import state verification failed')
                    for r in rows['media_assets']:
                        if file_hash(Path(args.uploads_root)/r['storage_key'])!=r['sha256']:raise Conflict('Media changed before commit')
                    db.execute(metadata.tables['site_settings'].insert().values(id=uuid.uuid4(),key=receipt_key,value={'status':'applied','package_id':package_id,'before_hash':before_hash,'after_hash':after,'plan_sha256':digest(reviewed),'applied_at':datetime.now(timezone.utc).isoformat(),'new_media':[p.name for p in created]}))
        print(canonical({'status':'committed','package_id':package_id,'new_media':len(created)}))
    finally:
        # Keep final media even on failure: a commit acknowledgement can be lost
        # after the server committed. Orphans are safe; deleting referenced files is not.
        engine.dispose()

if __name__=='__main__':
    try:main()
    except Exception as error:
        # SQLAlchemy exceptions may contain private values/SQL parameters. Never print them.
        message=str(error) if isinstance(error,Conflict) else type(error).__name__+'; details omitted to protect private data'
        print('EDITORIAL TRANSFER REFUSED: '+message,file=sys.stderr);sys.exit(1)
