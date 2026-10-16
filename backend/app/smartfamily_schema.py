"""Structured, reviewable SmartFamily sections. No executable markup or private files in public snapshots."""
from fastapi import HTTPException

STATUSES=['Não verificado','Em desenvolvimento','Implementado','Planejado']
SLOTS=['cover','desktop','calendar','tasks','whatsapp','mobile','architecture','video']

def fields(field):
    result=[]
    for key,label,tab in [
        ('sfTagline','Chamada do hero','Informações gerais'),
        ('sfOverview','Visão geral','Visão geral e solução'),
        ('sfProblem','Problema de negócio','Visão geral e solução'),
        ('sfSolution','Solução proposta','Visão geral e solução'),
        ('sfHow','Como funciona','Como funciona'),
        ('sfArchitecture','Descrição da arquitetura','Arquitetura e tecnologias'),
        ('sfChallenges','Desafios técnicos','Desafios e decisões'),
        ('sfStage','Estágio de desenvolvimento','Resultados e roadmap'),
        ('sfCtaTitle','Título da chamada final','Links e acessos'),
        ('sfCtaText','Texto da chamada final','Links e acessos')]:
        result.append(field(key,label,'text' if key in ['sfTagline','sfCtaTitle'] else 'richtext',tab,smartOnly=True))
    for key,label,tab in [('sfFeatures','Blocos de funcionalidades','Funcionalidades'),('sfCommands','Exemplos de comandos','Como funciona'),('sfTech','Tecnologias e responsabilidades','Arquitetura e tecnologias'),('sfIntegrations','Integrações externas','Integrações'),('sfDecisions','Decisões de arquitetura','Desafios e decisões'),('sfRoadmap','Etapas do roadmap','Resultados e roadmap')]:
        result.append(field(key,label,'smartblocks',tab,smartOnly=True))
    result.extend([field('sfMedia','Imagens, diagramas e vídeo','smartmedia','Imagens e mídia',smartOnly=True),field('sfMetrics','Indicadores comprovados','metrics','Resultados e roadmap',smartOnly=True)])
    return result

def validate_items(kind,value,publishing):
    from app.cms_schema import clean_html,youtube_id
    def fail(message):raise HTTPException(422,message)
    if not isinstance(value,list) or len(value)>40:fail('Blocos: use até 40 itens.')
    result=[]
    for item in value:
        if not isinstance(item,dict):fail('Bloco inválido.')
        keys=['title','description','status','evidence','visibility'] if kind=='smartblocks' else ['slot','title','description','alt','url','visibility']
        row={}
        for key in keys:
            v=item.get(key,'PÚBLICO' if key=='visibility' else 'Não verificado' if key=='status' else '')
            if not isinstance(v,str) or len(v)>12000:fail('Texto do bloco inválido.')
            row[key]=clean_html(v) if key=='description' else v.strip()
        if row['visibility'] not in ['PÚBLICO','PRIVADO']:fail('Visibilidade inválida.')
        order=item.get('order',len(result))
        if type(order)!=int or not 0<=order<=1000:fail('Ordem inválida.')
        row['order']=order
        if kind=='smartblocks':
            if row['status'] not in STATUSES:fail('Status de implementação inválido.')
            if publishing and row['visibility']=='PÚBLICO' and row['status']=='Implementado' and not row['evidence']:fail('Registre a evidência antes de marcar como implementado.')
        else:
            if row['slot'] not in SLOTS:fail('Posição de mídia inválida.')
            row['illustrative']=item.get('illustrative',True)
            if type(row['illustrative'])!=bool:fail('Tipo de imagem inválido.')
            if not row['url'] and not row['illustrative']:fail('Envie a captura real antes de desmarcar a ilustração.')
            if row['slot']=='video' and row['url']:
                try: valid=youtube_id(row['url'])
                except ValueError:valid=None
                if not valid:fail('Vídeo: use uma URL HTTPS válida do YouTube.')
            if publishing and row['visibility']=='PÚBLICO' and (not row['title'] or not row['alt']):fail('Preencha título e texto alternativo da mídia pública.')
        result.append(row)
    return sorted(result,key=lambda row:row['order'])
