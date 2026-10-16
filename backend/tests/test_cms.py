import io
import secrets
from datetime import timedelta
import pytest
import sqlalchemy as sa
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app import models as m,cms,admin
from app.cms_schema import MODULES
from app.import_cms import import_content
from app.worker import tick
from test_admin import access,headers,login


def payload(module):
    key='qa-'+secrets.token_hex(6)
    data={'title':'Teste '+key,'slug':key,'visible':True,'featured':True,'sortOrder':1}
    if module=='experiencias':data.update(company='Empresa teste',role='Engenheiro',startMonth='2020-01',endMonth='2022-01')
    if module=='formacoes':data.update(institution='Instituição teste',degree='Curso teste')
    if module=='artigos':data['body']='<h2>Título</h2><p>Texto do artigo para teste.</p>'
    if module=='cases':data.update(company='Empresa teste',confidentialityReviewed=True)
    if module=='videos':data['planned']=True
    return data


@pytest.mark.parametrize('module',[k for k,v in MODULES.items() if not v.get('singleton')])
def test_crud_persistence_publication_archive_delete(access,module):
    client,db,*_=access;assert login(access).status_code==200
    r=client.post('/api/admin/cms/'+module,json={'data':payload(module)},headers=headers(client));assert r.status_code==201,r.text
    row=r.json();entry_id=row['id'];url='/api/admin/cms/'+module+'/'+entry_id
    assert db.scalar(sa.select(m.cms_entries.c.title).where(m.cms_entries.c.id==entry_id))==row['title']
    data={**row['data'],'title':row['title']+' editado'}
    r=client.put(url,json={'data':data,'version':row['version']},headers=headers(client));assert r.status_code==200,r.text;row=r.json()
    r=client.post(url+'/publish',json={'version':row['version']},headers=headers(client));assert r.status_code==200,r.text;row=r.json()
    assert any(x['id']==entry_id for x in client.get('/api/content').json()['modules'][module])
    old_title=row['published_data']['title'];data={**row['data'],'title':'Ainda não publicado'}
    row=client.put(url,json={'data':data,'version':row['version']},headers=headers(client)).json()
    assert next(x for x in client.get('/api/content').json()['modules'][module] if x['id']==entry_id)['title']==old_title
    assert client.put(url,json={'data':data,'version':1},headers=headers(client)).status_code==409
    row=client.post(url+'/archive',json={'version':row['version']},headers=headers(client)).json()
    assert not any(x['id']==entry_id for x in client.get('/api/content').json()['modules'][module])
    assert client.delete(url+'?version='+str(row['version']),headers=headers(client)).status_code==200
    assert client.get(url).status_code==404
    assert db.scalar(sa.select(sa.func.count()).select_from(m.cms_revisions).where(m.cms_revisions.c.entry_id==entry_id))>=5


@pytest.mark.parametrize('module',['perfil','configuracoes','curriculo'])
def test_singleton_edit_and_publish(access,module):
    client,db,*_=access;login(access)
    row=client.get('/api/admin/cms/'+module).json()['items'][0]
    data={**row['data'],'title':row['title']+' atualizado'}
    row=client.put(f"/api/admin/cms/{module}/{row['id']}",json={'data':data,'version':row['version']},headers=headers(client)).json()
    r=client.post(f"/api/admin/cms/{module}/{row['id']}/publish",json={'version':row['version']},headers=headers(client));assert r.status_code==200,r.text
    assert client.get('/api/content').json()['modules'][module][0]['title']==data['title']


def test_permissions_csrf_and_validation(access):
    client,*_=access
    for path in ['/api/admin/cms/schema','/api/admin/cms/projetos','/api/admin/cms/media','/api/admin/messages']:
        assert client.get(path).status_code==401
    login(access)
    assert client.post('/api/admin/cms/projetos',json={'data':payload('projetos')}).status_code==403
    assert client.post('/api/admin/cms/experiencias',json={'data':{**payload('experiencias'),'endMonth':'2010-01'}},headers=headers(client)).status_code==422
    assert client.post('/api/admin/cms/experiencias',json={'data':{**payload('experiencias'),'current':True,'endDateValidationRequired':True}},headers=headers(client)).status_code==422
    assert client.post('/api/admin/cms/videos',json={'data':{**payload('videos'),'youtubeUrl':'https://evil.example/watch?v=abcdefghijk'}},headers=headers(client)).status_code==422


def test_xss_sanitization_and_version_restore(access):
    client,*_=access;login(access)
    data={**payload('artigos'),'body':'<h2>Bom</h2><script>alert(1)</script><p onclick="evil()">Texto seguro aqui</p><a href="javascript:evil()">link</a><img src="https://evil.example/x" onerror="evil()">'}
    row=client.post('/api/admin/cms/artigos',json={'data':data},headers=headers(client)).json()
    body=row['data']['body'];assert 'script' not in body and 'onclick' not in body and 'javascript:' not in body and 'onerror' not in body and 'evil.example' not in body
    url='/api/admin/cms/artigos/'+row['id'];row=client.put(url,json={'version':row['version'],'data':{**row['data'],'title':'Editado'}},headers=headers(client)).json()
    restored=client.put(url+'/restore',json={'version':row['version'],'revision':1},headers=headers(client));assert restored.status_code==200,restored.text
    assert restored.json()['data']['title']==data['title']


def test_confidentiality_and_video_publish_guards(access):
    client,*_=access;login(access)
    for module,data in [('cases',{**payload('cases'),'confidentialityReviewed':False}),('videos',{**payload('videos'),'planned':False})]:
        row=client.post('/api/admin/cms/'+module,json={'data':data},headers=headers(client)).json()
        assert client.post(f"/api/admin/cms/{module}/{row['id']}/publish",json={'version':row['version']},headers=headers(client)).status_code==422


def test_upload_persistence_private_until_publish_and_reference_guard(access,tmp_path,monkeypatch):
    client,db,*_=access;login(access);monkeypatch.setattr(cms,'UPLOAD_ROOT',tmp_path)
    image=io.BytesIO();Image.new('RGB',(12,9),'blue').save(image,format='PNG')
    result=client.post('/api/admin/cms/media',files={'file':('foto.png',image.getvalue(),'image/png')},headers=headers(client));assert result.status_code==201,result.text
    asset=result.json();assert any(tmp_path.iterdir())
    with TestClient(app) as anon: assert anon.get(asset['url']).status_code==401
    row=client.post('/api/admin/cms/projetos',json={'data':{**payload('projetos'),'cover':asset['url'],'gallery':[asset['url']]}},headers=headers(client)).json()
    assert client.post(f"/api/admin/cms/projetos/{row['id']}/publish",json={'version':row['version']},headers=headers(client)).status_code==200
    with TestClient(app) as anon: assert anon.get(asset['url']).content==image.getvalue()
    assert client.delete('/api/admin/cms/media/'+asset['id'],headers=headers(client)).status_code==409
    assert client.post('/api/admin/cms/media',files={'file':('mal.svg',b'<svg onload="evil()"/>','image/svg+xml')},headers=headers(client)).status_code==422
    assert client.post('/api/admin/cms/media',files={'file':('fake.png',b'not an image','image/png')},headers=headers(client)).status_code==422


def test_curriculum_upload_and_replace(access,tmp_path,monkeypatch):
    client,*_=access;login(access);monkeypatch.setattr(cms,'UPLOAD_ROOT',tmp_path)
    import zipfile
    doc=io.BytesIO()
    with zipfile.ZipFile(doc,'w') as z:z.writestr('word/document.xml','<document/>')
    asset=client.post('/api/admin/cms/media',files={'file':('curriculo.docx',doc.getvalue(),'application/octet-stream')},headers=headers(client)).json()
    row=client.get('/api/admin/cms/curriculo').json()['items'][0]
    r=client.put('/api/admin/cms/curriculo/'+row['id'],json={'version':row['version'],'data':{**row['data'],'file':asset['url'],'privacyReviewed':True}},headers=headers(client));assert r.status_code==200,r.text
    row=r.json();assert client.post(f"/api/admin/cms/curriculo/{row['id']}/publish",json={'version':row['version']},headers=headers(client)).status_code==200
    with TestClient(app) as anon:assert anon.get(asset['url']).content==doc.getvalue()


def test_schedule_worker_and_snapshot_independence(access):
    client,db,*_=access;login(access)
    row=client.post('/api/admin/cms/projetos',json={'data':payload('projetos')},headers=headers(client)).json();url='/api/admin/cms/projetos/'+row['id'];scheduled_title=row['data']['title']
    row=client.post(url+'/schedule',json={'version':row['version'],'scheduledAt':(admin.now()+timedelta(days=1)).isoformat()},headers=headers(client)).json()
    row=client.put(url,json={'version':row['version'],'data':{**row['data'],'title':'Edição posterior ao agendamento'}},headers=headers(client)).json()
    db.execute(m.cms_entries.update().where(m.cms_entries.c.id==row['id']).values(scheduled_at=admin.now()-timedelta(minutes=1)));db.commit()
    tick(db)
    record=db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.id==row['id'])).mappings().one()
    assert record['published_data']['title']==scheduled_title and record['data']['title']=='Edição posterior ao agendamento'
    version=record['version'];tick(db)
    assert db.scalar(sa.select(m.cms_entries.c.version).where(m.cms_entries.c.id==row['id']))==version


def test_contact_messages_csv_and_deletion(access,monkeypatch):
    monkeypatch.setattr("app.contact_notifications.send_contact",lambda body: None)
    client,db,*_=access
    token=client.get('/api/contact/challenge').json()['ticket']
    db.execute(m.contact_tickets.update().where(m.contact_tickets.c.token_hash==admin.digest(token)).values(created_at=admin.now()-timedelta(seconds=5)));db.commit()
    body={'name':'=Teste de fórmula','email':'cms-test@example.com','subject':'Outro assunto','message':'Mensagem real de teste automatizado.','consent':True,'ticket':token}
    assert client.post('/api/contact',json={**body,'consent':False},headers={'Origin':'http://localhost:8080'}).status_code==422
    result=client.post('/api/contact',json=body,headers={'Origin':'http://localhost:8080'});assert result.status_code==201,result.text
    assert client.post('/api/contact',json=body,headers={'Origin':'http://localhost:8080'}).status_code==422
    login(access)
    row=client.get('/api/admin/messages?q=cms-test@example.com').json()['items'][0]
    assert client.patch('/api/admin/messages/'+row['id'],json={'status':'reviewing','internal_notes':'Anotação interna'},headers=headers(client)).status_code==200
    csv=client.get('/api/admin/messages/export?q=cms-test@example.com');assert csv.status_code==200 and "'=Teste" in csv.text
    assert client.delete('/api/admin/messages/'+row['id'],headers=headers(client)).status_code==200
    assert not client.get('/api/admin/messages?q=cms-test@example.com').json()['items']


def test_import_idempotent_and_does_not_publish(access):
    client,db,*_=access
    assert import_content(db)==0
    row=db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.source_key=='initial:experiencias:compass-cef')).mappings().one()
    assert row['data']['endDateValidationRequired'] is True and row['data']['current'] is False
    assert row['published_data'] is None


def test_retention_cleanup(access):
    _,db,*_=access
    message_id=db.scalar(m.contact_messages.insert().values(name='Expirado',email='expired@example.com',subject='Teste',message='Teste retenção',consent=True,privacy_version='test',created_at=admin.now()-timedelta(days=800)).returning(m.contact_messages.c.id))
    db.execute(m.contact_notifications.insert().values(message_id=message_id));db.commit();tick(db)
    assert db.scalar(sa.select(m.contact_messages.c.id).where(m.contact_messages.c.id==message_id)) is None
