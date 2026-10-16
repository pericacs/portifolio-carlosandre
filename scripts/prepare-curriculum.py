"""Explicit extraction from the supplied CV; never publishes its personal header.

Source paragraphs are retained for editorial traceability. No database write.
"""
import json
from pathlib import Path

source = json.loads(Path('docs/private/curriculo-extracted.json').read_text(encoding='utf-8'))
assert len(source) >= 466 and source[16].startswith('COMPASS UOL') and source[166].strip() == 'FASTCONNECT', 'Source changed: review paragraph mapping before extraction.'
def lines(start, end):
    return [line.strip().lstrip(' ').rstrip() for line in source[start:end] if line.strip()]
def exp(id, company, wordmark, role, period, description, tags, narrative, responsibilities, results, technologies, pending=False):
    return dict(id=id,company=company,wordmark=wordmark,role=role,period=period,description=description,tags=tags,
        narrative=lines(*narrative),responsibilities=lines(*responsibilities),results=lines(*results),technologies=technologies,
        endDateValidationRequired=pending,featured=True,visible=True,sourceParagraphs=list(range(narrative[0],results[1])))

data = {
 'schemaVersion':1,
 'source':{'file':'curriculo-original.docx','kind':'owner-provided-cv','verifiedExternally':False},
 'about':lines(6,12),'objective':source[14].strip(),
 'experiences':[
 exp('compass-cef','Compass UOL / Caixa Econômica Federal','CAIXA',source[17].strip(),'Jun/2024 · término em validação','Mais de 9 bilhões de registros processados e redução superior a 80% no tempo das cargas analíticas.',['Dados','Databricks','Arquitetura'],(19,25),(26,40),(41,48),['Databricks','Apache Spark','Python','PySpark','SQL Server','PostgreSQL','Oracle','Azure Data Factory','Terraform','GitHub Actions'],True),
 exp('rpe-tech','RPE.tech / Fiabilité Tech','RPE.tech','Senior Data Engineer','Jan/2025 – Nov/2025','RPE Analisa: cerca de 12 milhões de registros por dia e informações disponíveis em D+1.',['Spark','Databricks','APIs'],(51,59),(61,80),(82,89),[t.strip() for t in source[104].split('•')]),
 exp('alibin','Alibin','alibin',source[107].strip(),'Jan/2021 – Jun/2024','Liderança tecnológica, estruturação de SCD, plataformas financeiras, dados e IA.',['CTO','Banking','Cloud'],(109,117),(118,155),(156,164),['Python','Django','Databricks','Apache Spark','PySpark','Azure Data Factory','PostgreSQL','SQL Server','Oracle','AWS','Azure','GCP','Terraform','GitHub Actions','AWS CloudFormation']),
 exp('fastconnect','Fastconnect','fastconnect','Founder · CEO · Principal Solution Architect','Jan/2014 – Dez/2020','Plataforma de subadquirência e soluções para Winker, Khronos, Top Clínicas e outros clientes.',['Founder','Payments','SaaS'],(169,176),(208,247),(249,256),['APIs REST','Microsserviços','Apache Spark','Python','PostgreSQL','SQL Server','Oracle','MySQL','AWS','Azure','Terraform','Git','GitHub','Jira']),
 exp('manager-systems','Manager Systems','Manager Systems',source[258].strip(),'Jan/2013 – Dez/2013','ERP para saúde, arquitetura de banco de dados e evolução de módulos corporativos.',['ERP','Saúde','Dados'],(260,264),(266,277),(277,277),[t.strip() for t in source[279].split('•')]),
 exp('cetil','Cetil Sistemas de Informação','Cetil',source[282].strip(),'Nov/2011 – Dez/2012','Transparência pública e BI com informações provenientes de mais de 500 prefeituras.',['BI','ETL','Governo'],(284,288),(290,302),(302,302),[t.strip() for t in source[304].split('•')]),
 exp('senai','SENAI/SC','SENAI/SC',source[307].strip(),'Mar/2009 – Nov/2011','Coordenação das equipes de Florianópolis e Tubarão em projetos do Sistema FIESC.',['Liderança','Projetos','ERP'],(309,313),(315,326),(326,326),[t.strip() for t in source[328].split('•')]),
 exp('unimed','Unimed','Unimed',source[331].strip(),'Abr/2008 – Mar/2009','Business Intelligence e indicadores para o Conselho de Administração e a Diretoria Executiva.',['BI','Data Warehouse','SQL'],(333,337),(339,352),(352,352),[t.strip() for t in source[354].split('•')]),
 exp('someday','Someday','Someday',source[357].strip(),'Mai/2006 – Mar/2008','Gestão de tecnologia e sistemas de produção, estoque, logística, vendas e administração.',['Liderança','.NET','ERP'],(359,363),(365,376),(376,376),[t.strip() for t in source[378].split('•')]),
 ],
 'skills':[
  {'title':'Engenharia de Dados','items':lines(424,438)},
  {'title':'Cloud & DevOps','items':lines(439,449)},
  {'title':'Arquitetura de Software','items':lines(394,402)},
  {'title':'Banking & Payments','items':lines(403,423)},
  {'title':'Inteligência Artificial','items':lines(458,466)},
  {'title':'Bancos de Dados','items':lines(450,457)},
  {'title':'Liderança','items':['Gestão de Tecnologia','Coordenação de equipes','Gerenciamento de Projetos','PMBOK','Scrum','Kanban','ITIL']},
 ],
 'education':{'institution':source[381].strip(),'degree':source[382].strip(),'period':source[383].strip()},
 'certifications':lines(386,387),'languages':lines(389,391),
 'clientsRpe':lines(91,102),
 'cases':[],
 'resume':{'originalPrivatePath':'docs/private/curriculo-original.docx','publicDownload':'/documents/carlos-andre-curriculo-publico.docx','publicRedactions':['endereço residencial','metadados pessoais'],'compassEndDatePending':True},
 'contacts':{'email':'pericacs@gmail.com','whatsapp':'5548996277411'},
}
for id,title,company,summary,paragraphs in [
 ('cef','Modernização analítica da CEF','Compass UOL / Caixa Econômica Federal','Mais de 9 bilhões de registros; redução superior a 80% no tempo de processamento.',(19,25)),
 ('rpe-analisa','RPE Analisa','RPE.tech / Fiabilité Tech','Cerca de 12 milhões de registros por dia e dados consolidados em D+1.',(53,59)),
 ('alibin-scd','Arquitetura financeira e estruturação de SCD','Alibin','Evolução de plataformas financeiras, Data Lake, cloud e IA aplicada.',(110,117)),
 ('subadquirencia','Plataforma de Subadquirência','Fastconnect','Processamento financeiro, split, conciliação e gestão de recebíveis.',(179,181)),
 ('winker','Winker','Fastconnect','Contas escrow e volume superior a um milhão de boletos mensais.',(183,186)),
 ('khronos','Khronos','Fastconnect','Ciclo de vendas de 30–45 para cerca de 7 dias; inadimplência de aproximadamente 15% para 4%.',(188,193)),
 ('sistemapet','SistemaPet','Fastconnect','Arquitetura implantada em 2018 como parte da infraestrutura da expansão posterior.',(195,198)),
 ('top-clinicas','Top Clínicas','Fastconnect','Split financeiro, faturamento, cobrança e conciliação para diferentes especialidades médicas.',(200,202)),
 ('jogos-do-rei','Jogos do Rei','Fastconnect','Assinaturas, cobrança recorrente e automação financeira.',(204,206)),
]:
 data['cases'].append(dict(id=id,title=title,company=company,summary=summary,narrative=lines(*paragraphs),sourceParagraphs=list(range(*paragraphs)),evidence='Resultado declarado no currículo fornecido pelo proprietário.',publicationReviewRequired=True))

periods = [('2024-06',None),('2025-01','2025-11'),('2021-01','2024-06'),('2014-01','2020-12'),('2013-01','2013-12'),('2011-11','2012-12'),('2009-03','2011-11'),('2008-04','2009-03'),('2006-05','2008-03')]
for order, (experience, period) in enumerate(zip(data['experiences'], periods)):
 experience.update(startMonth=period[0],endMonth=period[1],datePrecision='month',sortOrder=order,featured=order<4,displayRole=experience['role'])
 if experience['id']=='fastconnect': experience['role']=source[167].strip()
Path('frontend/src/data/curriculum.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f"Extracted {len(data['experiences'])} experiences, {len(data['cases'])} cases and {len(data['skills'])} skill groups; personal address excluded.")
