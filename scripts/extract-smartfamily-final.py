"""Extract supplied HTML as data, never execute its scripts."""
import base64,json,re,hashlib
from pathlib import Path
from html.parser import HTMLParser

class Node:
    def __init__(self,tag='',attrs=(),parent=None):self.tag=tag;self.attrs=dict(attrs);self.children=[];self.parent=parent
    def find(self,predicate):
        found=[]
        for c in self.children:
            if isinstance(c,Node):
                if predicate(c):found.append(c)
                found+=c.find(predicate)
        return found
    def html(self):
        from html import escape
        if self.tag=='#text':return self.attrs['text']
        attrs=''.join(' '+k+'="'+escape(v or '',quote=True)+'"' for k,v in self.attrs.items() if k not in ['style','id'])
        return '<'+self.tag+attrs+'>'+self.inner()+('</'+self.tag+'>' if self.tag not in ['img','br','meta','input','link'] else '')
    def inner(self):return ''.join(c.html() for c in self.children)

class Parser(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=False);self.root=Node('root');self.current=self.root
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs,self.current);self.current.children.append(node)
        if tag not in ['img','br','meta','input','link','hr']:self.current=node
    def handle_endtag(self,tag):
        p=self.current
        while p.parent:
            if p.tag==tag:self.current=p.parent;return
            p=p.parent
    def handle_data(self,text):self.current.children.append(Node('#text',[('text',text)],self.current))
    def handle_entityref(self,name):self.handle_data('&'+name+';')
    def handle_charref(self,name):self.handle_data('&#'+name+';')

source=Path(r'C:\Users\T-GAMER\Downloads\SmartFamily_Final (1).html').read_text(encoding='utf-8')
parser=Parser();parser.feed(source);root=parser.root
def first(tag,id=None):return root.find(lambda n:n.tag==tag and (id is None or n.attrs.get('id')==id))[0]
decoder=json.JSONDecoder()
def array(name):return decoder.raw_decode(source[source.index('const '+name+'=')+len('const '+name+'='):])[0]
messages=array('messages');items=array('items')
out=Path('backend/app/data/smartfamily-final');out.mkdir(parents=True,exist_ok=True)
assets=[]
def extract(uri,name):
    mime,encoded=uri.split(';base64,',1);extension={'image/png':'png','image/jpeg':'jpg','image/webp':'webp'}[mime[5:]]
    raw=base64.b64decode(encoded);filename=name+'.'+extension;(out/filename).write_bytes(raw)
    assets.append(dict(name=name,file=filename,mime=mime[5:],sha256=hashlib.sha256(raw).hexdigest(),size=len(raw)))
    return 'ASSET:'+name
logo=extract(first('nav').find(lambda n:n.tag=='img')[0].attrs['src'],'smartfamily-logo-oficial')
dashboard=extract(first('button','dashboard').find(lambda n:n.tag=='img')[0].attrs['src'],'smartfamily-dashboard-real')
infra=extract(first('button','infra-map').find(lambda n:n.tag=='img')[0].attrs['src'],'smartfamily-mapa-infraestrutura')
names=['criar-compromisso','consultar-agenda','criar-tarefa','listar-tarefas','consultar-despesas','resumo-financeiro','sua-familia','agendamento-voz']
demos=[]
for i,item in enumerate(items):
    demos.append(dict(title=item['title'],category=item['cat'],description=item['desc'],message=messages[i],image=extract(item['src'],'smartfamily-'+names[i]),visibility='PÚBLICO',order=i))
assert len(demos)==8
assert not re.search(r'^\s*[678]\.',messages[6],re.M),'Removed family entries unexpectedly present'
sections=[n for n in first('main').children if n.tag=='section']
data={'sfApproved':True,'sfFinalHero':first('section','produto').children[0].inner(),'sfFinalIntro':first('main').find(lambda n:n.attrs.get('class')=='intro')[0].inner(),'sfFinalDemos':demos,'sfFinalLogo':logo,'sfFinalDashboard':dashboard,'sfFinalMap':infra}
for key,id in [('sfFinalOverview','visao'),('sfFinalFeatures','funcionalidades'),('sfFinalChannels','canais'),('sfFinalFaq','perguntas')]:data[key]=first('section',id).inner()
data['sfFinalFlow']=next(n for n in sections if 'Da mensagem ao registro organizado.' in n.inner()).inner()
tech=first('section','tecnologia');tech.children=[n for n in tech.children if n.tag!='figure'];data['sfFinalTechnology']=tech.inner()
data['sfFinalEvolution']=next(n for n in sections if 'Uma base para ampliar' in n.inner()).inner()
data['sfFinalCta']=next(n for n in sections if n.attrs.get('class')=='end').inner()
(out/'content.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'manifest.json').write_text(json.dumps(assets,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'assets':len(assets),'demos':len(demos),'bytes':sum(x['size'] for x in assets),'fields':list(data)},ensure_ascii=False))
