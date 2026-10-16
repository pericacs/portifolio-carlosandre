import secrets
from datetime import timedelta
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db
from app import admin, models as m


@pytest.fixture
def access(db):
    # Real PostgreSQL, all writes including API commits stay in the outer rollback.
    session = Session(bind=db, join_transaction_mode="create_savepoint")
    app.dependency_overrides[get_db] = lambda: session
    password = secrets.token_urlsafe(28)
    email = f"test-{secrets.token_hex(8)}@example.com"
    user_id = session.scalar(m.admin_users.insert().values(email=email,
        password_hash=admin.hasher.hash(password)).returning(m.admin_users.c.id))
    session.commit()
    with TestClient(app) as client:
        yield client, session, email, password, user_id
    app.dependency_overrides.clear()
    session.close()


def headers(client):
    return {"Origin": "http://localhost:8080", "X-CSRF-Token": client.get('/api/admin/auth/csrf').json()['csrfToken']}


def login(access):
    client, _, email, password, _ = access
    return client.post('/api/admin/auth/login', json={"email":email,"password":password}, headers=headers(client))


def test_unauthorized_routes(access):
    client, *_ = access
    for route in ['auth/me','dashboard','audit']:
        result=client.get('/api/admin/'+route)
        assert result.status_code==401
        assert result.headers['cache-control']=='no-store'
    assert client.post('/api/admin/register', json={}).status_code==404


def test_login_cookie_hash_rotation_logout(access):
    client, db, email, _, user_id=access
    before=client.get('/api/admin/auth/csrf').json()['csrfToken']
    response=login(access)
    assert response.status_code==200
    assert response.json()=={'email':email}
    cookies=response.headers.get_list('set-cookie')
    assert any('HttpOnly' in c and 'SameSite=strict' in c and 'portfolio_session=' in c for c in cookies)
    token=client.cookies.get(admin.SESSION_COOKIE)
    csrf=client.cookies.get(admin.CSRF_COOKIE)
    assert before!=csrf
    row=db.execute(sa.select(m.admin_sessions).where(m.admin_sessions.c.admin_id==user_id)).mappings().one()
    assert row['token_hash']==admin.digest(token) and row['csrf_hash']==admin.digest(csrf)
    assert token not in str(row) and csrf not in str(row)
    assert client.get('/api/admin/auth/me').status_code==200
    assert login(access).status_code==200
    assert client.cookies.get(admin.SESSION_COOKIE)!=token
    assert db.scalar(sa.select(m.admin_sessions.c.revoked_at).where(m.admin_sessions.c.token_hash==admin.digest(token)))
    assert client.post('/api/admin/auth/logout',headers=headers(client)).status_code==200
    assert client.get('/api/admin/auth/me').status_code==401
    actions=set(db.scalars(sa.select(m.audit_logs.c.action).where(m.audit_logs.c.actor_id==user_id)))
    assert {'auth.login','auth.logout'}<=actions


def test_csrf_and_origin_enforced(access):
    client, _, email, password, _=access
    body={'email':email,'password':password}
    assert client.post('/api/admin/auth/login',json=body).status_code==403
    head=headers(client);head['Origin']='https://attacker.example'
    assert client.post('/api/admin/auth/login',json=body,headers=head).status_code==403
    assert login(access).status_code==200
    assert client.post('/api/admin/auth/logout',headers={'Origin':'http://localhost:8080'}).status_code==403
    fake=secrets.token_urlsafe(32)
    client.cookies.set(admin.CSRF_COOKIE,fake,domain='testserver.local',path='/')
    assert client.post('/api/admin/auth/logout',headers={'Origin':'http://localhost:8080','X-CSRF-Token':fake}).status_code==403


def test_bad_credentials_generic_and_limited(access):
    client, db, email, _, _=access
    responses=[]
    for _ in range(5):
        responses.append(client.post('/api/admin/auth/login',json={'email':email,'password':'wrong'},headers=headers(client)))
    assert all(r.status_code==401 for r in responses)
    blocked=client.post('/api/admin/auth/login',json={'email':email,'password':'wrong'},headers=headers(client))
    assert blocked.status_code==429 and blocked.headers['retry-after']=='900'
    unknown=client.post('/api/admin/auth/login',json={'email':'unknown@example.com','password':'wrong'},headers=headers(client))
    assert unknown.json()==responses[0].json()
    assert db.scalar(sa.select(m.auth_rate_limits.c.attempts).where(m.auth_rate_limits.c.key==admin.digest('login:account:'+email)))==6
    db.execute(m.auth_rate_limits.update().where(m.auth_rate_limits.c.key==admin.digest('login:account:'+email)).values(expires_at=admin.now()-timedelta(seconds=1)))
    db.commit()
    assert login(access).status_code==200


def test_expired_and_disabled_sessions(access):
    client, db, _, _, user_id=access
    assert login(access).status_code==200
    db.execute(m.admin_sessions.update().where(m.admin_sessions.c.admin_id==user_id).values(expires_at=admin.now()-timedelta(seconds=1)));db.commit()
    assert client.get('/api/admin/dashboard').status_code==401
    assert login(access).status_code==200
    db.execute(m.admin_users.update().where(m.admin_users.c.id==user_id).values(active=False));db.commit()
    assert client.get('/api/admin/dashboard').status_code==401
    assert login(access).status_code==401


def test_dashboard_counts_are_database_values(access):
    client, db, *_=access
    assert login(access).status_code==200
    result=client.get('/api/admin/dashboard').json()
    assert result['counts']['projects']==db.scalar(sa.select(sa.func.count()).select_from(m.projects).where(m.projects.c.archived_at.is_(None)))
    if db.scalar(sa.select(m.site_settings.c.id).where(m.site_settings.c.key=='cms_initialized')):
        assert result['counts']['experiences']==db.scalar(sa.select(sa.func.count()).select_from(m.cms_entries).where(m.cms_entries.c.module=='experiencias',m.cms_entries.c.deleted_at.is_(None)))
    else:
        assert result['counts']['experiences']==db.scalar(sa.select(sa.func.count()).select_from(m.experiences).where(m.experiences.c.archived_at.is_(None)))
    assert result['analyticsConnected'] is False
    assert isinstance(client.get('/api/admin/audit').json(),list)


def test_recovery_disabled_without_smtp(access,monkeypatch):
    client, _, email, *_=access
    settings=admin.get_settings().model_copy(update={'smtp_host':'','smtp_from':''})
    monkeypatch.setattr(admin,'get_settings',lambda:settings)
    assert client.get('/api/admin/auth/csrf').json()['passwordRecoveryAvailable'] is False
    assert client.post('/api/admin/auth/recovery',json={'email':email},headers=headers(client)).status_code==503


def test_recovery_single_use_revokes_sessions(access,monkeypatch):
    client, db, email, _, user_id=access
    settings=admin.get_settings().model_copy(update={'smtp_host':'smtp.test','smtp_from':'sender@example.com','smtp_user':''})
    monkeypatch.setattr(admin,'get_settings',lambda:settings)
    sent=[]
    monkeypatch.setattr(admin,'send_reset',lambda *args:sent.append(args))
    assert login(access).status_code==200
    known=client.post('/api/admin/auth/recovery',json={'email':email},headers=headers(client))
    unknown=client.post('/api/admin/auth/recovery',json={'email':'not-registered@example.com'},headers=headers(client))
    assert known.status_code==unknown.status_code==202 and known.json()==unknown.json()
    assert len(sent)==1 and sent[0][0]==email
    token=sent[0][1]
    assert db.scalar(sa.select(m.password_resets.c.token_hash).where(m.password_resets.c.admin_id==user_id))==admin.digest(token)
    new_password=secrets.token_urlsafe(28)
    result=client.post('/api/admin/auth/reset',json={'token':token,'password':new_password},headers=headers(client))
    assert result.status_code==200
    assert client.get('/api/admin/auth/me').status_code==401
    assert client.post('/api/admin/auth/reset',json={'token':token,'password':new_password},headers=headers(client)).status_code==400
    assert client.post('/api/admin/auth/login',json={'email':email,'password':new_password},headers=headers(client)).status_code==200


def test_expired_reset_and_short_password_rejected(access):
    client, db, _, _, user_id=access
    token=secrets.token_urlsafe(32)
    db.execute(m.password_resets.insert().values(admin_id=user_id,token_hash=admin.digest(token),expires_at=admin.now()-timedelta(minutes=1)));db.commit()
    assert client.post('/api/admin/auth/reset',json={'token':token,'password':'short'},headers=headers(client)).status_code==422
    assert client.post('/api/admin/auth/reset',json={'token':token,'password':secrets.token_urlsafe(28)},headers=headers(client)).status_code==400


def test_secure_cookie_flag_in_production(access,monkeypatch):
    settings=admin.get_settings().model_copy(update={'cookie_secure':True})
    monkeypatch.setattr(admin,'get_settings',lambda:settings)
    client, _, email, password, _=access
    with TestClient(app,base_url='https://testserver') as secure_client:
        csrf=secure_client.get('/api/admin/auth/csrf').json()['csrfToken']
        result=secure_client.post('/api/admin/auth/login',json={'email':email,'password':password},headers={'Origin':'http://localhost:8080','X-CSRF-Token':csrf})
        assert result.status_code==200
        assert all('Secure' in value for value in result.headers.get_list('set-cookie'))


def test_smtp_adapter_uses_tls_and_fragment_link(monkeypatch):
    settings=admin.get_settings().model_copy(update={'smtp_host':'smtp.example.com','smtp_from':'sender@example.com',
        'smtp_user':'smtp-test-user','smtp_password':'test-only-value','smtp_starttls':True})
    monkeypatch.setattr(admin,'get_settings',lambda:settings)
    calls=[]
    class FakeSMTP:
        def __init__(self,*args,**kwargs): calls.append('connect')
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def starttls(self,**kwargs): calls.append('tls')
        def login(self,*args): calls.append('login')
        def send_message(self,message):
            calls.append('send')
            assert '/admin/redefinir-senha#token=' in message.get_content()
            assert '?token=' not in message.get_content()
    monkeypatch.setattr(admin.smtplib,'SMTP',FakeSMTP)
    admin.send_reset('test@example.com',secrets.token_urlsafe(32),None)
    assert calls==['connect','tls','login','send']


def test_prune_preserves_accounts_audit_and_live_tokens(access,monkeypatch):
    from app import cli
    client,db,_,_,user_id=access
    login(access)
    db.execute(m.password_resets.insert().values(admin_id=user_id,token_hash=admin.digest('expired'),expires_at=admin.now()-timedelta(days=1)))
    db.commit()
    # Execute against the test's outer transaction without touching real accounts.
    # Use a context manager that yields the same SQLAlchemy Session.
    from contextlib import contextmanager
    class TestEngine:
        @contextmanager
        def begin(self):
            yield db
            db.commit()
    monkeypatch.setattr(cli,'get_engine',lambda:TestEngine())
    cli.prune_auth()
    assert db.scalar(sa.select(m.password_resets.c.id).where(m.password_resets.c.token_hash==admin.digest('expired'))) is None
    assert client.get('/api/admin/auth/me').status_code==200
    assert db.scalar(sa.select(m.audit_logs.c.id).where(m.audit_logs.c.actor_id==user_id))
