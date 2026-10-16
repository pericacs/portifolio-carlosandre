import re
import nh3
from fastapi import HTTPException

SECTIONS=[('sfFinalHero','Apresentação','Informações gerais'),('sfFinalIntro','Resumo da experiência','Visão geral e solução'),('sfFinalOverview','Visão geral, problema e solução','Visão geral e solução'),('sfFinalFeatures','Funcionalidades demonstradas','Funcionalidades'),('sfFinalChannels','WhatsApp e painel web','Como funciona'),('sfFinalFlow','Da mensagem à confirmação','Como funciona'),('sfFinalTechnology','Arquitetura, integrações e decisões','Arquitetura e tecnologias'),('sfFinalFaq','Perguntas frequentes','Perguntas frequentes'),('sfFinalEvolution','Evolução do produto','Resultados e roadmap'),('sfFinalCta','Chamada final','Links e acessos')]
CLASSES={'eyebrow','actions','btn','secondary','richgrid','richbox','process','detail','tech','stack'}
def fields(field):
    result=[field('sfApproved','Usar a apresentação final aprovada','boolean','SEO e publicação',smartOnly=True)]
    result += [field(key,label,'finalrich',tab,smartOnly=True) for key,label,tab in SECTIONS]
    result += [field(key,label,'media','Imagens e mídia',smartOnly=True) for key,label in [('sfFinalLogo','Logo oficial'),('sfFinalDashboard','Dashboard real'),('sfFinalMap','Mapa ilustrado da infraestrutura')]]
    result.append(field('sfFinalDemos','Demonstrações e transcrições','finaldemos','Demonstrações',smartOnly=True))
    return result

def clean(value):
    def attr(tag,name,v):
        if name=='class':return ' '.join(x for x in v.split() if x in CLASSES) or None
        if tag=='img' and name=='src':return v if re.fullmatch(r'/api/media/[a-f0-9-]{36}',v) else None
        return v
    return nh3.clean(value,tags={'div','article','p','br','h1','h2','h3','strong','b','span','em','ul','ol','li','details','summary','a','img'},attributes={'*':{'class'},'details':{'open'},'a':{'href','target'},'img':{'src','alt'}},attribute_filter=attr,url_schemes={'http','https'},link_rel='noopener noreferrer')

def demos(value,publishing):
    def fail(text):raise HTTPException(422,text)
    if not isinstance(value,list) or len(value)>40:fail('Demonstrações inválidas.')
    result=[]
    for i,item in enumerate(value):
        if not isinstance(item,dict):fail('Demonstração inválida.')
        row={}
        for key in ['title','category','description','message','image','visibility']:
            v=item.get(key,'PÚBLICO' if key=='visibility' else '')
            if not isinstance(v,str) or len(v)>20000:fail('Texto inválido na demonstração.')
            row[key]=v
        if row['category'] not in ['Agenda','Tarefas','Financeiro','Família']:fail('Categoria da demonstração inválida.')
        if row['visibility'] not in ['PÚBLICO','PRIVADO']:fail('Visibilidade inválida.')
        if publishing and row['visibility']=='PÚBLICO' and not all(row[k] for k in ['title','message','image']):fail('Informe título, transcrição e captura original.')
        if row['category']=='Família' and row['title']=='Sua família' and re.search(r'^\s*[678]\.',row['message'],re.M):fail('Os itens 6, 7 e 8 foram removidos da versão aprovada.')
        row['order']=item.get('order',i)
        if type(row['order'])!=int or not 0<=row['order']<=1000:fail('Ordem inválida.')
        result.append(row)
    return sorted(result,key=lambda x:x['order'])

def install(db):
    import json,hashlib,shutil
    from uuid import uuid5,NAMESPACE_URL
    from pathlib import Path
    from PIL import Image
    import sqlalchemy as sa
    from app import models as m
    from app.cms import UPLOAD_ROOT,refs,revision,publish_entry
    from app.cms_schema import validate
    root=Path(__file__).parent/'data'/'smartfamily-final'
    row=db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.module=='projetos',m.cms_entries.c.slug=='smartfamily',m.cms_entries.c.deleted_at.is_(None)).with_for_update()).mappings().one()
    if db.scalar(sa.select(m.cms_revisions.c.id).where(m.cms_revisions.c.entry_id==row['id'],m.cms_revisions.c.action=='smartfamily_final_html').limit(1)):
        print('Versão final já importada; edições preservadas.');return
    mapping={}
    for asset in json.loads((root/'manifest.json').read_text()):
        source=root/asset['file'];raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==asset['sha256']
        with Image.open(source) as image:width,height=image.size;image.verify()
        media_id=uuid5(NAMESPACE_URL,'smartfamily-final:'+asset['sha256']);key=str(media_id)+source.suffix
        if not db.scalar(sa.select(m.media_assets.c.id).where(m.media_assets.c.id==media_id)):
            shutil.copyfile(source,UPLOAD_ROOT/key)
            db.execute(m.media_assets.insert().values(id=media_id,storage_key=key,original_name=asset['file'],mime_type=asset['mime'],size_bytes=len(raw),width=width,height=height,sha256=asset['sha256'],uploaded_by=row['editor_id']))
        mapping['ASSET:'+asset['name']]='/api/media/'+str(media_id)
    text=(root/'content.json').read_text()
    for old,new in mapping.items():text=text.replace(old,new)
    supplied=json.loads(text)
    draft=validate('projetos',{**row['data'],**supplied,'publicationReviewed':True})
    if '_legacy' in row['data']:draft['_legacy']=row['data']['_legacy']
    updated=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==row['id']).values(data=draft,version=row['version']+1).returning(m.cms_entries)).mappings().one()
    refs(db,row['id'],'projetos',draft,'draft');revision(db,updated,'smartfamily_final_html',row['editor_id'])
    publish_entry(db,updated,row['editor_id'],{**(row['published_data'] or {}),**supplied,'publicationReviewed':True});db.commit()
    print('HTML aprovado integrado ao CMS local: 11 arquivos, 8 demonstrações; nenhum deploy externo.')

if __name__=='__main__':
    from sqlalchemy.orm import Session
    from app.db import get_engine
    with Session(get_engine()) as db:install(db)
