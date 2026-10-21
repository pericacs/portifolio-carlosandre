"""Run DOCX checks in disposable PostgreSQL; never uses the original database."""
import json,os,subprocess,time,uuid
from pathlib import Path
root=Path(__file__).resolve().parents[1]
name='portfolio-docx-'+uuid.uuid4().hex[:10]
image='carlosandre-docx-check-backend'
def docker(*args):
    return subprocess.run(['docker',*args],check=True,cwd=root,capture_output=True,text=True).stdout
env=['-e','POSTGRES_USER=stage','-e','POSTGRES_DB=stage','-e','POSTGRES_PASSWORD=synthetic-docx-test-password-32','-e','DB_HOST=db']
def app(*args):
    reference=root/'.private/docx-import-check'
    private_args=['-e','DOCX_REFERENCE=/reference/reference.docx','-v',str(reference)+':/reference:ro'] if (reference/'reference.docx').is_file() else []
    return docker('run','--rm','--network',name,*env,*private_args,'-v',str(root/'backend/app')+':/app/app:ro','-v',str(root/'backend/tests')+':/tests:ro',image,*args)
try:
    docker('network','create','--internal',name);docker('volume','create',name)
    docker('run','-d','--name',name,'--network',name,'--network-alias','db',*env,'-v',name+':/var/lib/postgresql/data','postgres:16-alpine')
    for _ in range(60):
        if subprocess.run(['docker','exec',name,'pg_isready','-U','stage'],capture_output=True).returncode==0:break
        time.sleep(1)
    print(app('alembic','upgrade','head'),flush=True)
    print(app('python','-m','pytest','-q','-p','no:cacheprovider','/tests/test_docx_import.py'),flush=True)
except subprocess.CalledProcessError as error:
    print(error.stdout,flush=True);print(error.stderr,flush=True);raise
finally:
    subprocess.run(['docker','rm','-f',name],capture_output=True)
    subprocess.run(['docker','volume','rm',name],capture_output=True)
    subprocess.run(['docker','network','rm',name],capture_output=True)
