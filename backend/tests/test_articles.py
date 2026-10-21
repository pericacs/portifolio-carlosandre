import pytest
from fastapi import HTTPException
from test_admin import access
from app.cms_schema import validate,clean_html

def test_article_external_requires_original_url():
    data={'title':'Insight','slug':'insight','contentType':'Insight','readingMode':'Externo','originalUrl':'https://www.linkedin.com/posts/example'}
    assert validate('artigos',data,True)['body']==''
    with pytest.raises(HTTPException):validate('artigos',{**data,'originalUrl':''},True)

def test_internal_requires_author_text_and_preserves_figures():
    data={'title':'Article','slug':'article','readingMode':'Interno'}
    with pytest.raises(HTTPException):validate('artigos',data,True)
    html='<figure><img src="/api/media/00000000-0000-0000-0000-000000000001"><figcaption>Simulação com dados fictícios.</figcaption></figure><pre>print(1)\nprint(2)</pre><script>alert(1)</script>'
    cleaned=clean_html(html)
    assert '<figcaption>Simulação com dados fictícios.</figcaption>' in cleaned
    assert 'print(1)\nprint(2)' in cleaned
    assert '<script>' not in cleaned
    assert validate('artigos',{**data,'body':html},True)['readingMode']=='Interno'

def test_confirmed_dates_and_types_are_validated():
    with pytest.raises(HTTPException):validate('artigos',{'title':'Article','slug':'article','publishedDate':'há duas semanas'})
    with pytest.raises(HTTPException):validate('artigos',{'title':'Article','slug':'article','contentType':'Unknown'})


def test_article_home_controls_are_in_available_tabs_and_independent():
    from app.cms_schema import MODULES
    article={f['key']:f for f in MODULES['artigos']['fields']}
    project={f['key']:f for f in MODULES['projetos']['fields']}
    assert article['featured']['tab']=='Publicação' and article['featured']['label']=='Destaque na Home'
    assert article['sortOrder']['tab']=='Publicação'
    assert article['featured'] is not project['featured']
    assert project['featured']['tab']=='SEO e publicação'


def test_feature_existing_split_changes_only_flag_and_preserves_draft(access):
    import sqlalchemy as sa
    from app import cms,models as m
    from app.feature_split_home import feature_split
    from test_admin import login,headers
    client,db,*_=access;login(access)
    data={'title':'O SPLIT DO MAL','slug':'o-split-do-mal','body':'<p>Conteúdo publicado para controle.</p>','visible':True,'featured':False,'spotlight':True,'sortOrder':17}
    row=client.post('/api/admin/cms/artigos',json={'data':data},headers=headers(client)).json()
    row=client.post('/api/admin/cms/artigos/'+row['id']+'/publish',json={'version':row['version']},headers=headers(client)).json()
    draft={**row['data'],'description':'Later draft must stay private'}
    row=client.put('/api/admin/cms/artigos/'+row['id'],json={'data':draft,'version':row['version']},headers=headers(client)).json()
    assert feature_split(db)['version']==row['version'] and not feature_split(db)['changed']
    count=db.scalar(sa.select(sa.func.count()).select_from(m.cms_entries))
    changed=feature_split(db,True,row['version']);db.commit();assert changed['changed']
    updated=client.get('/api/admin/cms/artigos/'+row['id']).json()
    assert updated['data']=={**row['data'],'featured':True}
    assert updated['published_data']=={**row['published_data'],'featured':True}
    assert updated['status']==row['status'] and updated['published_at']==row['published_at']
    assert db.scalar(sa.select(sa.func.count()).select_from(m.cms_entries))==count
    assert not feature_split(db,True,updated['version'])['changed']
    with pytest.raises(HTTPException):feature_split(db,True,row['version'])


def test_initial_split_flag_does_not_create_or_publish_article(access):
    from app.feature_split_home import feature_split
    client,db,*_=access
    with pytest.raises(ValueError):feature_split(db,True,1)
