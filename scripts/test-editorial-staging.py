"""Rehearse the approved editorial package using exclusively disposable Docker resources."""
import hashlib, json, os, secrets, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / '.private/editorial-transfer-20261021T042605Z'
ARCHIVE = Path(str(PACKAGE) + '.tar.gz')
EXPECTED = '60812da2f38caa50b9a52fb04b07ab4a7689f78fde5538713b82fe848acd69c3'
IMAGE = 'carlosandre-production-check-backend'
PREFIX = 'portfolio-editorial-stage-' + secrets.token_hex(5)
OUT = ROOT / '.private' / PREFIX
OUT.mkdir()
PASSWORD = secrets.token_hex(24)
checks = []

def run(args, fail=False):
    p = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if (p.returncode == 0) == fail:
        raise RuntimeError('Unexpected command result: ' + p.stdout[-2000:] + p.stderr[-2000:])
    return p.stdout.strip()

def docker(*args, fail=False): return run(['docker', *args], fail)
def check(name, condition=True):
    if not condition: raise AssertionError(name)
    checks.append(name)
    print('PASS ' + name, flush=True)

def client(db, *args, fail=False):
    env = {'APP_ENV':'production','POSTGRES_USER':'stage','POSTGRES_PASSWORD':PASSWORD,
           'POSTGRES_DB':db,'DB_HOST':'db','SITE_URL':'https://carlosandre.tech',
           'CORS_ORIGINS':'["https://carlosandre.tech"]','COOKIE_SECURE':'true'}
    cmd = ['run','--rm','--network',PREFIX]
    for k,v in env.items(): cmd += ['-e',k+'='+v]
    cmd += ['-v',str(PACKAGE)+':/migration:ro','-v',PREFIX+'-media:/app/uploads',
            '-v',PREFIX+'-review:/review',IMAGE,*args]
    return docker(*cmd, fail=fail)

def py(db, code):
    return client(db,'python','-c',"import sys;sys.path.insert(0,'/migration/tools');import editorial_transfer as e;import sqlalchemy as sa;" + code)

def snapshot(db):
    return json.loads(py(db,"engine=e.connect('"+db+"');\nwith engine.connect() as c:\n s,r=e.read_state(c,e.RECEIPT_PREFIX+e.verify('/migration')[1]['package_id']);print(e.canonical({'hash':e.state_hash(s),'receipt':r,'counts':{k:len(v) for k,v in s.items()}}))"))

def cli(db, mode, fail=False):
    args = [mode,'/migration','--expected-database',db]
    if mode=='plan': args += ['--output','/review/'+db+'.json']
    else: args += ['--approved-plan','/review/'+db+'.json','--confirm-production-write']
    if mode=='rollback': args += ['--confirm-rollback']
    return client(db,'python','/migration/tools/editorial_transfer.py',*args,fail=fail)

def initialize(db, seed=False):
    docker('exec',PREFIX,'createdb','-U','stage',db)
    client(db,'alembic','upgrade','head')
    if seed: client(db,'python','-m','app.import_cms')

def validate(db):
    code = """
directory,manifest,payload,baseline=e.verify('/migration')
engine=e.connect(DBNAME)
with engine.connect() as c:
 s,r=e.read_state(c,e.RECEIPT_PREFIX+manifest['package_id'])
 assert e.state_hash(s)==e.state_hash(payload['rows'])
 assert len(s['cms_entries'])==122 and len(s['media_assets'])==28
 from collections import Counter
 assert Counter(x['status'] for x in s['cms_entries'])=={'draft':118,'published':4}
 for t in e.TABLES:
  for fk in t.foreign_keys:
   ids={str(x[fk.column.name]) for x in s.get(fk.column.table.name,[])}
   assert all(x[fk.parent.name] is None or str(x[fk.parent.name]) in ids for x in s[t.name]), (t.name,fk.parent.name,fk.column.table.name)
 for t in e.EXCLUDED: assert c.execute(sa.text('SELECT count(*) FROM '+t)).scalar_one()==(117 if t=='audit_logs' and DBNAME!='stage_empty' else 0),t
 from pathlib import Path
 for x in s['media_assets']: assert e.file_hash(Path('/app/uploads')/x['storage_key'])==x['sha256']
 assert len([p for p in Path('/app/uploads').iterdir() if p.is_file()])==28
 print('122 contents;118 draft;4 published;28 verified media;all rows and relationships match;excluded tables empty')
""".replace('DBNAME',repr(db))
    return py(db,code)

try:
    check('revised archive SHA-256',hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()==EXPECTED)
    docker('network','create','--internal',PREFIX)
    for suffix in ['pg','media','review']: docker('volume','create',PREFIX+'-'+suffix)
    docker('run','--rm','--network','none','--user','0','-v',PREFIX+'-media:/app/uploads',
           '-v',PREFIX+'-review:/review',IMAGE,'chown','10001:10001','/app/uploads','/review')
    docker('run','-d','--name',PREFIX,'--network',PREFIX,'--network-alias','db',
           '-e','POSTGRES_USER=stage','-e','POSTGRES_PASSWORD='+PASSWORD,
           '-v',PREFIX+'-pg:/var/lib/postgresql/data','postgres:16-alpine')
    for attempt in range(60):
        p=subprocess.run(['docker','exec',PREFIX,'pg_isready','-U','stage'],capture_output=True)
        if p.returncode==0: break
        time.sleep(1)
    else: raise RuntimeError('Disposable PostgreSQL did not become ready')
    for db,seed in [('stage_seed',True),('stage_empty',False)]:
        initialize(db,seed)
        before=snapshot(db)
        if seed:
            print(py(db,"engine=e.connect('"+db+"');base=e.initial_rows(e.verify('/migration')[3]);\nwith engine.connect() as c:\n s,_=e.read_state(c,'none');bad=[r for r in s['cms_entries'] if not e.pristine(r,base)];print(e.canonical({'non_pristine':len(bad),'differences':[{'module':r['module'],'fields':[k for k in ['source_key','module','slug','title'] if r[k] != (base[r['id']]['data'].get('slug','main') if k=='slug' else base[r['id']]['data']['title'] if k=='title' else base[r['id']][k])],'data_keys':[k for k in set(e.normalized_data(r['module'],r['data']))|set(base[r['id']]['data']) if e.normalized_data(r['module'],r['data']).get(k)!=base[r['id']]['data'].get(k)]} for r in bad]}))"),flush=True)
        check(db+' initial count',before['counts']['cms_entries']==(117 if seed else 0))
        cli(db,'plan');check(db+' planning is read only',snapshot(db)==before)
        cli(db,'apply');validate(db);check(db+' exact content, media, FK, states, exclusions')
        after=snapshot(db)
        check(db+' idempotent apply','already_applied_no_writes' in cli(db,'apply') and snapshot(db)==after)
        cli(db,'rollback');rolled=snapshot(db)
        check(db+' rollback restores before hash',rolled['hash']==before['hash'] and rolled['receipt']['value']['status']=='rolled_back')
        check(db+' idempotent rollback','already_rolled_back' in cli(db,'rollback') and snapshot(db)==rolled)
    initialize('stage_failure',True)
    before=snapshot('stage_failure');cli('stage_failure','plan')
    py('stage_failure',"engine=e.connect('stage_failure');\nwith engine.begin() as c:\n c.execute(sa.text(\"CREATE FUNCTION stage_reject_receipt() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.key LIKE 'editorial_import:%' THEN RAISE EXCEPTION 'intentional staging failure'; END IF; RETURN NEW; END $$\"));c.execute(sa.text('CREATE TRIGGER stage_reject BEFORE INSERT ON site_settings FOR EACH ROW EXECUTE FUNCTION stage_reject_receipt()'))")
    cli('stage_failure','apply',fail=True)
    check('forced SQL failure rolls back every editorial write and receipt',snapshot('stage_failure')==before)
    py('stage_failure',"engine=e.connect('stage_failure');\nwith engine.begin() as c: c.execute(sa.text('DROP TRIGGER stage_reject ON site_settings'));c.execute(sa.text('DROP FUNCTION stage_reject_receipt()'))")
    cli('stage_failure','apply');validate('stage_failure');check('retry after transaction failure succeeds')
    py('stage_failure',"engine=e.connect('stage_failure');\nwith engine.begin() as c: c.execute(sa.text(\"UPDATE cms_entries SET version=version+1 WHERE id=(SELECT id FROM cms_entries LIMIT 1)\"))")
    changed=snapshot('stage_failure')
    cli('stage_failure','apply',fail=True);cli('stage_failure','rollback',fail=True)
    check('later editorial changes block apply and rollback without overwrite',snapshot('stage_failure')==changed)
    check('revised archive remains unchanged',hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()==EXPECTED)
finally:
    # Only exact random resource names created by this invocation are removed.
    subprocess.run(['docker','rm','-f',PREFIX],capture_output=True)
    for suffix in ['pg','media','review']: subprocess.run(['docker','volume','rm',PREFIX+'-'+suffix],capture_output=True)
    subprocess.run(['docker','network','rm',PREFIX],capture_output=True)
    (OUT/'results.json').write_text(json.dumps({'checks':checks,'passed':len(checks),'archive_sha256':EXPECTED,'resources':PREFIX},indent=2),encoding='utf-8')
    print('Private evidence: '+str(OUT),flush=True)
