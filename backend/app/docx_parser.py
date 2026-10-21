"""Bounded OOXML article extraction. No network, Office execution, or persistence."""
import hashlib
import html
import io
import posixpath
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit,unquote
from uuid import uuid4
from defusedxml import ElementTree as safe_xml
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import parse_xml
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from PIL import Image,UnidentifiedImageError
from app.cms_schema import clean_html,validate

MAX_UPLOAD=8*1024*1024
MAX_EXPANDED=50*1024*1024
MAX_IMAGES=32
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','a':'http://schemas.openxmlformats.org/drawingml/2006/main','v':'urn:schemas-microsoft-com:vml'}

class DocxError(ValueError): pass

def raster(raw):
    if not raw or len(raw)>MAX_UPLOAD:raise DocxError('Imagem vazia ou maior que 8 MB.')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            width,height=image.size;fmt=image.format
            if width*height>25_000_000:raise DocxError('Imagem excede 25 megapixels.')
            image.verify()
        if fmt not in {'PNG','JPEG','WEBP'}:raise DocxError('Use PNG, JPEG ou WebP rasterizado.')
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as error:raise DocxError('Imagem inválida.') from error
    return {'width':width,'height':height,'mime':{'PNG':'image/png','JPEG':'image/jpeg','WEBP':'image/webp'}[fmt],'extension':{'PNG':'.png','JPEG':'.jpg','WEBP':'.webp'}[fmt],'sha256':hashlib.sha256(raw).hexdigest()}

def plain(value):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>',' ',value))).strip()
def slugify(value):return re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower()).strip('-')[:180]
def safe_link(value):
    try:
        p=urlsplit(value)
        return p.scheme in {'https','http'} and bool(p.hostname) and not p.username and not p.password and not re.search(r'[\x00-\x20]',value)
    except ValueError:return False

@dataclass
class ParsedArticle:
    data:dict
    images:list
    warnings:list
    source_hash:str
    sections:int

class Extractor:
    def __init__(self,blob,filename,defaults):
        if not filename.lower().endswith('.docx') or not blob.startswith(b'PK\x03\x04'):raise DocxError('Envie um arquivo DOCX válido.')
        if not blob or len(blob)>MAX_UPLOAD:raise DocxError('O DOCX deve ter até 8 MB.')
        self.blob=blob;self.defaults=defaults;self.warnings=[];self.images=[];self.asset_map={};self.notes=[];self.note_numbers={};self.blocks_count=0
        try:
            self.zip=zipfile.ZipFile(io.BytesIO(blob));infos=self.zip.infolist();names=[i.filename for i in infos]
            if len(infos)>1000 or len(set(names))!=len(names) or sum(i.file_size for i in infos)>MAX_EXPANDED:raise DocxError('Limites de descompressão do DOCX excedidos.')
            for i in infos:
                name=i.filename
                if name.startswith('/') or '\\' in name or '..' in name.split('/') or i.flag_bits&1 or i.compress_type not in {zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED} or (i.external_attr>>16)&0o170000==0o120000:raise DocxError('Estrutura ZIP insegura.')
                if i.file_size>1024*1024 and i.file_size>max(1,i.compress_size)*300:raise DocxError('Taxa de compressão excessiva.')
                if i.file_size>MAX_UPLOAD and not name.endswith(('.xml','.rels')):raise DocxError('Arquivo incorporado excessivamente grande.')
                if i.file_size>8*1024*1024 and name.endswith(('.xml','.rels')):raise DocxError('XML excessivamente grande.')
                if any(x in name.lower() for x in ['vbaproject','activex/','embeddings/']) or name.lower().endswith(('.exe','.js','.html','.htm','.bin')):raise DocxError('Macros, objetos ou conteúdo ativo não são aceitos.')
                if name.endswith(('.xml','.rels')):
                    tree=safe_xml.fromstring(self.zip.read(i))
                    if sum(1 for _ in tree.iter())>100000:raise DocxError('XML com elementos excessivos.')
                    if name=='[Content_Types].xml' and any('macroenabled' in str(x.attrib).lower() for x in tree):raise DocxError('Documento com macros não é aceito.')
            if not {'[Content_Types].xml','word/document.xml','_rels/.rels'}.issubset(names):raise DocxError('Estrutura DOCX incompleta.')
            if self.zip.testzip():raise DocxError('DOCX corrompido.')
            self.doc=Document(io.BytesIO(blob))
        except DocxError:raise
        except Exception as error:raise DocxError('DOCX corrompido ou XML inseguro.') from error
        self.relations={};self.numbering={}
        for name in names:
            if not name.endswith('.rels'):continue
            part=posixpath.join(posixpath.dirname(posixpath.dirname(name)),posixpath.basename(name)[:-5])
            rels={}
            for r in safe_xml.fromstring(self.zip.read(name)):
                if 'altChunk' in r.get('Type','') or r.get('Type','').endswith(('/oleObject','/package')):raise DocxError('Conteúdo ativo incorporado não é aceito.')
                rels[r.get('Id')]=dict(r.attrib)
            self.relations[part]=rels
        if 'word/numbering.xml' in names:
            tree=safe_xml.fromstring(self.zip.read('word/numbering.xml'))
            abstracts={a.get(qn('w:abstractNumId')):a for a in tree.findall('w:abstractNum',NS)}
            for num in tree.findall('w:num',NS):
                ref=num.find('w:abstractNumId',NS);abstract=abstracts.get(ref.get(qn('w:val')) if ref is not None else '')
                if abstract is None:continue
                for lvl in abstract.findall('w:lvl',NS):
                    fmt=lvl.find('w:numFmt',NS);start=lvl.find('w:start',NS);index=lvl.get(qn('w:ilvl'),'0')
                    override=num.find(f"w:lvlOverride[@w:ilvl='{index}']/w:startOverride",NS)
                    self.numbering[(num.get(qn('w:numId')),index)]=(fmt.get(qn('w:val'),'decimal') if fmt is not None else 'decimal',int((override if override is not None else start).get(qn('w:val'),'1')) if override is not None or start is not None else 1)

    def warn(self,message):
        if message not in self.warnings:self.warnings.append(message)

    def image(self,rid,part):
        relation=self.relations.get(part,{}).get(rid)
        if not relation or relation.get('TargetMode')=='External':self.warn('Imagem externa ou relação ausente: revisão necessária. Nenhum recurso externo foi baixado.');return ''
        target=posixpath.normpath(posixpath.join(posixpath.dirname(part),unquote(relation.get('Target',''))))
        if not target.startswith('word/media/') or target not in self.zip.namelist():raise DocxError('Relação de imagem inválida.')
        if target in self.asset_map:return self.asset_map[target]['id']
        if len(self.images)>=MAX_IMAGES:raise DocxError('O documento excede 32 imagens.')
        raw=self.zip.read(target)
        try:
            with Image.open(io.BytesIO(raw)) as im:
                width,height=im.size;fmt=im.format
                if width<1 or height<1 or width*height>25_000_000:raise DocxError('Imagem excede 25 megapixels.')
                im.verify()
            if fmt not in {'PNG','JPEG','WEBP','GIF','TIFF'}:raise DocxError('Formato de imagem não suportado.')
            if fmt in {'GIF','TIFF'}:
                with Image.open(io.BytesIO(raw)) as im:
                    output=io.BytesIO();im.convert('RGBA').save(output,format='PNG');raw=output.getvalue();fmt='PNG'
                self.warn('GIF/TIFF convertido para PNG estático; revise a imagem e eventuais páginas/quadros adicionais.')
        except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as error:raise DocxError('Imagem incorporada inválida ou não rasterizada (EMF/WMF/SVG não suportados).') from error
        if len(raw)>MAX_UPLOAD:raise DocxError('Imagem extraída excede 8 MB.')
        identifier=str(uuid4());ext={'PNG':'.png','JPEG':'.jpg','WEBP':'.webp'}[fmt]
        asset={'id':identifier,'key':identifier+ext,'name':posixpath.basename(target),'mime':{'PNG':'image/png','JPEG':'image/jpeg','WEBP':'image/webp'}[fmt],'width':width,'height':height,'sha256':hashlib.sha256(raw).hexdigest(),'blob':raw,'caption':''}
        self.images.append(asset);self.asset_map[target]=asset;return identifier

    def inline(self,node,part='word/document.xml'):
        tag=node.tag.rsplit('}',1)[-1]
        if tag in {'del','moveFrom','instrText','pPr','rPr','lastRenderedPageBreak'}:return ''
        if tag=='t':
            text=node.text or ''
            if any(parent.tag==qn('w:hyperlink') for parent in node.iterancestors()):return html.escape(text)
            pieces=[];position=0
            for match in re.finditer(r'https?://[^\s<>"\x00-\x1f]+',text):
                url=match.group().rstrip('.,;:!?')
                while url.endswith(')') and url.count(')')>url.count('('):url=url[:-1]
                pieces.append(html.escape(text[position:match.start()]))
                pieces.append(f'<a href="{html.escape(url,quote=True)}">{html.escape(url)}</a>' if safe_link(url) else html.escape(url))
                position=match.start()+len(url)
            pieces.append(html.escape(text[position:]));return ''.join(pieces)
        if tag=='tab':return ' '
        if tag in {'br','cr'}:return '<br/>' if node.get(qn('w:type'))!='page' else ''
        if tag in {'blip','imagedata'}:
            rid=node.get(qn('r:embed')) or node.get(qn('r:id'));identifier=self.image(rid,part) if rid else ''
            if not identifier:self.warn('Imagem vinculada externamente não foi importada.');return ''
            return f'\x00IMAGE:{identifier}\x00'
        if tag in {'footnoteReference','endnoteReference'}:
            key=(tag,node.get(qn('w:id')))
            if key not in self.note_numbers:self.note_numbers[key]=len(self.note_numbers)+1;self.notes.append(key)
            number=self.note_numbers[key];return f'<sup><a href="#docx-note-{number}">[{number}]</a></sup>'
        if tag=='hyperlink':
            content=''.join(self.inline(c,part) for c in node);rel=self.relations.get(part,{}).get(node.get(qn('r:id')),{});target=rel.get('Target','')
            if safe_link(target):return f'<a href="{html.escape(target,quote=True)}">{content}</a>'
            self.warn('Link interno ou inseguro mantido somente como texto; revisão necessária.');return content
        if tag in {'object','altChunk','control'}:raise DocxError('Objeto ativo não é aceito no corpo.')
        content=''.join(self.inline(c,part) for c in node)
        if tag=='r':
            props=node.find('w:rPr',NS)
            for key,wrapper,attribute in [('i','em','italic'),('b','strong','bold')]:
                prop=props.find('w:'+key,NS) if props is not None else None
                enabled=prop.get(qn('w:val'),'1') not in {'0','false','off'} if prop is not None else None
                if enabled is None:
                    try:
                        parent=node
                        while parent is not None and parent.tag!=qn('w:p'):parent=parent.getparent()
                        if parent is not None:
                            paragraph=Paragraph(parent,self.doc);run=Run(node,paragraph)
                            for style in [run.style,paragraph.style]:
                                for _ in range(12):
                                    if style is None:break
                                    enabled=getattr(style.font,attribute)
                                    if enabled is not None:break
                                    style=style.base_style
                                if enabled is not None:break
                    except (AttributeError,KeyError):pass
                if enabled:content=f'<{wrapper}>{content}</{wrapper}>'
        return content

    def paragraph(self,node,part='word/document.xml'):
        paragraph=Paragraph(node,self.doc);style=paragraph.style;style_name=(style.name or '').lower() if style else ''
        inherited=[];base=style
        for _ in range(12):
            if base is None:break
            inherited.append((base.name or '').lower());base=base.base_style
        style_chain=' '.join(inherited)
        text=self.inline(node,part);raw=plain(text.replace('\x00',' '));props=node.find('w:pPr',NS)
        if not raw and not text.strip():return []
        heading=re.search(r'(?:heading|t[ií]tulo|cabe[cç]alho)\s*([1-6])',style_chain)
        outline=props.find('w:outlineLvl',NS) if props is not None else None
        level=min(4,int(heading[1])+1) if heading else min(4,int(outline.get(qn('w:val')))+2) if outline is not None and outline.get(qn('w:val'),'9') in {'0','1','2'} else 2 if style_name in {'section head','section heading'} else 3 if style_name in {'mini head','subheading','subhead'} else None
        kind='heading' if level else 'subtitle' if 'subtitle' in style_name or 'subtítulo' in style_name or 'subtitulo' in style_name else 'title' if style_name in {'title','título','titulo','article title'} else 'caption' if 'caption' in style_name or 'legenda' in style_name or re.match(r'^(Figura|Imagem|Diagrama|Visual)\s+\d+\s*[:.•–-]',raw,re.I) else 'quote' if 'quote' in style_name or 'cita' in style_name else 'p'
        numbering=props.find('w:numPr',NS) if props is not None else None
        if numbering is None and style is not None and style.element.pPr is not None:numbering=style.element.pPr.find('w:numPr',NS)
        attrs={}
        if numbering is not None and not level:
            num=numbering.find('w:numId',NS);ilvl=numbering.find('w:ilvl',NS)
            numid=num.get(qn('w:val'),'0') if num is not None else '0';depth=ilvl.get(qn('w:val'),'0') if ilvl is not None else '0'
            if numid!='0':
                fmt,start=self.numbering.get((numid,depth),('bullet' if 'bullet' in style_name else 'decimal',1));kind='list';attrs={'depth':min(8,int(depth)),'num':numid,'format':fmt,'start':max(1,min(start,10000))}
        result=[]
        for chunk in re.split(r'(\x00IMAGE:[a-f0-9-]{36}\x00)',text):
            if chunk.startswith('\x00IMAGE:'):result.append({'kind':'figure','image':chunk[7:-1],'html':'','text':''})
            elif plain(chunk):result.append({'kind':kind,'html':chunk,'text':plain(chunk),'level':level,**attrs})
        return result

    def blocks(self,parent,part='word/document.xml',depth=0):
        if depth>8:raise DocxError('Estrutura editorial excessivamente aninhada.')
        result=[]
        for node in parent:
            self.blocks_count+=1
            if self.blocks_count>6000:raise DocxError('Documento com blocos excessivos.')
            tag=node.tag.rsplit('}',1)[-1]
            if tag=='p':result.extend(self.paragraph(node,part))
            elif tag=='tbl':
                rows=[];cells=0
                for tr in node.findall('w:tr',NS):
                    values=[]
                    for tc in tr.findall('w:tc',NS):
                        cells+=1
                        if cells>2000:raise DocxError('Tabela excessivamente grande.')
                        span=tc.find('w:tcPr/w:gridSpan',NS);vertical=tc.find('w:tcPr/w:vMerge',NS)
                        if vertical is not None:self.warn('Tabela com mesclagem vertical: revise a estrutura das células.')
                        colspan=max(1,min(32,int(span.get(qn('w:val'),'1')))) if span is not None else 1
                        values.append(f'<td colspan="{colspan}">{self.render(self.blocks(tc,part,depth+1))}</td>')
                    rows.append('<tr>'+''.join(values)+'</tr>')
                table_html='<table><tbody>'+''.join(rows)+'</tbody></table>'
                if cells==1 and plain(table_html).startswith(('“','"')):table_html='<blockquote>'+re.search(r'<td[^>]*>(.*)</td>',table_html,re.S)[1]+'</blockquote>'
                result.append({'kind':'raw','html':table_html,'text':''})
            elif tag in {'sdt','sdtContent','ins','moveTo'}:result.extend(self.blocks(node,part,depth+1))
            elif tag in {'altChunk','object'}:raise DocxError('Conteúdo ativo não suportado.')
        return result

    def render(self,blocks):
        out=[];i=0
        def listing(index,depth):
            first=blocks[index];fmt=first['format'];tag='ul' if fmt=='bullet' else 'ol';types={'lowerLetter':'a','upperLetter':'A','lowerRoman':'i','upperRoman':'I'}
            result=f'<{tag}'+(f' start="{first["start"]}" type="{types.get(fmt,"1")}"' if tag=='ol' else '')+'>'
            while index<len(blocks) and blocks[index]['kind']=='list' and blocks[index]['depth']==depth and blocks[index]['num']==first['num'] and blocks[index]['format']==fmt:
                result+='<li>'+blocks[index]['html'];index+=1
                while index<len(blocks) and blocks[index]['kind']=='list' and blocks[index]['depth']>depth:
                    child,index=listing(index,blocks[index]['depth']);result+=child
                result+='</li>'
            return result+f'</{tag}>',index
        while i<len(blocks):
            b=blocks[i];kind=b['kind']
            if kind=='list':value,i=listing(i,b['depth']);out.append(value);continue
            if kind=='figure':
                caption=''
                if i+1<len(blocks) and blocks[i+1]['kind']=='caption':caption=blocks[i+1]['html'];i+=1
                elif out and i>0 and blocks[i-1]['kind']=='caption':caption=blocks[i-1]['html'];out.pop()
                asset=next(x for x in self.images if x['id']==b['image']);asset['caption']=plain(caption)
                out.append(f'<figure><img src="/api/media/{asset["id"]}" alt="{html.escape(plain(caption),quote=True)}"/>'+('<figcaption>'+caption+'</figcaption>' if caption else '')+'</figure>')
            elif kind=='raw':out.append(b['html'])
            else:
                tag=f'h{b["level"]}' if kind=='heading' else 'blockquote' if kind=='quote' else 'p';out.append(f'<{tag}>{b["html"]}</{tag}>')
            i+=1
        return ''.join(out)

    def extract(self):
        blocks=self.blocks(self.doc.element.body);meta={};remove=set()
        cp=self.doc.core_properties
        title_index=next((i for i,b in enumerate(blocks[:12]) if b['kind']=='title'),None)
        title=blocks[title_index]['text'][:300] if title_index is not None else cp.title.strip()[:300] if cp.title else ''
        if title_index is not None:
            remove.add(title_index)
            for i,b in enumerate(blocks[:title_index]):
                if b['kind']=='figure' and i==0:remove.add(i)
                if re.match(r'^(ARTIGO|INSIGHT|ESPECIAL)\b',b['text']) and '•' in b['text']:
                    meta['categories']=[x.strip() for x in b['text'].split('•',1)[1].split(',') if x.strip()];remove.add(i)
        for index,b in enumerate(blocks):
            if title_index is not None and index<=title_index:continue
            if index>12:break
            if b['kind']=='figure':continue
            if b['kind'] in {'raw','list'} or b['kind']=='heading' and title:break
            text=b['text']
            if not title:title=text[:300];remove.add(index);continue
            if b['kind']=='title' or text.casefold()==title.casefold():remove.add(index);continue
            if b['kind']=='subtitle':meta['subtitle']=text[:1000];remove.add(index);continue
            match=re.match(r'^(?:Autor(?:a)?|Por)\s*[:–-]?\s+(.+)$',text,re.I)
            if match:
                signature=match[1].split('|',1);meta['author']=signature[0].strip()[:300];remove.add(index)
                if len(signature)>1:self.warn('Qualificação da assinatura extraída para revisão: '+signature[1].strip())
                continue
            match=re.match(r'^(Tags?|Palavras.chave|Categorias?|Assuntos?)\s*:\s*(.+)$',text,re.I)
            if match:meta['tags' if match[1].lower().startswith(('tag','palavra')) else 'categories']=[x.strip() for x in re.split('[,;]',match[2]) if x.strip()][:30];remove.add(index);continue
            match=re.match(r'^(?:Data(?: editorial)?|Publicado em)\s*:\s*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})$',text,re.I)
            if match:
                try:value=match[1];meta['publishedDate']=date.fromisoformat(value if '-' in value else '-'.join(reversed(value.split('/')))).isoformat();remove.add(index)
                except ValueError:self.warn('Data editorial inválida: revisão necessária.')
                continue
            if not meta.get('subtitle') and index<(title_index+3 if title_index is not None else 3) and len(text)<240 and not text.endswith(('.',':')) and b['kind']=='p' and '<a ' not in b['html']:meta['subtitle']=text;remove.add(index);self.warn('Subtítulo sugerido pela posição no documento: confirme na revisão.');continue
            break
        if not title:raise DocxError('O documento não possui texto editorial.')
        author=meta.get('author') or cp.author.strip()
        if author.lower() in {'python-docx','user','administrator','microsoft office user','openai'}:author=''
        if not author:author=self.defaults.get('author','');self.warn('Autoria ausente: revisão necessária.' if not author else 'Autor preenchido pelo padrão configurado; confirme na revisão.')
        if not meta.get('publishedDate'):
            update=next((re.search(r'(?:Texto\s+)?(?:atualizado|atualizada|revisado|revisada)\s+em\s+(\d{2}/\d{2}/\d{4})',b['text'],re.I) for b in blocks if re.search(r'(?:atualizado|atualizada|revisado|revisada)\s+em\s+\d{2}/\d{2}/\d{4}',b['text'],re.I)),None)
            if update:
                try:meta['publishedDate']=date.fromisoformat('-'.join(reversed(update[1].split('/')))).isoformat();self.warn('Data encontrada em nota de atualização; confirme seu uso como data de publicação.')
                except ValueError:self.warn('Data de atualização inválida; revisão necessária.')
            if not meta.get('publishedDate'):self.warn('Data editorial ausente; nenhuma data foi inventada.')
        remaining=[b for i,b in enumerate(blocks) if i not in remove];body=self.render(remaining)
        for key in self.notes:
            tag,identifier=key;name='word/footnotes.xml' if tag=='footnoteReference' else 'word/endnotes.xml';number=self.note_numbers[key]
            if name not in self.zip.namelist():self.warn('Nota sem conteúdo disponível: revisão necessária.');continue
            # All XML was already validated with defusedxml; use OOXML element
            # classes here so paragraph/run style inheritance also works in notes.
            tree=parse_xml(self.zip.read(name));note=next((n for n in tree if n.get(qn('w:id'))==identifier),None)
            if note is not None:body+=f'<ol start="{number}"><li id="docx-note-{number}">'+self.render(self.blocks(note,name))+'</li></ol>'
        summary=next((b['text'] for b in remaining if b['kind']=='p' and len(b['text'])>40),'')
        summary=(summary[:277].rsplit(' ',1)[0]+'…') if len(summary)>280 else summary
        if not summary:self.warn('Resumo ausente: revisão necessária.')
        categories=meta.get('categories') or ([self.defaults['category']] if self.defaults.get('category') else [])
        if not categories:self.warn('Categoria ausente: revisão necessária.')
        hashtags=list(dict.fromkeys(tag for b in remaining if b['text'].startswith('#') for tag in re.findall(r'#([\w]+)',b['text'])))[:30]
        tags=meta.get('tags') or hashtags or ([x.strip() for x in cp.keywords.split(',') if x.strip()] if cp.keywords else self.defaults.get('tags',[]))
        if not tags:self.warn('Tags ausentes: revisão necessária.')
        if self.images:self.warn('Confirme a imagem de capa e as legendas antes de publicar.')
        data=validate('artigos',{'title':title,'slug':slugify(title) or 'artigo','subtitle':meta.get('subtitle',''),'author':author,'publishedDate':meta.get('publishedDate',''),'description':summary,'category':categories[0] if categories else '', 'categories':categories,'tags':tags,'body':clean_html(body),'cover':'/api/media/'+self.images[0]['id'] if self.images else '', 'gallery':['/api/media/'+a['id'] for a in self.images[1:]],'seoTitle':title[:60],'metaDescription':summary[:160],'readingMode':'Interno','planned':False,'featured':False,'visible':True})
        self.zip.close()
        numbered=sum(b['kind']=='heading' and bool(re.match(r'^\d+[.)]\s',b['text'])) for b in remaining)
        return ParsedArticle(data,self.images,self.warnings,hashlib.sha256(self.blob).hexdigest(),numbered or sum(b['kind']=='heading' for b in remaining))

def parse_docx(blob,filename,defaults=None):
    try:return Extractor(blob,filename,defaults or {}).extract()
    except DocxError:raise
    except Exception as error:raise DocxError('Documento não suportado ou estrutura inválida; nenhum conteúdo foi salvo.') from error
