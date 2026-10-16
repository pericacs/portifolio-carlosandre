"""Cadastro único do conteúdo explicitamente fornecido pelo proprietário."""
import sqlalchemy as sa
from sqlalchemy.orm import Session
from app.db import get_engine
from app import models as m
from app.cms import publish_entry,refs,revision
from app.cms_schema import validate


def register(db):
    row=db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.module=='projetos',m.cms_entries.c.slug=='smartfamily',m.cms_entries.c.deleted_at.is_(None)).with_for_update()).mappings().one()
    if db.scalar(sa.select(m.cms_revisions.c.id).where(m.cms_revisions.c.entry_id==row['id'],m.cms_revisions.c.action=='smartfamily_setup').limit(1)):
        print('SmartFamily já cadastrado; edições preservadas.');return
    known={'title':'SmartFamily','slug':'smartfamily','category':'FamilyTech / SaaS / Inteligência Artificial','description':'Plataforma de organização familiar com agenda, tarefas, lembretes, comandos via WhatsApp e assistente inteligente.','technologies':['React','Python','FastAPI','PostgreSQL','Docker','Nginx','Groq','Whisper'],'integrations':['WhatsApp Cloud API','Google Calendar OAuth','Apple Calendar via CalDAV'],'features':['Agenda familiar','Tarefas','Lembretes','Comandos via WhatsApp','Assistente inteligente'],'links':[{'label':'Site institucional','url':'https://www.smartfamily.com.br'},{'label':'Aplicativo SmartFamily','url':'https://app.smartfamily.com.br'}],'visible':True,'featured':row['data'].get('featured',True),'sortOrder':row['data'].get('sortOrder',0),'publicationReviewed':True,'seoTitle':'SmartFamily | Carlos André','metaDescription':'Plataforma de organização familiar: agenda, tarefas, lembretes, WhatsApp e assistente inteligente.'}
    # Preserve prior draft-only material, but publish only the supplied, reviewed facts.
    data=validate('projetos',{**row['data'],**known})
    if '_legacy' in row['data']:data['_legacy']=row['data']['_legacy']
    updated=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==row['id']).values(data=data,version=row['version']+1).returning(m.cms_entries)).mappings().one()
    refs(db,row['id'],'projetos',data,'draft');revision(db,updated,'smartfamily_setup',row['editor_id'])
    publish_entry(db,updated,row['editor_id'],known);db.commit()
    print('SmartFamily cadastrado e página local publicada com os dados fornecidos.')

if __name__=='__main__':
    with Session(get_engine()) as db:register(db)
