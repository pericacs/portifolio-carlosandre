import zipfile, xml.etree.ElementTree as ET, json
from pathlib import Path
with zipfile.ZipFile('docs/private/curriculo-original.docx') as z:
 root=ET.fromstring(z.read('word/document.xml'))
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
 lines=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in root.findall('.//w:body/w:p',ns)]
 Path('docs/private/curriculo-extracted.json').write_text(json.dumps(lines,ensure_ascii=False,indent=2),encoding='utf-8')
 for i,line in enumerate(lines):
  if i>=18 and line.strip(): print(f'{i}: {line}')
