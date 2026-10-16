'use client';
import s from './admin.module.css';
export default function AdminError({reset}:{reset:()=>void}){return <main className={s.unavailable}><div><p className={s.eyebrow}>Administração</p><h1>Conexão indisponível</h1><p>Não foi possível carregar o painel. Verifique o ambiente e tente novamente.</p><button className={s.primary} onClick={reset}>Tentar novamente</button></div></main>;}
