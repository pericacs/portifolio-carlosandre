from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as ET
root=Path('.')
original=Path('docs/private/curriculo-original.docx')
public=Path('frontend/public/documents/carlos-andre-curriculo-publico.docx')
with zipfile.ZipFile(original) as z:
 source=ET.fromstring(z.read('word/document.xml'))
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
 assert len(source.findall('.//w:tbl',ns))==0, 'Review table extraction'
 assert len(source.findall('.//w:ins',ns))==0 and len(source.findall('.//w:del',ns))==0, 'Review tracked changes'
with zipfile.ZipFile(public) as z:
 xml='\n'.join(z.read(name).decode('utf-8') for name in z.namelist() if name.endswith('.xml'))
 assert 'Greysbelen' not in xml and '88085-500' not in xml
 assert 'Até Hoje' not in xml and 'vínculo atual não confirmado' in xml
 assert '\uf0b7' not in ''.join(ET.fromstring(z.read('word/document.xml')).itertext())
for p in Path('frontend/src').rglob('*'):
 if p.suffix in ['.tsx','.ts','.json','.css']:
  content=p.read_text(encoding='utf-8-sig')
  assert 'Greysbelen' not in content and '88085-500' not in content
cv=json.loads(Path('frontend/src/data/curriculum.json').read_text(encoding='utf-8'))
assert len(cv['experiences'])==9 and len(cv['skills'])==7
assert cv['experiences'][0]['endDateValidationRequired'] and cv['experiences'][0]['endMonth'] is None
assert cv['experiences'][1]['startMonth']=='2025-01' and cv['experiences'][1]['endMonth']=='2025-11'
assert len(cv['certifications'])==1
report={'sourceOriginalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'publicDocxSha256':hashlib.sha256(public.read_bytes()).hexdigest(),'privacyChecks':'passed','experiences':9,'skillGroups':7,'cases':9,'tables':0,'trackedChanges':0,'compassEndDate':'pending-owner-validation'}
Path('docs/screenshots/content-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
