import pytest
from fastapi import HTTPException
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
