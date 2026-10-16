# Contato por Gmail

O formulário valida e salva a mensagem no PostgreSQL antes de confirmar o recebimento. A notificação usa Gmail SMTP com STARTTLS, remetente e destinatário `pericacs@gmail.com`, e Reply-To do visitante. O corpo inclui nome, e-mail, empresa, cargo, interesse, mensagem e consentimento.

O arquivo local `.env` e o exemplo usam `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USE_STARTTLS=true`, `SMTP_USERNAME=pericacs@gmail.com`, `SMTP_FROM_EMAIL=pericacs@gmail.com` e `CONTACT_NOTIFICATION_EMAIL=pericacs@gmail.com`.

Falta preencher **SMTP_PASSWORD** no `.env` do servidor com uma senha de app da Conta Google. Não usar a senha comum da conta, não versionar o segredo e não cadastrá-lo no painel. Depois de preencher, recriar os serviços: `docker compose up -d --force-recreate backend worker`.

Falhas preservam a mensagem e deixam a notificação pendente. A auditoria registra apenas a classificação da falha. O worker tenta novamente com espera progressiva, até cinco tentativas totais. O administrador também pode usar **Tentar notificação novamente** em `/admin/mensagens`. Uma notificação já aceita não é reenviada por esse controle. Como SMTP não oferece chave de idempotência, uma interrupção entre o aceite remoto e o registro local pode ocasionar duplicação em nova tentativa.

Validação: suíte backend com PostgreSQL e SMTP simulado; Playwright em 1440px e 390px para validação, preservação dos dados em falha, confirmação após persistência, bloqueio de duplicação e mailto. Nenhum e-mail real foi enviado: SMTP_PASSWORD está vazia.
