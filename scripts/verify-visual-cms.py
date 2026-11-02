"""Disposable local QA stack. Source DB/media are read only; never uses production."""
import io,subprocess,sys,time,tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.private/visual-cms'
PREFIX='portfolio-visual-cms-qa'
IMAGE='portfolio-visual-backend'
def docker(*args,capture=False,input=None):
    result=subprocess.run(['docker',*map(str,args)],cwd=ROOT,input=input,capture_output=capture,check=True)
    return result.stdout if capture else None
ENV=['-e','POSTGRES_PASSWORD=disposable-visual-cms-password-32','-e','POSTGRES_USER=portfolio','-e','POSTGRES_DB=portfolio','-e','DB_HOST='+PREFIX+'-db','-e','SITE_URL=http://127.0.0.1:8097','-e','CORS_ORIGINS=["http://127.0.0.1:8097"]']
def backend(*cmd,capture=False,database='portfolio'):
    test_env=['-e','SITE_URL=http://localhost:8080','-e','CORS_ORIGINS=["http://localhost:8080"]'] if database=='portfolio_tests' else []
    return docker('run','--rm','--network',PREFIX,*ENV,*test_env,'-e','POSTGRES_DB='+database,'-v',str(ROOT/'backend')+':/app','-v',PREFIX+'-media:/app/uploads',IMAGE,*cmd,capture=capture)
def serve(after):
    source=ROOT/'backend' if after else STATE/'baseline/backend'
    if not source.is_dir() and not after:source=STATE/'before-backend' # retained older QA runs
    (source/'uploads').mkdir(exist_ok=True)
    docker('run','-d','--name',PREFIX+'-api','--network',PREFIX,'--network-alias','backend',*ENV,'-v',str(source)+':/app:ro','-v',PREFIX+'-media:/app/uploads',IMAGE)
    docker('run','-d','--name',PREFIX+'-web','--network',PREFIX,'--network-alias','frontend','-e','API_INTERNAL_URL=http://backend:8000','portfolio-visual-'+('after' if after else 'before'))
    docker('run','-d','--name',PREFIX+'-proxy','--network',PREFIX,'-p','127.0.0.1:8097:80','-v',str(ROOT/'infra/nginx/default.conf')+':/etc/nginx/conf.d/default.conf:ro','nginx:stable-alpine')
    for _ in range(40):
        ready=subprocess.run(['docker','exec',PREFIX+'-api','python','-c',"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready',timeout=2)"],capture_output=True)
        if ready.returncode==0:break
        time.sleep(1)
    else:raise RuntimeError('Disposable API failed readiness; inspect its logs')

mode=sys.argv[1]
if mode=='setup':
    STATE.mkdir(parents=True,exist_ok=True)
    baseline=STATE/'baseline'
    if not baseline.exists():
        archive=subprocess.run(['git','archive','7c1aa6b','backend','frontend'],cwd=ROOT,capture_output=True,check=True).stdout
        baseline.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(baseline,filter='data')
    docker('build','-t','portfolio-visual-before',baseline/'frontend')
    docker('network','create',PREFIX)
    docker('volume','create',PREFIX+'-db');docker('volume','create',PREFIX+'-media')
    docker('run','-d','--name',PREFIX+'-db','--network',PREFIX,*ENV,'-v',PREFIX+'-db:/var/lib/postgresql/data','postgres:16-alpine')
    for _ in range(40):
        if subprocess.run(['docker','exec',PREFIX+'-db','pg_isready','-U','portfolio'],capture_output=True).returncode==0:break
        time.sleep(1)
    dump=docker('exec','carlos-andre-portfolio-db-1','sh','-c','pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc',capture=True)
    docker('exec','-i',PREFIX+'-db','pg_restore','-U','portfolio','-d','portfolio','--no-owner','--no-privileges','--exit-on-error',input=dump)
if mode in ('setup','resume-media'):
    docker('run','--rm','--user','0','--network','none','--volumes-from','carlos-andre-portfolio-backend-1:ro','-v',PREFIX+'-media:/restore',IMAGE,'sh','-c','cp -r /app/uploads/. /restore/ && chown -R appuser:appuser /restore')
    setup="import json,secrets; from app.db import get_engine; from app.admin import hasher; from app import models as m; p=secrets.token_urlsafe(32); e='visual-qa-'+secrets.token_hex(6)+'@example.com'; db=get_engine().connect(); db.execute(m.admin_users.insert().values(email=e,password_hash=hasher.hash(p))); db.commit(); print(json.dumps({'email':e,'password':p})); db.close()"
    (STATE/'credentials.json').write_bytes(backend('python','-c',setup,capture=True))
    serve(False)
elif mode in ('before','after'):
    for suffix in ('proxy','web','api'):docker('rm','-f',PREFIX+'-'+suffix)
    if mode=='after':backend('alembic','upgrade','head')
    serve(mode=='after')
elif mode=='test':
    backend('alembic','check')
    docker('exec',PREFIX+'-db','dropdb','--if-exists','-U','portfolio','portfolio_tests')
    docker('exec',PREFIX+'-db','createdb','-U','portfolio','portfolio_tests')
    backend('alembic','upgrade','head',database='portfolio_tests')
    backend('python','-m','app.import_cms',database='portfolio_tests')
    backend('python','-m','pytest','-q','-p','no:cacheprovider','tests',database='portfolio_tests')
elif mode=='cleanup':
    for suffix in ('proxy','web','api','db'):docker('rm','-f',PREFIX+'-'+suffix)
    for suffix in ('db','media'):docker('volume','rm',PREFIX+'-'+suffix)
    docker('network','rm',PREFIX)
    (STATE/'credentials.json').unlink(missing_ok=True)
else:raise ValueError(mode)
