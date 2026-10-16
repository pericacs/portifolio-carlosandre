"""Extract only author article blocks from the supplied public LinkedIn pages."""
from html.parser import HTMLParser
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen
import json,hashlib
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'backend/app/data/articles'
DEST.mkdir(exist_ok=True)
class Node:
 def __init__(self,tag='',attrs=()):self.tag=tag;self.attrs=dict(attrs);self.children=[]
 def find(self,predicate):
  if predicate(self):return self
  for c in self.children:
   if isinstance(c,Node):
    found=c.find(predicate)
    if found:return found
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.root=Node();self.stack=[self.root]
 def handle_starttag(self,t,a):
  n=Node(t,a);self.stack[-1].children.append(n)
  if t not in {'img','br','hr','meta','link','input','source','wbr','area','base','embed','param','track','col'}:self.stack.append(n)
 def handle_endtag(self,t):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i].tag==t:self.stack=self.stack[:i];break
 def handle_data(self,d):self.stack[-1].children.append(d)
assets=[]
def asset(url):
 from urllib.parse import urlparse
 assert urlparse(url).hostname=='media.licdn.com'
 raw=urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read()
 digest=hashlib.sha256(raw).hexdigest()
 import io
 with Image.open(io.BytesIO(raw)) as im:
  fmt=im.format;w,h=im.size;im.verify()
 ext={'JPEG':'.jpg','PNG':'.png','WEBP':'.webp'}[fmt];name=digest[:20]+ext
 (DEST/name).write_bytes(raw)
 if not any(x['file']==name for x in assets):assets.append({'file':name,'sha256':digest,'width':w,'height':h,'mime':'image/'+('jpeg' if fmt=='JPEG' else fmt.lower())})
 return 'ASSET:'+name
ALLOWED={'p','br','h2','h3','h4','strong','b','em','i','ul','ol','li','blockquote','pre','code','a','img','table','thead','tbody','tr','th','td','hr','figure','figcaption'}
def render(n):
 if isinstance(n,str):return escape(n)
 if n.tag in {'script','style'}:return ''
 if n.tag=='img':
  url=n.attrs.get('data-delayed-url') or n.attrs.get('src')
  return '<img src="'+asset(url)+'" alt="'+escape(n.attrs.get('alt',''),quote=True)+'">'
 content=''.join(render(c) for c in n.children)
 if n.tag not in ALLOWED:return content
 attrs=''
 if n.tag=='a' and n.attrs.get('href'):attrs=' href="'+escape(n.attrs['href'],quote=True)+'"'
 return '<'+n.tag+attrs+'>'+content+('' if n.tag in {'br','hr'} else '</'+n.tag+'>')
urls=['https://pt.linkedin.com/pulse/engenharia-de-dados-aplicada-ao-split-payment-do-bem-carlos-andr%C3%A9-ihn5f','https://pt.linkedin.com/pulse/split-payment-do-bem-e-mal-carlos-andr%C3%A9-cardoso-dos-santos-uneie']
titles=['Engenharia de dados aplicada ao Split Payment do Bem','Split Payment do bem e Split Payment do mal']
slugs=['engenharia-de-dados-aplicada-ao-split-payment-do-bem','split-payment-do-bem-e-split-payment-do-mal']
summaries=['Uma proposta de arquitetura para acompanhar pagamentos desde as fontes até a conciliação, com camadas Bronze, Silver e Gold, regras de repasse e apoio de IA na investigação de divergências.','A diferença entre dividir pagamentos entre parceiros e segregar tributos, com exemplos sobre repasses, previsibilidade e os efeitos do calendário de recolhimento no caixa.']
rows=[]
for i in range(2):
 parser=Parser();parser.feed((ROOT/f'docs/references/linkedin-article-{i+1}.html').read_text(encoding='utf-8'))
 body=parser.root.find(lambda n:n.attrs.get('data-test-id')=='article-content-blocks');assert body
 cover=parser.root.find(lambda n:n.attrs.get('property')=='og:image');assert cover
 content=render(body);assert len(content)>5000
 rows.append(dict(title=titles[i],slug=slugs[i],description=summaries[i],originalUrl=urls[i],body=content,cover=asset(cover.attrs['content']),contentType='Artigo',readingMode='Interno',publishedDate=['2026-10-13','2026-10-07'][i],categories=[['Engenharia de Dados','Payments','IA'],['Payments']][i],featured=True,spotlight=i==0,visible=True,planned=False,sortOrder=i,author='Carlos André Cardoso dos Santos'))
insights=[('ia-na-conciliacao-financeira','IA na conciliação financeira: onde analisar, recomendar e executar','inteligenciaartificial-conciliacaofinanceira-activity-7511382841717514242-rK42',['IA','Payments']),('quatro-golpes-com-cartoes','Quatro golpes com cartões e como se proteger','payments-cartoes-prevencaoafraudes-activity-7512850100818411520-Eu4t',['Payments','Segurança']),('idempotencia-em-pagamentos','Idempotência em pagamentos: evitando baixas duplicadas','payments-pix-engenhariadedados-activity-7510324775718916096-tule',['Engenharia de Dados','Payments'])]
for i,(slug,title,path,categories) in enumerate(insights):rows.append(dict(title=title,slug=slug,description='',originalUrl='https://pt.linkedin.com/posts/carlos-andr%C3%A9-cardoso-dos-santos-4159b937_'+path,body='',contentType='Insight',readingMode='Externo',publishedDate='',categories=categories,featured=i==0,spotlight=False,visible=True,planned=False,sortOrder=i+2,author='Carlos André Cardoso dos Santos'))
(DEST/'content.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(DEST/'manifest.json').write_text(json.dumps(assets,indent=2),encoding='utf-8')
print('Extracted',len(rows),'entries;',len(assets),'original images. Body lengths:',[len(x['body']) for x in rows[:2]])
