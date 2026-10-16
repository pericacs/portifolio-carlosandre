import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app import cms
from test_admin import access,login,headers
from test_cms import payload


def test_private_fields_and_upload_never_published(access,tmp_path,monkeypatch):
    client,*_=access;login(access);monkeypatch.setattr(cms,'UPLOAD_ROOT',tmp_path)
    image=io.BytesIO();Image.new('RGB',(20,30),'blue').save(image,format='PNG')
    asset=client.post('/api/admin/cms/media',files={'file':('private.png',image.getvalue(),'image/png')},headers=headers(client)).json()
    data={**payload('projetos'),'features':['Agenda','Tarefas'],'integrations':['Google Calendar OAuth'],'privateNotes':'private-sentinel','architecture':'private-architecture','privateFields':['architecture','mobileScreenshots'],'mobileScreenshots':[asset['url']]}
    row=client.post('/api/admin/cms/projetos',json={'data':data},headers=headers(client)).json();url='/api/admin/cms/projetos/'+row['id']
    row=client.post(url+'/publish',json={'version':row['version']},headers=headers(client)).json()
    assert row['data']['architecture']=='private-architecture'
    assert 'architecture' not in row['published_data'] and 'mobileScreenshots' not in row['published_data']
    with TestClient(app) as anon:
        assert anon.get(asset['url']).status_code==401
        assert 'private-sentinel' not in anon.get('/api/content').text
        assert anon.get(url).status_code==401
        assert anon.get(url+'/revisions').status_code==401
    data={**row['data'],'privateFields':[],'desktopScreenshots':[asset['url']],'mobileScreenshots':[]}
    row=client.put(url,json={'data':data,'version':row['version']},headers=headers(client)).json()
    row=client.post(url+'/publish',json={'version':row['version']},headers=headers(client)).json()
    with TestClient(app) as anon:assert anon.get(asset['url']).status_code==200
    data={**row['data'],'privateFields':['desktopScreenshots']}
    row=client.put(url,json={'data':data,'version':row['version']},headers=headers(client)).json()
    client.post(url+'/publish',json={'version':row['version']},headers=headers(client))
    with TestClient(app) as anon:assert anon.get(asset['url']).status_code==401


@pytest.mark.parametrize('unsafe',['postgresql://user:password@db/database','password=not-a-real-secret','http://192.168.0.8','https://service.local/admin','https://example.com/admin','https://example.com/?token=example'])
def test_reject_sensitive_public_content(access,unsafe):
    client,*_=access;login(access)
    row=client.post('/api/admin/cms/projetos',json={'data':{**payload('projetos'),'architecture':unsafe}},headers=headers(client)).json()
    assert client.post('/api/admin/cms/projetos/'+row['id']+'/publish',json={'version':row['version']},headers=headers(client)).status_code==422
