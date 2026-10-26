"""Reproduce root-owned 0600/0700 contexts; prove non-root production startup.

Only tracked backend sources and synthetic ignore canaries enter the build.
No local .env, uploads, credentials, or existing database is read.
"""
import io,subprocess,tarfile,tempfile,time,uuid
from pathlib import Path
root=Path(__file__).resolve().parents[1]
name='portfolio-permissions-'+uuid.uuid4().hex[:10]
images=[name+':before',name+':fixed',name+':ignore']
env=['-e','POSTGRES_USER=stage','-e','POSTGRES_DB=stage','-e','POSTGRES_PASSWORD=synthetic-permission-check-password','-e','DB_HOST=db','-e','APP_ENV=production','-e','SITE_URL=https://carlosandre.tech','-e','CORS_ORIGINS=["https://carlosandre.tech"]','-e','COOKIE_SECURE=true']
def run(*args,**kw):return subprocess.run(['docker',*args],check=True,cwd=root,**kw)
def context(dockerfile):
    files=subprocess.check_output(['git','ls-files','backend'],cwd=root,text=True).splitlines()
    payload={p.removeprefix('backend/'):(root/p).read_bytes() for p in files if (root/p).is_file()}
    payload['Dockerfile.prod']=dockerfile
    for p in ['.env','.env.production','.private/canary','uploads/canary','backups/canary','.venv/canary','__pycache__/canary.pyc','.pytest_cache/canary','tests/canary','canary.pyc']:
        payload[p]=b'SYNTHETIC_IGNORE_CANARY_ONLY'
    payload['Dockerfile.ignorecheck']=b'FROM python:3.12-slim\nCOPY . /context\nRUN python -c "from pathlib import Path; p=Path(\'/context\'); assert all(not (p/x).exists() for x in [\'.env\',\'.env.production\',\'.private\',\'uploads\',\'backups\',\'.venv\',\'__pycache__\',\'.pytest_cache\',\'tests\',\'canary.pyc\'])"\n'
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode='w') as archive:
        directories=set()
        for p in payload:
            directories.update(str(parent).replace('\\','/') for parent in Path(p).parents if str(parent)!='.')
        for p in sorted(directories):
            item=tarfile.TarInfo(p);item.type=tarfile.DIRTYPE;item.mode=0o700;item.uid=item.gid=0;archive.addfile(item)
        for p,blob in payload.items():
            item=tarfile.TarInfo(p);item.size=len(blob);item.mode=0o600;item.uid=item.gid=0;archive.addfile(item,io.BytesIO(blob))
    return output.getvalue()

try:
    old=subprocess.check_output(['git','show','HEAD:backend/Dockerfile.prod'],cwd=root)
    fixed=(root/'backend/Dockerfile.prod').read_text(encoding='utf8').encode('utf8')
    # The baseline comes from the parent of the fix when rerunning after commit.
    if old==fixed:
        start=old.index(b'# Context permissions');end=old.index(b'USER appuser',start)
        old=old[:start]+b'RUN mkdir uploads && chown appuser:appuser uploads\n'+old[end:]
    run('build','-f','Dockerfile.prod','-t',images[0],'-',input=context(old))
    denied=subprocess.run(['docker','run','--rm','--network','none',images[0],'python','-c',"from pathlib import Path; Path('/app/app/main.py').read_text()"],capture_output=True,text=True)
    assert denied.returncode!=0 and 'PermissionError' in denied.stderr,'Restrictive-context regression was not reproduced'
    print('PASS: original image reproduces PermissionError with 0600/0700 context',flush=True)
    run('build','-f','Dockerfile.prod','-t',images[1],'-',input=context(fixed))
    # Prepacked remote tar contexts do not exercise the client's ignore filtering.
    # Use a normal directory containing only tracked files + synthetic canaries.
    private=root/'.private';private.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='permission-context-',dir=private) as scratch:
        directory=Path(scratch).resolve();assert directory.is_relative_to(private.resolve())
        with tarfile.open(fileobj=io.BytesIO(context(fixed))) as archive:
            for item in archive:
                path=directory/item.name;assert path.resolve().is_relative_to(directory)
                if item.isdir():path.mkdir(parents=True,exist_ok=True)
                else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.extractfile(item).read())
        run('build','-f',str(directory/'Dockerfile.ignorecheck'),'-t',images[2],str(directory))
        (directory/'Dockerfile.ignorecheck.dockerignore').write_bytes((root/'backend/Dockerfile.prod.dockerignore').read_bytes())
        run('build','-f',str(directory/'Dockerfile.ignorecheck'),'-t',images[2],str(directory))
    proof="""import os,stat; from pathlib import Path
assert os.getuid()==10001
for base in [Path('/app/app'),Path('/app/alembic')]:
    for p in [base,*base.rglob('*')]:
        mode=stat.S_IMODE(p.stat().st_mode)
        assert p.stat().st_uid==0 and mode==(0o755 if p.is_dir() else 0o644),(str(p),oct(mode))
        assert os.access(p,os.R_OK) and (not p.is_dir() or os.access(p,os.X_OK))
        assert not os.access(p,os.W_OK)
for name in ['alembic.ini','requirements.txt']:assert stat.S_IMODE(Path('/app',name).stat().st_mode)==0o644
assert not any(Path('/app',x).exists() for x in ['.env','.env.production','.private','backups','.venv'])
Path('/app/uploads/probe').write_text('writable');Path('/app/uploads/probe').unlink()
from app.main import app
from app.docx_parser import parse_docx
print('PASS: UID=10001; code 0644, directories 0755, root-owned/read-only; uploads writable; imports OK')
"""
    run('run','--rm','--network','none',*env,images[1],'python','-c',proof)
    run('network','create','--internal',name);run('volume','create',name)
    run('run','-d','--name',name+'-db','--network',name,'--network-alias','db',*env,'-v',name+':/var/lib/postgresql/data','postgres:16-alpine')
    for _ in range(60):
        if subprocess.run(['docker','exec',name+'-db','pg_isready','-U','stage'],capture_output=True).returncode==0:break
        time.sleep(1)
    run('run','--rm','--network',name,*env,images[1],'alembic','upgrade','head')
    run('run','-d','--name',name+'-api','--network',name,*env,images[1])
    for _ in range(45):
        result=subprocess.run(['docker','exec',name+'-api','python','-c',"import os,json,urllib.request; assert os.getuid()==10001; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health/live'))['status']=='ok'; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready'))['schema']=='0003'"],capture_output=True)
        if result.returncode==0:break
        time.sleep(1)
    else:raise AssertionError('Production Uvicorn did not become ready as appuser')
    run('run','-d','--name',name+'-worker','--network',name,*env,images[1],'python','-m','app.worker')
    for _ in range(30):
        result=subprocess.run(['docker','exec',name+'-worker','python','-c',"import os,time; from pathlib import Path; assert os.getuid()==10001 and time.time()-Path('/tmp/worker-heartbeat').stat().st_mtime<30"],capture_output=True)
        if result.returncode==0:break
        time.sleep(1)
    else:raise AssertionError('Worker failed to start as appuser')
    print('PASS: .dockerignore canaries excluded; Alembic, actual Uvicorn live/ready and worker heartbeat passed as appuser UID 10001',flush=True)
finally:
    for suffix in ['-worker','-api','-db']:subprocess.run(['docker','rm','-f',name+suffix],capture_output=True)
    subprocess.run(['docker','volume','rm',name],capture_output=True)
    subprocess.run(['docker','network','rm',name],capture_output=True)
    subprocess.run(['docker','image','rm',*images],capture_output=True)
