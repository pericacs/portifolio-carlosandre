from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree
source=Path('docs/private/curriculo-original.docx')
output=Path('frontend/public/documents/carlos-andre-curriculo-publico.docx')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
redacted=False
updated=False
with ZipFile(source) as src, ZipFile(output,'w',ZIP_DEFLATED) as dst:
 for item in src.infolist():
  raw=src.read(item.filename)
  if item.filename=='word/document.xml':
   root=etree.fromstring(raw)
   for run in root.findall('.//w:t',ns):
    if run.text: run.text=run.text.replace('\uf0b7','•')
   for p in root.findall('.//w:body/w:p',ns):
    text=''.join(p.itertext())
    if 'Rua Luis da Costa' in text:
     p.getparent().remove(p);redacted=True
    elif 'Junho/2024' in text and 'Até Hoje' in text:
     runs=p.findall('.//w:t',ns)
     runs[0].text='Junho/2024 – Término em validação (vínculo atual não confirmado)'
     for run in runs[1:]:run.text=''
     updated=True
   raw=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
  if item.filename=='docProps/core.xml':
   root=etree.fromstring(raw)
   for child in list(root):
    if etree.QName(child).localname in ('creator','lastModifiedBy','description','keywords'):root.remove(child)
   raw=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
  dst.writestr(item,raw)
assert redacted and updated
with ZipFile(output) as z:
 for name in z.namelist():
  if name.endswith('.xml'):
   xml=z.read(name).decode('utf-8')
   assert '88085-500' not in xml and 'Greysbelen' not in xml
print('Public copy verified: residential address removed; Compass end date flagged. Original unchanged.')
