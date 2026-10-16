import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app import cms
from app.smartfamily_content import content,block
from test_admin import access,login,headers
from test_cms import payload

def test_structured_content_publication_privacy_and_xss(access,tmp_path,monkeypatch):
    client,*_=access;login(access);monkeypatch.setattr(cms,'UPLOAD_ROOT',tmp_path)
    image=io.BytesIO();Image.new('RGB',(40,30),'blue').save(image,format='PNG')
    asset=client.post('/api/admin/cms/media',files={'file':('private-diagram.png',image.getvalue(),'image/png')},headers=headers(client)).json()
    data={**payload('projetos'),**content()}
    data['sfFeatures'].append({**block('private-sentinel','<script>alert(1)</script>private-body'),'visibility':'PRIVADO'})
    data['sfMedia'].append({'slot':'desktop','title':'Private media','alt':'private-alt','description':'','url':asset['url'],'visibility':'PRIVADO','illustrative':False,'order':0})
    row=client.post('/api/admin/cms/projetos',json={'data':data},headers=headers(client)).json();url='/api/admin/cms/projetos/'+row['id']
    assert '<script>' not in row['data']['sfFeatures'][-1]['description']
    row=client.post(url+'/publish',json={'version':row['version']},headers=headers(client)).json()
    with TestClient(app) as anon:
        published=next(x for x in anon.get('/api/content').json()['modules']['projetos'] if x['id']==row['id'])
        assert 'private-sentinel' not in str(published) and asset['url'] not in str(published)
        assert anon.get(asset['url']).status_code==401
    data=row['data'];uploaded=next(x for x in data['sfMedia'] if x['url']==asset['url']);uploaded['visibility']='PÚBLICO';uploaded['order']=99
    row=client.put(url,json={'data':data,'version':row['version']},headers=headers(client)).json()
    assert row['data']['sfMedia'][-1]['order']==99
    row=client.post(url+'/publish',json={'version':row['version']},headers=headers(client)).json()
    with TestClient(app) as anon:assert anon.get(asset['url']).status_code==200
    assert len(client.get(url+'/revisions').json())>=4

@pytest.mark.parametrize('change',[{'status':'Implementado','evidence':''},{'status':'Concluído inventado'}])
def test_implementation_requires_valid_status_and_evidence(access,change):
    client,*_=access;login(access)
    data={**payload('projetos'),'sfFeatures':[{**block('Teste','Teste'),**change}]}
    response=client.post('/api/admin/cms/projetos',json={'data':data},headers=headers(client))
    if response.status_code==201:
        row=response.json();response=client.post('/api/admin/cms/projetos/'+row['id']+'/publish',json={'version':row['version']},headers=headers(client))
    assert response.status_code==422

def test_missing_alt_and_external_image_rejected(access):
    client,*_=access;login(access)
    data={**payload('projetos'),**content()};data['sfMedia'][0]['alt']=''
    row=client.post('/api/admin/cms/projetos',json={'data':data},headers=headers(client)).json()
    assert client.post('/api/admin/cms/projetos/'+row['id']+'/publish',json={'version':row['version']},headers=headers(client)).status_code==422
    data['slug']+='-external';data['sfMedia'][0]['url']='https://example.com/untrusted.png'
    assert client.post('/api/admin/cms/projetos',json={'data':data},headers=headers(client)).status_code==422
