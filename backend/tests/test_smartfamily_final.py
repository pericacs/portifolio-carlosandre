import json
from pathlib import Path
from app.smartfamily_final import clean,demos
from fastapi import HTTPException
import pytest
from test_admin import access,login,headers
from test_cms import payload

def test_final_html_sanitized_and_draft_publication(access):
    client,*_=access;login(access)
    html='<div class="richgrid evil"><article class="richbox"><h3>Teste</h3><p onclick="bad()">Conteúdo</p><script>bad()</script><a href="javascript:bad()">Link</a></article></div>'
    row=client.post('/api/admin/cms/projetos',json={'data':{**payload('projetos'),'sfFinalOverview':html,'sfFinalFeatures':'<p>private-sentinel</p>','privateFields':['sfFinalFeatures']}},headers=headers(client)).json()
    body=row['data']['sfFinalOverview'];assert 'richgrid' in body and 'evil' not in body and 'onclick' not in body and 'script' not in body and 'javascript:' not in body
    row=client.post('/api/admin/cms/projetos/'+row['id']+'/publish',json={'version':row['version']},headers=headers(client)).json()
    assert 'sfFinalFeatures' not in row['published_data']
    assert 'private-sentinel' not in client.get('/api/content').text

def test_approved_transcripts_intact_and_family_removals():
    data=json.loads((Path(__file__).parents[1]/'app/data/smartfamily-final/content.json').read_text())
    result=demos(data['sfFinalDemos'],False)
    assert len(result)==8 and result[0]['message']==data['sfFinalDemos'][0]['message']
    family=next(x for x in result if x['category']=='Família')
    assert '5. 💙 Lucca — Filho' in family['message']
    family['message']+='\n6. Removed item'
    with pytest.raises(HTTPException):demos([family],True)
