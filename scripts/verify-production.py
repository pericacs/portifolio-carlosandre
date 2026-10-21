"""Isolated Docker checks. Never reads local .env or touches existing containers."""
import json
import os
os.environ["ENV_FILE"] = ".env.production.example"
import subprocess
import uuid
from pathlib import Path
root = Path(__file__).resolve().parents[1]
prefix = "carlosandre-check-" + uuid.uuid4().hex[:10]
def run(*args, capture=False):
    result = subprocess.run(["docker", *args], cwd=root, text=True, capture_output=capture)
    if result.returncode:
        if capture: print(result.stderr)
        result.check_returncode()
    return result.stdout.strip() if capture else None
backend = "carlosandre-production-check-backend"
frontend = "carlosandre-production-check-frontend"
env = ["-e", "POSTGRES_PASSWORD=isolated-test-password-32-characters", "-e", "POSTGRES_USER=portfolio", "-e", "POSTGRES_DB=portfolio", "-e", "DB_HOST="+prefix+"-db"]
def app(*command, volumes=()):
    return run("run", "--rm", "--network", prefix, *env, *volumes, backend, *command)
try:
    config = json.loads(run("compose", "--env-file", ".env.production.example", "-f", "docker-compose.prod.yml", "config", "--format", "json", capture=True))
    assert config["name"] == "carlosandre-portfolio-prod"
    assert all(not service.get("ports") for name, service in config["services"].items() if name != "nginx")
    port = config["services"]["nginx"]["ports"]
    assert len(port) == 1 and port[0]["host_ip"] == "127.0.0.1" and str(port[0]["published"]) == "8088" and port[0]["target"] == 80
    assert config["networks"]["private"]["internal"]
    assert all(v["name"].startswith("carlosandre-portfolio-prod_") for v in config["volumes"].values())
    assert all(v["name"].startswith("carlosandre-portfolio-prod_") for v in config["networks"].values())
    assert all(service.get("mem_limit") for name,service in config["services"].items())
    run("network", "create", "--internal", prefix)
    run("volume", "create", prefix+"-db")
    run("volume", "create", prefix+"-media")
    run("run", "-d", "--name", prefix+"-db", "--network", prefix, *env, "-v", prefix+"-db:/var/lib/postgresql/data", "postgres:16-alpine")
    import time
    for attempt in range(60):
        result = subprocess.run(["docker", "exec", prefix+"-db", "pg_isready", "-U", "portfolio"], capture_output=True)
        if result.returncode == 0: break
        time.sleep(1)
    else: raise RuntimeError("Database failed to start")
    app("alembic", "upgrade", "head")
    app("alembic", "upgrade", "head")
    app("alembic", "check")
    app("python", "-m", "app.import_cms")
    app("python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "/app/tests", volumes=("-v", str(root/"backend/tests")+":/app/tests:ro", "-v", prefix+"-media:/app/uploads"))
    app("python", "-c", "from pathlib import Path; Path('/app/uploads/persistence-check').write_text('persistent')", volumes=("-v",prefix+"-media:/app/uploads"))
    app("python", "-c", "from pathlib import Path; assert Path('/app/uploads/persistence-check').read_text()=='persistent'", volumes=("-v",prefix+"-media:/app/uploads"))
    run("restart", prefix+"-db")
    for attempt in range(60):
        if subprocess.run(["docker", "exec", prefix+"-db", "pg_isready", "-U", "portfolio"], capture_output=True).returncode == 0: break
        time.sleep(1)
    app("alembic", "current")
    prod = ["-e","APP_ENV=production","-e","SITE_URL=https://carlosandre.tech","-e",'CORS_ORIGINS=["https://carlosandre.tech"]',"-e","COOKIE_SECURE=true"]
    run("run", "--rm", "--network", prefix, *env, *prod, backend, "python", "-c", "from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); assert c.get('/api/health/ready').status_code==200; assert c.get('/api/docs').status_code==404; r=c.get('/api/admin/auth/csrf'); cookie=r.headers['set-cookie']; assert 'Secure' in cookie and 'SameSite=strict' in cookie; assert c.post('/api/admin/auth/login',json={'email':'test@example.com','password':'test-password-32-characters'}).status_code==403; print('Production health, docs, cookies and CSRF passed')")
    run("run", "--rm", "--network", "none", "--entrypoint", "node", frontend, "-e", "require('fs').accessSync('/app/server.js'); console.log('Standalone frontend artifact passed')")
    # Verify a real logical dump restores into a separate database.
    dump = subprocess.run(["docker","exec",prefix+"-db","pg_dump","-U","portfolio","-d","portfolio","-Fc"],capture_output=True,check=True).stdout
    run("exec",prefix+"-db","createdb","-U","portfolio","recovery")
    subprocess.run(["docker","exec","-i",prefix+"-db","pg_restore","-U","portfolio","-d","recovery","--exit-on-error","--single-transaction"],input=dump,check=True)
    revision = run("exec",prefix+"-db","psql","-U","portfolio","-d","recovery","-Atc","SELECT version_num FROM alembic_version",capture=True)
    assert revision == "0003"
    run("run","-d","--name",prefix+"-web","--network",prefix,"--network-alias","frontend","-e","API_INTERNAL_URL=http://"+prefix+"-api:8000",frontend)
    run("run","-d","--name",prefix+"-api","--network",prefix,"--network-alias","backend",*env,*prod,"-v",prefix+"-media:/app/uploads",backend)
    time.sleep(3)
    run("exec",prefix+"-web","node","-e","fetch('http://127.0.0.1:3000').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))")
    archive = subprocess.run(["docker","run","--rm","--network","none","-v",prefix+"-media:/app/uploads:ro",backend,"tar","-C","/app/uploads","-czf","-","."],capture_output=True,check=True).stdout
    run("volume","create",prefix+"-restored-media")
    subprocess.run(["docker","run","--rm","-i","--network","none","-v",prefix+"-restored-media:/app/uploads",backend,"tar","-C","/app/uploads","-xzf","-"],input=archive,check=True)
    app("python","-c","from pathlib import Path; assert Path('/app/uploads/persistence-check').read_text()=='persistent'",volumes=("-v",prefix+"-restored-media:/app/uploads:ro"))
    run("volume","create",prefix+"-tls")
    run("run","--rm","--user","0","--network","none","-v",prefix+"-tls:/tls",backend,"openssl","req","-x509","-newkey","rsa:2048","-nodes","-keyout","/tls/privkey.pem","-out","/tls/fullchain.pem","-days","1","-subj","/CN=carlosandre.tech")
    run("run","--rm","--network",prefix,"-v",prefix+"-tls:/etc/nginx/tls:ro","-v",str(root/"infra/nginx/production.conf")+":/etc/nginx/conf.d/default.conf:ro","nginx:stable-alpine","nginx","-t")
    run("run","-d","--name",prefix+"-proxy","--network",prefix,"--network-alias","portfolio-proxy","-v",str(root/"infra/nginx/production.conf")+":/etc/nginx/conf.d/default.conf:ro","nginx:stable-alpine")
    run("run","-d","--name",prefix+"-worker","--network",prefix,*env,*prod,backend,"python","-m","app.worker")
    time.sleep(3)
    temp = root / ".private" / prefix
    temp.mkdir(parents=True, exist_ok=True)
    host_config = (root/"infra/nginx/host-portfolio.conf.example").read_text().replace("http://127.0.0.1:8088", "http://portfolio-proxy:80").replace("/etc/letsencrypt/live/carlosandre.tech", "/etc/nginx/tls")
    (temp/"host.conf").write_text(host_config, encoding="utf-8")
    run("run","-d","--name",prefix+"-host","--network",prefix,"--network-alias","carlosandre.tech","-v",prefix+"-tls:/etc/nginx/tls:ro","-v",str(temp/"host.conf")+":/etc/nginx/conf.d/default.conf:ro","nginx:stable-alpine")
    run("exec",prefix+"-host","nginx","-t")
    run("run","--rm","--network",prefix,*env,"-v",prefix+"-tls:/tls:ro",backend,"python","-c","import ssl,urllib.request; c=ssl.create_default_context(cafile='/tls/fullchain.pem'); assert urllib.request.urlopen('https://carlosandre.tech/api/health/ready',context=c,timeout=10).status==200; assert urllib.request.urlopen('https://carlosandre.tech/',context=c,timeout=10).status==200; print('Existing-host Nginx -> internal Nginx HTTPS proxy passed')")
    run("exec",prefix+"-worker","python","-c","import time,pathlib; assert time.time()-pathlib.Path('/tmp/worker-heartbeat').stat().st_mtime < 90")
    run("run","--rm","--network","none","-v",str(root/"scripts/production")+":/scripts:ro","bash:5.2","bash","-c","for f in /scripts/*.sh; do bash -n \"$f\" || exit; done")
    if any(flag in __import__("sys").argv for flag in ("--visual","--docx","--combined")):
        # Read-only clone of approved local state; restore only into the disposable database.
        run("stop",prefix+"-api",prefix+"-worker")
        if any(flag in __import__("sys").argv for flag in ("--docx","--combined")):
            # Remove synthetic unit-test contents from this disposable database
            # before taking a visual baseline; no source database is accessed.
            run("exec",prefix+"-db","dropdb","-U","portfolio","portfolio")
            run("exec",prefix+"-db","createdb","-U","portfolio","portfolio")
            app("alembic","upgrade","head")
            app("python","-m","app.import_cms")
        if "--visual" in __import__("sys").argv:
            source_dump = subprocess.run(["docker","exec","carlos-andre-portfolio-db-1","sh","-c",'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'],capture_output=True,check=True).stdout
            subprocess.run(["docker","exec","-i",prefix+"-db","pg_restore","-U","portfolio","-d","portfolio","--clean","--if-exists","--no-owner","--no-privileges","--exit-on-error","--single-transaction"],input=source_dump,check=True)
            run("run","--rm","--user","0","--network","none","--volumes-from","carlos-andre-portfolio-backend-1:ro","-v",prefix+"-media:/restore",backend,"sh","-c","cp -r /app/uploads/. /restore/ && chown -R 10001:10001 /restore")
        run("network","create",prefix+"-edge")
        run("run","-d","--name",prefix+"-browser-proxy","--network",prefix+"-edge","-p","127.0.0.1::80","-v",str(root/"infra/nginx/production.conf")+":/etc/nginx/conf.d/default.conf:ro","nginx:stable-alpine")
        run("network","connect",prefix,prefix+"-browser-proxy")
        binding = json.loads(run("inspect",prefix+"-browser-proxy",capture=True))[0]["NetworkSettings"]["Ports"]["80/tcp"][0]
        base="http://127.0.0.1:"+binding["HostPort"]
        run("rm","-f",prefix+"-api")
        run("run","-d","--name",prefix+"-api","--network",prefix,"--network-alias","backend",*env,"-e","SITE_URL="+base,"-e",'CORS_ORIGINS=["'+base+'"]',"-v",prefix+"-media:/app/uploads",backend)
        setup = "import json,secrets; from app.db import get_engine; from app.admin import hasher; from app import models as m; password=secrets.token_urlsafe(32); email='recovery-'+secrets.token_hex(6)+'@example.com'; db=get_engine().connect(); db.execute(m.admin_users.insert().values(email=email,password_hash=hasher.hash(password))); db.commit(); print(json.dumps({'email':email,'password':password})); db.close()"
        credentials = run("run","--rm","--network",prefix,*env,backend,"python","-c",setup,capture=True)
        fixture = temp/"browser-fixture.json"
        fixture.write_text(credentials,encoding="utf-8")
        child_env=os.environ.copy()
        child_env.update(RECOVERY_BASE_URL=base,RECOVERY_REFERENCE_URL="http://localhost:8080",RECOVERY_FIXTURE=str(fixture),RECOVERY_OUTPUT=str(temp/"visual"))
        try:
            spec="docx-import.spec.cjs" if any(flag in __import__("sys").argv for flag in ("--docx","--combined")) else "docker-recovery.spec.cjs"
            subprocess.run(["node",str(root/"frontend/tests"/spec)],cwd=root,env=child_env,check=True)
        finally:
            fixture.unlink(missing_ok=True)
        print("Visual report:",temp/"visual/report.json")
        if "--combined" in __import__("sys").argv:
            helper='/tmp/portfolio-release.py'
            run('cp',str(root/'scripts/production/portfolio-release.py'),prefix+'-api:'+helper)
            snapshot=run('exec',prefix+'-api','python',helper,'snapshot','test-combined',capture=True)
            def maintenance(mode,payload=None):
                return subprocess.run(['docker','exec','-i',prefix+'-api','python',helper,mode,'test-combined'],input=payload,text=True,capture_output=True,check=True).stdout
            maintenance('apply',snapshot)
            run('exec',prefix+'-api','python',helper,'probe',base,'http://portfolio-proxy')
            maintenance('verify',snapshot)
            maintenance('rollback',snapshot)
            after=json.loads(run('exec',prefix+'-api','python',helper,'snapshot','test-combined',capture=True))
            before=json.loads(snapshot)
            assert after['target']['data']==before['target']['data'] and after['target']['published_data']==before['target']['published_data'] and after['others_hash']==before['others_hash']
            print('PASS: combined release helper, real HTTP staging upload, targeted data rollback and unchanged other CMS entries')
    print("PASS: isolated migrations, backend suite, production security and volume persistence")
finally:
    subprocess.run(["docker","rm","-f",prefix+"-db",prefix+"-web",prefix+"-api",prefix+"-proxy",prefix+"-worker",prefix+"-host",prefix+"-browser-proxy"],capture_output=True)
    for suffix in ("-db","-media","-tls","-restored-media"):
        subprocess.run(["docker","volume","rm",prefix+suffix],capture_output=True)
    subprocess.run(["docker","network","rm",prefix,prefix+"-edge"],capture_output=True)
