"""Isolated before/after Home and CMS proof. No source DB or VPS writes."""
import json,os,subprocess,time,uuid
from pathlib import Path
root=Path(__file__).resolve().parents[1];name='portfolio-avallow-'+uuid.uuid4().hex[:10]
out=root/'.private'/name;out.mkdir(parents=True)
backend='carlosandre-docx-check-backend'
env=['-e','POSTGRES_USER=stage','-e','POSTGRES_DB=stage','-e','POSTGRES_PASSWORD=synthetic-avallow-password-32','-e','DB_HOST=db']
def run(*args):
    result=subprocess.run(['docker',*args],capture_output=True,text=True,encoding='utf8',check=True)
    return result.stdout.strip()
def app(*args):return run('run','--rm','--network',name,*env,backend,*args)
try:
    run('network','create','--internal',name);run('network','create',name+'-edge');run('volume','create',name)
    run('run','-d','--name',name+'-db','--network',name,'--network-alias','db',*env,'-v',name+':/var/lib/postgresql/data','postgres:16-alpine')
    for _ in range(60):
        if subprocess.run(['docker','exec',name+'-db','pg_isready','-U','stage'],capture_output=True).returncode==0:break
        time.sleep(1)
    app('alembic','upgrade','head');app('python','-m','app.import_cms')
    bases={}
    for label,image in [('before','carlosandre-docx-check-frontend'),('after','carlosandre-avallow-check-frontend')]:
        config=(root/'infra/nginx/production.conf').read_text().replace('frontend:3000',label+':3000')
        file=out/(label+'.conf');file.write_text(config)
        run('run','-d','--name',name+'-'+label,'--network',name,'--network-alias',label,'-e','API_INTERNAL_URL=http://backend:8000',image)
        proxy=name+'-'+label+'-proxy'
        run('run','-d','--name',proxy,'--network',name+'-edge','-p','127.0.0.1::80','-v',str(file)+':/etc/nginx/conf.d/default.conf:ro','nginx:stable-alpine')
        run('network','connect',name,proxy)
        binding=json.loads(run('inspect',proxy))[0]['NetworkSettings']['Ports']['80/tcp'][0]
        bases[label]='http://127.0.0.1:'+binding['HostPort']
    base=bases['after']
    run('run','-d','--name',name+'-api','--network',name,'--network-alias','backend',*env,'-e','SITE_URL='+base,'-e','CORS_ORIGINS='+json.dumps([base]),backend)
    credentials=json.loads(app('python','-c',"import json,secrets; from app.db import get_engine; from app.admin import hasher; from app import models as m; password=secrets.token_urlsafe(32); c=get_engine().connect(); c.execute(m.admin_users.insert().values(email='avallow-local@example.com',password_hash=hasher.hash(password))); c.commit(); print(json.dumps({'email':'avallow-local@example.com','password':password})); c.close()"))
    fixture=out/'fixture.json';fixture.write_text(json.dumps(credentials))
    child=os.environ.copy();child.update(AVALLOW_BEFORE=bases['before'],AVALLOW_AFTER=base,AVALLOW_FIXTURE=str(fixture),AVALLOW_OUTPUT=str(out),AVALLOW_CONTAINER=name+'-api',AVALLOW_PYTHON=__import__('sys').executable)
    try:subprocess.run(['node',str(root/'frontend/tests/avallow-card.spec.cjs')],env=child,cwd=root,check=True)
    finally:fixture.unlink(missing_ok=True)
    print('PASS: AVALLOW; evidence:',out)
finally:
    subprocess.run(['docker','rm','-f',*[name+suffix for suffix in ['-db','-api','-before','-after','-before-proxy','-after-proxy']]],capture_output=True)
    subprocess.run(['docker','volume','rm',name],capture_output=True)
    subprocess.run(['docker','network','rm',name,name+'-edge'],capture_output=True)
