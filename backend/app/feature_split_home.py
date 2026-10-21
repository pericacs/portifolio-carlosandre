"""Explicit, version-checked Home flag update for the existing published Split article."""
import argparse
import json
import sqlalchemy as sa
from sqlalchemy.orm import Session
from app import cms,models as m
from app.db import get_engine
from app.admin import now


def feature_split(db,apply=False,expected_version=None):
    query=sa.select(m.cms_entries).where(m.cms_entries.c.module=='artigos',m.cms_entries.c.slug=='o-split-do-mal',m.cms_entries.c.deleted_at.is_(None))
    row=db.execute(query.with_for_update() if apply else query).mappings().first()
    if not row or not row['published_data']:raise ValueError('O SPLIT DO MAL precisa existir e estar publicado. Nenhum registro foi criado ou publicado.')
    public=row['published_data']
    if public.get('planned') or public.get('visible') is False:raise ValueError('O artigo não está elegível para a Home. Revise sua publicação no painel.')
    if row['scheduled_data'] is not None:raise ValueError('Existe agendamento. Revise-o antes de alterar o destaque.')
    result={'id':str(row['id']),'version':row['version'],'featured':bool(public.get('featured')),'sortOrder':public.get('sortOrder',0),'changed':False}
    if not apply:return result
    if expected_version is None:raise ValueError('Informe a versão obtida na consulta prévia.')
    cms.version_check(row,expected_version)
    if public.get('featured') is True and row['data'].get('featured') is True:return result
    # Change only the approved flag in each snapshot; never publish pending edits.
    updated=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==row['id']).values(data={**row['data'],'featured':True},published_data={**public,'featured':True},version=row['version']+1,updated_at=now()).returning(m.cms_entries)).mappings().one()
    cms.revision(db,updated,'feature_home',None)
    return {**result,'version':updated['version'],'featured':True,'changed':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--expected-version',type=int)
    args=parser.parse_args()
    with Session(get_engine()) as db:
        result=feature_split(db,args.apply,args.expected_version)
        if args.apply:db.commit()
        print(json.dumps(result))

if __name__=='__main__':main()
