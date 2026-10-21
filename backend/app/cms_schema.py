"""Contrato único de campos para validação e formulários do CMS."""
import re
from datetime import date
from urllib.parse import urlparse, parse_qs
import nh3
from fastapi import HTTPException


def field(key, label, kind="text", tab="Informações gerais", **options):
    return dict(key=key, label=label, kind=kind, tab=tab, **options)


def text(key,label,kind="text",**kw): return field(key,label,kind,**kw)
def content(key,label,kind="textarea",**kw): return field(key,label,kind,"Conteúdo",**kw)
def media(key,label,kind="media",**kw): return field(key,label,kind,"Mídia",**kw)
def pub(key,label,kind="boolean",**kw): return field(key,label,kind,"Publicação",**kw)
def refs(key,label,module,multiple=True): return content(key,label,"references" if multiple else "reference",module=module)
COMMON=[text("title","Título / nome",required=True),text("slug","Endereço (slug)",required=True),pub("featured","Destacar na Home"),pub("visible","Visível",default=True),pub("sortOrder","Ordem","number",default=0)]
SEO=[field("seoTitle","Título SEO","text","SEO"),field("metaDescription","Descrição SEO","textarea","SEO")]
DETAIL=[content("description","Descrição resumida"),content("body","Conteúdo completo","richtext"),content("technologies","Tecnologias","lines"),content("links","Links externos","links")]
MEDIA=[media("cover","Imagem principal"),media("gallery","Galeria de imagens","gallery"),media("diagrams","Diagramas técnicos","gallery")]
MODULES={
 "perfil":{"label":"Meu perfil","singleton":True,"fields":[text("title","Nome de apresentação",required=True),text("professionalTitle","Título profissional"),text("subtitle","Subtítulo"),text("heroPrefix","Frase do Hero — início"),text("heroHighlight","Frase do Hero — destaque"),content("heroDescription","Descrição do Hero"),content("biographyPt","Biografia em português","lines"),content("biographyEn","Biografia em inglês","lines"),content("objective","Próximos desafios"),content("quote","Frase de destaque"),content("signature","Frase manuscrita","lines"),content("metrics","Indicadores profissionais","metrics"),media("photo","Fotografia profissional"),text("email","E-mail de contato","email"),text("whatsapp","WhatsApp (país + DDD + número)"),text("linkedin","LinkedIn","url"),text("youtube","YouTube","url"),text("github","GitHub","url"),content("links","Links complementares","links")]},
 "experiencias":{"label":"Currículo e experiências","fields":COMMON+[text("company","Empresa",required=True),text("role","Cargo",required=True),text("displayRole","Cargo resumido (Home)"),text("relationshipType","Tipo de vínculo"),text("startMonth","Início","month"),text("endMonth","Término","month"),pub("current","Trabalho atual"),pub("endDateValidationRequired","Término pendente de validação"),content("description","Resumo profissional"),content("narrative","Descrição completa","lines"),content("responsibilities","Responsabilidades","lines"),content("results","Resultados alcançados","lines"),content("technologies","Tecnologias","lines"),content("tags","Tags da Home","lines"),refs("projectIds","Projetos relacionados","projetos"),text("externalUrl","Link externo","url"),media("logo","Logotipo")]},
 "formacoes":{"label":"Formação acadêmica","fields":COMMON+[text("institution","Instituição",required=True),text("degree","Curso / grau",required=True),text("period","Período"),content("description","Descrição")]},
 "certificacoes":{"label":"Certificações","fields":COMMON+[text("issuer","Instituição emissora"),text("date","Data","date"),text("externalUrl","Link de verificação","url")]},
 "idiomas":{"label":"Idiomas","fields":COMMON+[text("level","Conhecimento declarado")]},
 "curriculo":{"label":"Arquivo do currículo","singleton":True,"fields":[text("title","Nome do documento",required=True),media("file","Currículo PDF ou DOCX","document"),pub("privacyReviewed","Revisei os dados pessoais do arquivo antes de disponibilizar o download")]},
 "categorias":{"label":"Categorias de skills","fields":COMMON+[content("description","Descrição"),text("icon","Ícone","select",options=['database','brain','cloud','code','card','people','chart']),text("color","Cor do ícone","select",options=['blue','violet','cyan','green'])]},
 "skills":{"label":"Skills e conhecimentos","fields":COMMON+[refs("categoryId","Categoria","categorias",False),content("description","Descrição"),text("icon","Ícone","select",options=['database','brain','cloud','code','card','people','chart'])]},
 "projetos":{"label":"Projetos","fields":COMMON+DETAIL+[content("problem","Problema resolvido"),content("solution","Solução proposta"),content("architecture","Arquitetura"),content("results","Resultados comprovados"),text("category","Categoria"),text("developmentStage","Estágio de desenvolvimento"),content("tags","Tags","lines")]+MEDIA+SEO},
 "cases":{"label":"Cases de sucesso","fields":COMMON+DETAIL+[text("company","Empresa",required=True),text("period","Período"),content("context","Contexto"),content("problem","Problema enfrentado"),content("solution","Solução implementada"),content("architecture","Arquitetura"),content("results","Resultados"),content("metrics","Indicadores","metrics"),refs("experienceIds","Experiências relacionadas","experiencias"),refs("projectIds","Projetos relacionados","projetos"),pub("confidentialityReviewed","Revisei as informações confidenciais e autorizo sua publicação")]+MEDIA+SEO},
 "artigos":{"label":"Artigos","fields":COMMON+[text("subtitle","Subtítulo"),text("category","Categoria"),content("description","Resumo"),content("tags","Tags","lines"),content("body","Artigo em português","richtext"),content("titleEn","Título em inglês","text"),content("bodyEn","Artigo em inglês","richtext"),refs("relatedIds","Artigos relacionados","artigos"),pub("planned","Exibir somente como prévia em preparação")]+MEDIA+SEO},
 "videos":{"label":"Vídeos e YouTube","fields":COMMON+[text("youtubeUrl","URL do YouTube","youtube"),content("description","Descrição"),text("category","Categoria"),text("duration","Duração real (ex.: 12:34)"),refs("relatedIds","Artigos associados","artigos"),pub("planned","Conteúdo planejado / em breve")]+[media("cover","Miniatura personalizada")]+SEO},
 "configuracoes":{"label":"Configurações","singleton":True,"fields":[text("title","Nome do site",required=True),media("logo","Logotipo"),media("favicon","Favicon (PNG)"),media("photo","Foto principal alternativa"),media("banner","Banner de contato"),content("footer","Texto do rodapé","lines"),content("institutional","Texto institucional"),content("services","Serviços e chamadas","services"),content("sectionOrder","Ordem das seções da Home","order"),content("categories","Categorias de conteúdo","lines"),content("locales","Idiomas habilitados","lines"),text("email","E-mail comercial","email"),text("whatsapp","WhatsApp"),text("linkedin","LinkedIn","url"),text("youtube","YouTube","url"),text("github","GitHub","url"),text("scheduleUrl","Link comercial / agenda","url"),text("analyticsId","Identificador da integração analytics (preparação)"),pub("retentionDays","Retenção de mensagens em dias","number",default=180)]+SEO},
}
MODULES['artigos']['fields'] += [text('contentType','Tipo','select',options=['Artigo','Insight'],default='Artigo'),content('categories','Assuntos','lines'),text('publishedDate','Data de publicação confirmada','date'),text('author','Autor'),text('originalUrl','URL original','url'),text('readingMode','Modo de leitura','select',options=['Interno','Externo'],default='Interno'),pub('spotlight','Destaque principal da listagem')]
PROJECT_TABS=['Informações gerais','Imagens e mídia','Funcionalidades','Arquitetura e tecnologias','Links e acessos','Resultados e roadmap','SEO e publicação']
project=MODULES['projetos']
for f in project['fields']:
    f['tab']=('Imagens e mídia' if f['tab']=='Mídia' else 'SEO e publicação' if f['tab'] in ['SEO','Publicação'] else 'Arquitetura e tecnologias' if f['key'] in ['architecture','technologies'] else 'Links e acessos' if f['key']=='links' else 'Resultados e roadmap' if f['key']=='results' else 'Informações gerais')
project['fields'] += [field('desktopScreenshots','Screenshots desktop','gallery',PROJECT_TABS[1]),field('mobileScreenshots','Screenshots mobile','gallery',PROJECT_TABS[1]),field('videoLinks','Vídeos demonstrativos','links',PROJECT_TABS[1]),field('features','Funcionalidades','lines',PROJECT_TABS[2]),field('integrations','Integrações','lines',PROJECT_TABS[3]),field('documentation','Documentação PDF / DOCX','document',PROJECT_TABS[4]),field('documentationLinks','Documentação externa','links',PROJECT_TABS[4]),field('privateNotes','Anotações privadas (não armazene senhas)','textarea',PROJECT_TABS[4]),field('roadmap','Roadmap — planos, sem promessas de entrega','lines',PROJECT_TABS[5]),field('publicationReviewed','Revisei o conteúdo e os arquivos públicos: sem segredos ou acessos internos','boolean',PROJECT_TABS[6])]
from app.smartfamily_schema import fields as smart_fields,validate_items
project['fields']+=smart_fields(field)
from app.smartfamily_final import fields as final_fields,clean as final_clean,demos as final_demos
project['fields']+=final_fields(field)
project['tabs']=PROJECT_TABS[:1]+['Visão geral e solução']+PROJECT_TABS[1:3]+['Como funciona']+PROJECT_TABS[3:4]+['Integrações','Desafios e decisões']+PROJECT_TABS[4:]+['Demonstrações','Perguntas frequentes']


def public_project(data):
    hidden=set(data.get('privateFields',[]))|{'privateFields','privateNotes','publicationReviewed','_legacy'}
    return {k:([item for item in v if item.get('visibility')!='PRIVADO'] if k.startswith('sf') and isinstance(v,list) and all(isinstance(item,dict) for item in v) else v) for k,v in data.items() if k not in hidden}


def check_public_project(data):
    import json,ipaddress
    value=json.dumps(public_project(data),ensure_ascii=False)
    if re.search(r'(?i)(-----BEGIN .*PRIVATE KEY|(?:postgres(?:ql)?|mysql|mongodb|redis)://|(?:password|senha|secret|api[_-]?key|access[_-]?token)\s*[=:]\s*[^\s"<]+)',value):
        fail('Possível segredo no conteúdo público. Remova-o ou marque o campo como PRIVADO.')
    for address in re.findall(r'https?://[^\s"<>]+',value):
        p=urlparse(address);host=(p.hostname or '').lower()
        try: private=not ipaddress.ip_address(host).is_global
        except ValueError: private='.' not in host or host.endswith(('.local','.internal','.localhost'))
        if private or p.username or p.password or re.search(r'(?i)/(admin|wp-admin|internal|console)(/|$)',p.path) or re.search(r'(?i)(token|secret|password|key)=',p.query):
            fail('Link interno ou credencial não pode ser publicado.')
    for ip in re.findall(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])',value):
        try:
            if not ipaddress.ip_address(ip).is_global: fail('IP privado não pode ser publicado.')
        except ValueError: pass


SECTIONS=['projetos','consultoria','experiencia','competencias','artigos','videos']
ICONS=['database','brain','cloud','code','card','people','chart','cube','rocket','network','bolt']


def fail(message): raise HTTPException(422,message)


def url_ok(value):
    parsed=urlparse(value)
    return parsed.scheme in {'https','http'} and bool(parsed.hostname) and not parsed.username and not parsed.password


def youtube_id(value):
    if not value: return None
    p=urlparse(value)
    if p.scheme!='https' or p.username or p.port not in (None,443): return None
    host=(p.hostname or '').lower()
    if host=='youtu.be': result=p.path.strip('/')
    elif host in {'youtube.com','www.youtube.com','m.youtube.com'}:
        if p.path=='/watch': result=parse_qs(p.query).get('v',[''])[0]
        elif p.path.startswith(('/shorts/','/embed/','/live/')): result=p.path.split('/')[2]
        else: return None
    else: return None
    return result if re.fullmatch(r'[A-Za-z0-9_-]{11}',result) else None


def clean_html(value):
    return nh3.clean(value,tags={'figure','figcaption','b','i','p','br','h2','h3','h4','strong','em','u','s','sup','ul','ol','li','blockquote','pre','code','a','img','table','thead','tbody','tr','th','td','hr'},
        attributes={'a':{'href','title'},'img':{'src','alt'},'ol':{'start','type'},'li':{'id'},'th':{'colspan','rowspan'},'td':{'colspan','rowspan'}},
        url_schemes={'https','http'},link_rel='noopener noreferrer',
        attribute_filter=lambda tag,attr,val: None if (tag=='img' and attr=='src' and not re.fullmatch(r'/api/media/[a-f0-9-]{36}',val)) or (attr=='id' and not re.fullmatch(r'docx-note-\d+',val)) or (tag=='ol' and attr=='start' and not re.fullmatch(r'\d{1,5}',val)) or (tag=='ol' and attr=='type' and val not in {'1','a','A','i','I'}) else val)


def validate(module,data,publishing=False):
    schema=MODULES[module]; result={}
    if not isinstance(data,dict): fail('Dados inválidos.')
    for f in schema['fields']:
        k,kind=f['key'],f['kind']; v=data.get(k,f.get('default',False if kind=='boolean' else [] if kind in {'lines','links','metrics','gallery','references','services','order','smartblocks','smartmedia','finaldemos'} else ''))
        if kind=='finaldemos':
            v=final_demos(v,publishing)
        elif kind in {'smartblocks','smartmedia'}:
            v=validate_items(kind,v,publishing)
        elif kind=='boolean':
            if type(v)!=bool: fail(f"{f['label']}: valor inválido.")
        elif kind=='number':
            if type(v)!=int or not -10000<=v<=10000: fail(f"{f['label']}: número inválido.")
        elif kind in {'lines','gallery','references','order'}:
            if not isinstance(v,list) or len(v)>300 or any(not isinstance(x,str) or len(x)>10000 for x in v): fail(f"{f['label']}: lista inválida.")
            v=[x.strip() for x in v if x.strip()]
        elif kind in {'links','metrics','services'}:
            if not isinstance(v,list) or len(v)>30 or any(not isinstance(x,dict) for x in v): fail(f"{f['label']}: lista inválida.")
            keys={'label','url'} if kind=='links' else {'label','value'} if kind=='metrics' else {'title','shortTitle','tagline','description','icon','color'}
            v=[{key:str(item.get(key,''))[:3000] for key in keys} for item in v]
            if kind=='links' and any(not url_ok(x['url']) for x in v): fail('Informe links http(s) válidos.')
            if kind=='services' and any(x['icon'] not in ICONS or x['color'] not in ['blue','cyan','green','violet'] for x in v): fail('Ícone ou cor inválida.')
        else:
            if not isinstance(v,str): fail(f"{f['label']}: texto inválido.")
            limit=200000 if kind in {'richtext','finalrich'} else 30000 if kind=='textarea' else 1000
            if len(v)>limit: fail(f"{f['label']}: limite de {limit} caracteres.")
            v=v.strip()
            if kind=='richtext': v=clean_html(v)
            if kind=='finalrich': v=final_clean(v)
            if kind=='url' and v and not url_ok(v): fail(f"{f['label']}: URL inválida.")
            if kind=='email' and v:
                from email_validator import validate_email, EmailNotValidError
                try: v=validate_email(v,check_deliverability=False).normalized
                except EmailNotValidError: fail('E-mail inválido.')
            if kind=='select' and v and v not in f['options']: fail('Opção inválida.')
            if kind in {'date','month'} and v:
                try: date.fromisoformat(v+'-01' if kind=='month' else v)
                except ValueError: fail('Data inválida.')
            if kind=='youtube' and v:
                try: valid=youtube_id(v)
                except ValueError: valid=None
                if not valid: fail('Use uma URL HTTPS válida do YouTube.')
        if f.get('required') and not v: fail(f"Preencha {f['label']}.")
        result[k]=v
    if module=='projetos':
        private=data.get('privateFields',[])
        allowed={f['key'] for f in schema['fields']}-{'title','slug','visible','featured','sortOrder','publicationReviewed'}
        if not isinstance(private,list) or any(not isinstance(x,str) or x not in allowed for x in private): fail('Visibilidade de campo inválida.')
        result['privateFields']=sorted(set(private)|{'privateNotes'})
        if publishing:
            if result['slug']=='smartfamily' and not result['publicationReviewed']: fail('Revise os dados e arquivos públicos antes de publicar.')
            check_public_project(result)
    slug=result.get('slug','')
    if slug and not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug): fail('Slug: use letras minúsculas, números e hífens.')
    if module=='experiencias':
        if result['startMonth'] and result['endMonth'] and result['endMonth']<result['startMonth']: fail('O término não pode anteceder o início.')
        if result['current'] and (result['endMonth'] or result['endDateValidationRequired']): fail('Vínculo atual não pode ter término informado ou pendente.')
    if module=='perfil' and len(result['metrics'])!=4: fail('Preserve os quatro indicadores do Hero.')
    if module=='configuracoes':
        if sorted(result['sectionOrder'])!=sorted(SECTIONS): fail('A ordem deve conter cada seção exatamente uma vez.')
        if not 1<=result['retentionDays']<=730: fail('Retenção: de 1 a 730 dias.')
        if len(result['services'])!=4: fail('Preserve os quatro serviços do layout.')
        if any(x not in ['pt-BR','en'] for x in result['locales']): fail('Idiomas disponíveis: pt-BR e en.')
    if module=='videos':
        result['youtubeId']=youtube_id(result['youtubeUrl']) if result['youtubeUrl'] else None
        if result['duration'] and not re.fullmatch(r'(?:(?:\d{1,2}):)?\d{1,2}:[0-5]\d',result['duration']): fail('Duração inválida. Use mm:ss ou hh:mm:ss.')
        if publishing and not result['planned'] and not result['youtubeId']: fail('Cadastre a URL antes de publicar o vídeo.')
    if module=='artigos':
        if data.get('docxImported') is True:result['docxImported']=True
        words=len(re.sub('<[^>]+>',' ',result['body']).split())
        result['readingMinutes']=max(1,(words+199)//200)
        if publishing and not result['planned']:
            if result['readingMode']=='Externo':
                if not result['originalUrl']: fail('Informe a URL original para leitura externa.')
            elif words<3: fail('Escreva o artigo antes de publicar.')
    if publishing and module=='cases' and not result['confidentialityReviewed']: fail('Revise e autorize as informações confidenciais antes de publicar.')
    if publishing and module=='curriculo' and (not result['privacyReviewed'] or not result['file']): fail('Envie o currículo e confirme a revisão dos dados pessoais.')
    return result
