"""Editorial presentation based on owner-provided facts; implementation is not inferred."""
def block(title,description,status='Não verificado',order=0):
    return dict(title=title,description='<p>'+description+'</p>',status=status,evidence='',visibility='PÚBLICO',order=order)

def content():
    data={
      'sfTagline':'Sua família organizada. Seu tempo de volta.',
      'sfOverview':'<p>O SmartFamily é uma proposta de organização familiar que reúne agenda, tarefas, lembretes e um assistente inteligente. A intenção é reduzir a fragmentação da rotina e tornar as informações da família mais fáceis de encontrar.</p><p>O projeto conecta a experiência web a comandos pelo WhatsApp. Esta apresentação descreve as tecnologias informadas pelo proprietário; a disponibilidade de cada capacidade está indicada separadamente.</p>',
      'sfProblem':'<p>Compromissos em calendários diferentes, tarefas distribuídas em conversas e lembretes dispersos tornam a coordenação familiar mais difícil. O desafio de negócio é organizar esse contexto sem acrescentar burocracia à rotina.</p>',
      'sfSolution':'<p>Centralizar agenda, tarefas e lembretes em uma experiência compartilhada, com uma interface web e comandos em linguagem natural. A integração com canais já presentes no cotidiano é parte da proposta do produto.</p>',
      'sfHow':'<p>A proposta é transformar uma intenção escrita ou falada em uma ação organizada. O fluxo abaixo é conceitual, não uma demonstração de execução.</p><p><strong>Os comandos são exemplos ilustrativos.</strong> Não foram fornecidos registros de testes para classificá-los como comandos reais já suportados.</p>',
      'sfArchitecture':'<p>Visão conceitual construída a partir da stack informada: React na experiência web, Python/FastAPI na camada de aplicação, PostgreSQL para persistência e Docker/Nginx na infraestrutura.</p><p>As conexões do diagrama representam responsabilidades propostas. Não são uma topologia de produção verificada.</p>',
      'sfChallenges':'<p>Os pontos abaixo são questões de engenharia relevantes para o escopo descrito. São critérios de análise e validação; não afirmam que uma solução específica já foi implementada.</p>',
      'sfStage':'<p><strong>Estágio de implementação a validar.</strong> Não foram fornecidas evidências suficientes para separar entregas concluídas de trabalho em andamento. As capacidades permanecem como não verificadas até revisão pelo proprietário.</p><p>O roteiro abaixo organiza essa validação e não representa um cronograma de entregas aprovado. Não há métricas de uso ou resultados comprovados cadastrados.</p>',
      'sfCtaTitle':'Tecnologia para uma rotina mais conectada.',
      'sfCtaText':'<p>Conheça a proposta do SmartFamily ou converse sobre arquitetura, evolução do produto e oportunidades de parceria.</p>',
      'tags':['Organização familiar','Produtividade','Inteligência artificial','SaaS','WhatsApp','Agenda compartilhada'],
      'sfMetrics':[],
    }
    groups={
      'sfFeatures':[
        ('Agenda familiar','Compromissos e visão da rotina são parte do escopo informado. Regras de compartilhamento e recorrência aguardam validação funcional.'),
        ('Tarefas e lembretes','Organização de responsabilidades e lembretes informada pelo proprietário. Canais de entrega, estados e garantias de notificação ainda não foram verificados.'),
        ('Assistente de IA','Interpretação de comandos naturais associada a Groq e transcrição por Whisper. Precisão, contexto e confirmações exigem testes.'),
        ('Gerenciamento da família','Área de domínio prevista no escopo. Convites, papéis e isolamento entre famílias precisam de confirmação antes de serem descritos como entregues.'),
        ('Comandos pelo WhatsApp','Canal informado via WhatsApp Cloud API. O conjunto de comandos efetivamente suportados ainda não foi comprovado.'),
        ('Calendários conectados','Google Calendar OAuth e Apple Calendar via CalDAV fazem parte das integrações informadas; sincronização e tratamento de conflitos aguardam verificação.')],
      'sfCommands':[
        ('Lembre-me da reunião amanhã às 9h.','Exemplo ilustrativo de intenção de lembrete. A interpretação de “amanhã” depende do fuso e de confirmação do horário.'),
        ('Adicionar a tarefa de organizar a semana.','Exemplo ilustrativo de criação de tarefa. Responsável, prazo e contexto familiar precisam ser definidos.'),
        ('Marcar uma atividade toda segunda às 18h.','Exemplo ilustrativo de recorrência. O comportamento em exceções, alterações e cancelamentos precisa de validação.')],
      'sfTech':[
        ('React','Frontend informado para a experiência web. Papel arquitetural: apresentar agenda, tarefas e interações com a aplicação.'),
        ('Python / FastAPI','Backend informado. Papel arquitetural: expor a API e coordenar regras de negócio, validação e integrações.'),
        ('PostgreSQL','Banco de dados informado. Papel arquitetural: persistir entidades e relações do domínio familiar. Modelo e isolamento não foram inspecionados.'),
        ('Docker / Nginx','Stack de infraestrutura informada. Contêineres organizam serviços; Nginx pode atuar como proxy. Configuração de produção não verificada.'),
        ('Groq','Serviço de IA informado para interpretação de linguagem natural. Modelo utilizado, limites e política de contexto ainda precisam ser documentados.'),
        ('Whisper','Tecnologia de transcrição informada para áudio. O caminho completo de voz até uma ação validada ainda precisa de demonstração.')],
      'sfIntegrations':[
        ('WhatsApp Cloud API','Canal de comunicação informado para receber comandos e interagir com o assistente. Fluxos de webhook e entrega não foram auditados.'),
        ('Google Calendar OAuth','Integração informada para autorização de acesso ao calendário Google. Escopos, renovação e revogação exigem revisão.'),
        ('Apple Calendar / CalDAV','Integração informada baseada no protocolo CalDAV. Compatibilidade, sincronização e resolução de conflitos precisam de teste.')],
      'sfDecisions':[
        ('Recorrência não é apenas repetir uma data','É necessário definir séries, exceções, fuso horário e o efeito de editar uma ocorrência versus toda a série. A estratégia adotada ainda não foi confirmada.'),
        ('Uma intenção precisa de contexto','Datas relativas, responsáveis e comandos ambíguos exigem critérios de confirmação. A interpretação por IA não deve ser tratada como garantia de uma ação correta.'),
        ('Sincronização exige regras claras','Antes de afirmar sincronização bidirecional, é preciso validar fonte de verdade, duplicidade, idempotência e conflitos entre calendários.'),
        ('O contexto de cada família deve permanecer separado','Papéis, autorização por recurso, minimização de dados e tratamento do conteúdo enviado à IA precisam de revisão específica. Nenhum dado familiar real é exibido aqui.')],
      'sfRoadmap':[
        ('Validar a base funcional','Registrar evidências de agenda, tarefas, lembretes, gerenciamento da família e comandos efetivamente suportados.'),
        ('Verificar integrações e recorrências','Testar WhatsApp, calendários externos, voz, exceções de recorrência e comportamento em falhas.'),
        ('Documentar a evolução','Adicionar capturas reais, demonstração, decisões confirmadas e resultados mensuráveis, sem datas ou números estimados.')]
    }
    for key,rows in groups.items():data[key]=[block(title,text,order=i) for i,(title,text) in enumerate(rows)]
    data['sfMedia']=[]
    for i,(slot,title,description) in enumerate([
        ('cover','SmartFamily: visão integrada','Composição desktop ilustrativa para apresentar a proposta.'),
        ('desktop','Dashboard desktop','Representação conceitual de uma visão compartilhada. Não é uma captura da aplicação.'),
        ('calendar','Agenda familiar','Ilustração de calendário. Compromissos e funcionamento são exemplos fictícios.'),
        ('tasks','Interface de tarefas','Representação ilustrativa de organização de responsabilidades.'),
        ('whatsapp','Conversa com o assistente','Conversa fictícia para explicar a proposta, sem execução real.'),
        ('mobile','Interface mobile','Representação conceitual para celular. Não comprova disponibilidade de funcionalidades.'),
        ('architecture','Diagrama conceitual da arquitetura','Responsabilidades e integrações informadas; não representa topologia verificada.'),
        ('video','Vídeo demonstrativo','A demonstração real ainda não foi fornecida. Este espaço não simula a reprodução de um vídeo.')]):
        data['sfMedia'].append(dict(slot=slot,title=title,description='<p>'+description+'</p>',alt=title+' — ilustração conceitual, não é tela funcional',url='',illustrative=True,order=i,visibility='PÚBLICO'))
    return data

def install(db):
    import sqlalchemy as sa
    from app import models as m
    from app.cms import revision,refs,publish_entry
    from app.cms_schema import validate
    row=db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.module=='projetos',m.cms_entries.c.slug=='smartfamily',m.cms_entries.c.deleted_at.is_(None)).with_for_update()).mappings().one()
    if db.scalar(sa.select(m.cms_revisions.c.id).where(m.cms_revisions.c.entry_id==row['id'],m.cms_revisions.c.action=='smartfamily_presentation').limit(1)):
        print('Apresentação já cadastrada; edições preservadas.');return
    new=content()
    draft=validate('projetos',{**row['data'],**new})
    if '_legacy' in row['data']:draft['_legacy']=row['data']['_legacy']
    updated=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==row['id']).values(data=draft,version=row['version']+1).returning(m.cms_entries)).mappings().one()
    refs(db,row['id'],'projetos',draft,'draft');revision(db,updated,'smartfamily_presentation',row['editor_id'])
    published={**(row['published_data'] or {}),**new,'publicationReviewed':True}
    publish_entry(db,updated,row['editor_id'],published);db.commit()
    print('SmartFamily: apresentação local publicada, com ilustrações e status não verificados explícitos.')

if __name__=='__main__':
    from sqlalchemy.orm import Session
    from app.db import get_engine
    with Session(get_engine()) as db:install(db)
