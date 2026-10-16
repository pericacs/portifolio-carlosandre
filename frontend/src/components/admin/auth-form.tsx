'use client';
import { useEffect, useState, FormEvent } from 'react';
import s from '@/app/admin/admin.module.css';
export function AuthForm({mode='login'}:{mode?:'login'|'recovery'|'reset'}) {
  const [csrf,setCsrf]=useState(''), [busy,setBusy]=useState(false), [error,setError]=useState(''), [message,setMessage]=useState('');
  const [show,setShow]=useState(false), [recovery,setRecovery]=useState(false), [resetToken,setResetToken]=useState('');
  useEffect(()=>{
    if(mode==='reset'){
      setResetToken(new URLSearchParams(window.location.hash.slice(1)).get('token')||'');
      window.history.replaceState(null,'',window.location.pathname);
    }
    fetch('/api/admin/auth/csrf',{cache:'no-store'}).then(async r=>{if(!r.ok)throw Error();return r.json();})
      .then(d=>{setCsrf(d.csrfToken);setRecovery(d.passwordRecoveryAvailable);})
      .catch(()=>setError('Não foi possível conectar ao painel. Recarregue a página.'));
  },[mode]);
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();setBusy(true);setError('');setMessage('');
    const data=new FormData(event.currentTarget);
    if(mode==='reset'&&data.get('password')!==data.get('confirmation')){setError('As senhas precisam ser iguais.');setBusy(false);return;}
    const body=mode==='login'?{email:data.get('email'),password:data.get('password')}:
      mode==='recovery'?{email:data.get('email')}:{token:resetToken,password:data.get('password')};
    try{
      const response=await fetch(`/api/admin/auth/${mode}`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(body)});
      const result=await response.json();
      if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'Verifique os campos e tente novamente.');
      if(mode==='login'){window.location.assign('/admin');return;}
      setMessage(result.message);
    }catch(e){setError(e instanceof Error?e.message:'Falha de conexão. Tente novamente.');}finally{setBusy(false);}
  }
  const disabled=busy||!csrf||(mode==='recovery'&&!recovery)||(mode==='reset'&&!resetToken);
  return <><form className={s.form} onSubmit={submit}>
    {mode!=='reset'&&<label className={s.field}>E-mail<input name="email" type="email" autoComplete="username" required maxLength={320} placeholder="seu@email.com" /></label>}
    {mode!=='recovery'&&<label className={s.field}>{mode==='reset'?'Nova senha':'Senha'}<span className={s.passwordField}><input name="password" type={show?'text':'password'} required minLength={mode==='reset'?14:1} maxLength={256} autoComplete={mode==='reset'?'new-password':'current-password'} placeholder={mode==='reset'?'Pelo menos 14 caracteres':'Digite sua senha'} /><button type="button" aria-pressed={show} onClick={()=>setShow(!show)}>{show?'Ocultar':'Mostrar'}</button></span></label>}
    {mode==='reset'&&<label className={s.field}>Confirmar nova senha<input name="confirmation" type="password" required minLength={14} maxLength={256} autoComplete="new-password" /></label>}
    {error&&<div role="alert" className={s.error}>{error}</div>}{message&&<div role="status" className={s.success}>{message}</div>}
    {!message&&<button className={s.primary} disabled={disabled}>{busy?'Aguarde…':mode==='login'?'Entrar no painel':mode==='recovery'?'Enviar instruções':'Atualizar senha'} {mode==='login'&&<span aria-hidden="true">→</span>}</button>}
  </form><div className={s.authLinks}>{mode==='login'?<>{recovery&&<a href="/admin/recuperar-senha">Esqueci minha senha</a>}<a href="/">← Voltar ao site</a></>:<a href="/admin/login">← Voltar ao login</a>}</div>
  {mode==='login'&&<p className={s.helper}>Acesso exclusivo à administração do portfólio. As contas são criadas pelo responsável pelo ambiente.</p>}
  {mode==='recovery'&&csrf&&!recovery&&<p className={s.helper}>O envio de e-mail ainda não está configurado. Contate o administrador do ambiente para recuperar seu acesso.</p>}
  {mode==='reset'&&!resetToken&&<p className={s.helper}>Abra o link completo recebido por e-mail. Se ele expirou, solicite um novo.</p>}</>;
}
export function AuthScreen({mode='login'}:{mode?:'login'|'recovery'|'reset'}){
  return <main className={s.auth}><aside className={s.authIntro}><div className={s.brand}><span className={s.brandMark}>CA</span><span>CARLOS ANDRÉ<small>Technology & Ventures</small></span></div><div><h2>O próximo capítulo<br/>começa por aqui.</h2><p>Um espaço para organizar sua trajetória, compartilhar conhecimento e dar vida a novas ideias.</p></div><div className={s.authIntroFooter}>Portfólio · Administração de conteúdo</div></aside><section className={s.authMain}><div className={s.authCard}><div className={s.eyebrow}>Área administrativa</div><h1>{mode==='login'?'Bem-vindo de volta.':mode==='recovery'?'Recuperar acesso.':'Definir nova senha.'}</h1><p>{mode==='login'?'Entre para acessar a administração do seu portfólio.':mode==='recovery'?'Receba as instruções no e-mail da sua conta.':'Escolha uma senha exclusiva com pelo menos 14 caracteres.'}</p><AuthForm mode={mode}/></div></section></main>;
}
