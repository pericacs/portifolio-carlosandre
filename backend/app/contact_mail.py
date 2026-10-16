"""Synchronous SMTP acceptance for the public contact form. No delivery is simulated."""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from fastapi import HTTPException
from app.config import get_settings


def send_contact(body):
 settings=get_settings()
 if not settings.smtp_host or not settings.smtp_from or (settings.smtp_user and not settings.smtp_password):
  raise HTTPException(503,'O envio de e-mail está indisponível no momento. Seus dados foram preservados; tente novamente mais tarde ou use o atalho E-mail.')
 mail=EmailMessage()
 accepted=False
 try:
  mail['From']=settings.smtp_from
  mail['To']=settings.contact_notification_email
  mail['Reply-To']=str(body.email)
  mail['Subject']='Contato pelo portfólio: '+body.subject
  mail.set_content('\n'.join(['Nova mensagem pelo portfólio','',f'Nome: {body.name}',f'E-mail: {body.email}',f'Empresa: {body.company or "Não informada"}',f'Cargo: {body.role or "Não informado"}',f'Interesse: {body.subject}','','Mensagem:',body.message,'','Consentimento para contato: confirmado.']))
  with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=15) as smtp:
   if settings.smtp_starttls:smtp.starttls(context=ssl.create_default_context())
   if settings.smtp_user:smtp.login(settings.smtp_user,settings.smtp_password)
   refused=smtp.send_message(mail)
   if refused:raise smtplib.SMTPRecipientsRefused(refused)
   accepted=True
 except (smtplib.SMTPException,OSError,ValueError):
  if accepted:return # SMTP DATA was accepted; a QUIT failure must not encourage duplicates.
  logging.getLogger(__name__).warning('Falha no envio SMTP do contato')
  raise HTTPException(502,'O serviço de e-mail não confirmou o envio. Seus dados foram preservados. Tente novamente.') from None
