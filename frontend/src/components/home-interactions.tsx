'use client';

import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Icon } from './icon';
import { contacts } from '@/data/contact';

const links = [['Início','/#inicio'],['Sobre','/sobre'],['Projetos','/#projetos'],['Experiência','/experiencia'],['Artigos','/#artigos'],['Vídeos','/#videos'],['Consultoria','/#consultoria'],['Contato','/#contato']];
export function Header({profile={},settings={},contacts:providedContacts=contacts}:{profile?:Record<string,any>;settings?:Record<string,any>;contacts?:Record<string,any>}={}) {
  const [open,setOpen] = useState(false);
  return <header className="site-header"><div className="container header-inner"><a href="/" className="brand" aria-label="Carlos André, início">{settings.logo?<img src={settings.logo} alt={profile.title||'Carlos André'} style={{maxWidth:170,height:40,objectFit:'contain'}}/>:<><strong>{(profile.title||'CARLOS ANDRÉ').toUpperCase()}</strong><span>{profile.professionalTitle||'TECHNOLOGY & VENTURES'}</span></>}</a><button className="menu-toggle" aria-expanded={open} aria-controls="main-nav" aria-label={open?'Fechar menu':'Abrir menu'} onClick={()=>setOpen(!open)}><Icon name={open?'close':'menu'} /></button><nav id="main-nav" className={open?'main-nav is-open':'main-nav'} aria-label="Navegação principal">{links.map(([label,href])=><a href={href} key={label} onClick={()=>setOpen(false)}>{label}</a>)}</nav><div className="header-socials"><a href={`mailto:${providedContacts.email}`} aria-label="Enviar e-mail"><Icon name="mail" /></a><a href={providedContacts.youtube||"/#videos"} aria-label="Explorar vídeos"><Icon name="video" /></a></div><a className="button primary header-cta" href="/#contato">Vamos conversar <Icon name="arrow" /></a></div></header>;
}

export function DetailButton({label,title,children,className,customIcon}: {label:string;title:string;children:ReactNode;className?:string;customIcon?:ReactNode}) {
  const ref=useRef<HTMLDialogElement>(null);
  const titleId=useId();
  return <><button type="button" className={className} aria-label={label} onClick={()=>ref.current?.showModal()}>{customIcon ?? (className==='text-link'?<>{label}<Icon name="arrow" /></>:<Icon name="arrow" />)}</button><dialog ref={ref} className="detail-dialog" aria-labelledby={titleId} onClick={event=>{if(event.target===ref.current)ref.current?.close();}}><div className="dialog-inner"><button autoFocus className="dialog-close" aria-label="Fechar detalhes" onClick={()=>ref.current?.close()}><Icon name="close" /></button><p className="eyebrow">CARLOS ANDRÉ · TECHNOLOGY & VENTURES</p><h2 id={titleId}>{title}</h2><div className="dialog-content">{children}</div><a className="button primary" href="/#contato" onClick={()=>ref.current?.close()}>Conversar sobre este tema <Icon name="arrow" /></a></div></dialog></>;
}

export function ContactForm() {
  const [message,setMessage]=useState(''),[result,setResult]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [fields,setFields]=useState<Record<string,string>>({});
  const sending=useRef(false),ticket=useRef({value:'',issued:0});
  async function challenge(){const response=await fetch('/api/contact/challenge',{cache:'no-store',signal:AbortSignal.timeout(10000)});if(!response.ok)throw Error('challenge');const data=await response.json();ticket.current={value:data.ticket,issued:Date.now()};}
  useEffect(()=>{challenge().catch(()=>setError('Não foi possível iniciar o formulário. Tente novamente.'));},[]);
  const feedback=(key:string)=>fields[key]?<small id={'contact-error-'+key} className="contact-field-error">{fields[key]}</small>:null;
  const invalid=(key:string)=>({'aria-invalid':!!fields[key],'aria-describedby':fields[key]?'contact-error-'+key:undefined});
  async function prepare(event:FormEvent<HTMLFormElement>){
    event.preventDefault();if(sending.current)return;
    const element=event.currentTarget,form=new FormData(element),value=(key:string)=>String(form.get(key)||'').trim();
    const errors:Record<string,string>={};
    if(value('name').length<2)errors.name='Informe seu nome completo (mínimo de 2 caracteres).';
    const email=element.elements.namedItem('email') as HTMLInputElement;
    if(!value('email')||!email.validity.valid)errors.email='Informe um e-mail válido.';
    if(!value('interest'))errors.interest='Selecione seu interesse.';
    if(value('message').length<10)errors.message='Escreva uma mensagem com pelo menos 10 caracteres.';
    if(form.get('consent')!=='on')errors.consent='Confirme o consentimento para contato.';
    setFields(errors);setError('');setResult('');
    if(Object.keys(errors).length){(element.elements.namedItem(Object.keys(errors)[0]) as HTMLElement)?.focus();return;}
    sending.current=true;setBusy(true);
    try{
      if(!ticket.current.value||Date.now()-ticket.current.issued>50*60*1000)await challenge();
      const wait=2100-(Date.now()-ticket.current.issued);if(wait>0)await new Promise(resolve=>setTimeout(resolve,wait));
      const response=await fetch('/api/contact',{method:'POST',headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(60000),body:JSON.stringify({name:value('name'),email:value('email'),company:value('company'),role:value('role'),subject:value('interest'),message:value('message'),consent:true,website:value('website'),ticket:ticket.current.value})});
      const data=await response.json().catch(()=>({}));
      if(!response.ok){
        if(response.status===422){const next:Record<string,string>={};const labels:Record<string,string>={name:'Confira seu nome completo.',email:'Informe um e-mail válido.',subject:'Selecione um interesse válido.',message:'A mensagem deve ter entre 10 e 1000 caracteres.',consent:'Confirme o consentimento para contato.',company:'A empresa deve ter até 120 caracteres.',role:'O cargo deve ter até 120 caracteres.'};
          if(Array.isArray(data.detail))for(const item of data.detail){const key=item.loc?.at(-1);if(labels[key])next[key==='subject'?'interest':key]=labels[key];}
          if(data.detail?.fields?.consent)next.consent=labels.consent;
          setFields(next);if(data.detail?.code==='contact_ticket'||!Object.keys(next).length)ticket.current={value:'',issued:0};
          setError(Object.keys(next).length?'Confira os campos indicados e tente novamente.':'A sessão do formulário expirou. Tente novamente.');
        }else setError(response.status===503?'O envio de e-mail está indisponível no momento. Seus dados foram preservados; tente novamente mais tarde ou use o atalho E-mail.':response.status===429?'Muitas tentativas. Aguarde 15 minutos antes de tentar novamente.':'O serviço de e-mail não confirmou o envio. Seus dados foram preservados. Tente novamente.');
        return;
      }
      if(data.stored!==true)throw Error('not-accepted');
      setResult('Mensagem recebida e salva. Obrigado pelo contato.');element.reset();setMessage('');ticket.current={value:'',issued:0};
    }catch{setError('Não foi possível confirmar o envio. Seus dados foram preservados. Verifique sua conexão e tente novamente.');}
    finally{sending.current=false;setBusy(false);}
  }
  return <form id="formulario" className="card contact-form" onSubmit={prepare} noValidate aria-busy={busy}>
    <p className="eyebrow">ENTRE EM CONTATO</p><h3>Conte sobre o seu projeto</h3><p>Preencha os dados abaixo e me conte como posso ajudar.</p>
    <div className="form-fields"><label>Nome completo <span>*</span><input name="name" autoComplete="name" required minLength={2} maxLength={120} placeholder="Seu nome" {...invalid('name')}/>{feedback('name')}</label><label>E-mail <span>*</span><input name="email" type="email" autoComplete="email" required maxLength={254} placeholder="seu@email.com" {...invalid('email')}/>{feedback('email')}</label><label>Empresa<input name="company" autoComplete="organization" maxLength={120} placeholder="Sua empresa (opcional)" {...invalid('company')}/>{feedback('company')}</label><label>Cargo<input name="role" autoComplete="organization-title" maxLength={120} placeholder="Seu cargo (opcional)" {...invalid('role')}/>{feedback('role')}</label><label className="full-field">Qual é o seu interesse? <span>*</span><select name="interest" required defaultValue="" {...invalid('interest')}><option value="" disabled>Selecione uma opção</option><option>Desenvolvimento de produto</option><option>Dados e Inteligência Artificial</option><option>Consultoria e arquitetura</option><option>Parceria ou investimento</option><option>Oportunidade profissional</option><option>Outro assunto</option></select>{feedback('interest')}</label><label className="full-field message-field">Como posso ajudar? <span>*</span><textarea name="message" required minLength={10} maxLength={1000} rows={4} placeholder="Conte um pouco sobre o seu desafio, objetivo ou ideia..." value={message} onChange={event=>setMessage(event.target.value)} {...invalid('message')}/><small className="message-count">{message.length}/1000</small>{feedback('message')}</label></div>
    <label className="consent"><input type="checkbox" required name="consent" {...invalid('consent')}/>Concordo em compartilhar estes dados para fins de contato.</label>{feedback('consent')}
    <input name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" style={{display:'none'}}/><button disabled={busy} className="button primary submit-button" type="submit">{busy?'Enviando…':error?'Tentar novamente':'Enviar mensagem'} <Icon name="arrow"/></button><p className="form-note">Seus dados serão usados para responder ao contato. <a href="/privacidade">Leia a política de privacidade.</a></p>
    {result&&<div className="form-result" role="status"><p>{result}</p></div>}{error&&<div className="form-result" role="alert"><p>{error}</p></div>}
  </form>;
}
