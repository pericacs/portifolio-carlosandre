import Image from 'next/image';
import {Icon, type IconName} from '@/components/icon';
import s from './intro.module.css';

type Content=Record<string,any>;
const panelOrder=['Produtos Digitais','Dados & IA','Consultoria Estratégica','Parcerias & Investimentos'];

export function HomeHero({profile,settings,services}:{profile:Content;settings:Content;services:Content[]}){
 const photo=settings.photo||profile.photo||'/images/carlos-andre-executivo.png';
 const rank=(title:string)=>{const index=panelOrder.indexOf(title);return index<0?panelOrder.length:index;};
 const panels=[...services].sort((a,b)=>rank(a.shortTitle)-rank(b.shortTitle));
 return <section className={s.hero} id="inicio" aria-labelledby="hero-title">
  <div className={`container ${s.shell}`}>
   <div className={s.main}>
    <div className={s.copy}>
     <p className={`eyebrow ${s.eyebrow}`}>{profile.subtitle}</p>
     <h1 id="hero-title">{(profile.heroPrefix||'').trim()} <span>{profile.heroHighlight}</span></h1>
     <p className={s.description}>{(profile.heroDescription||'').split('\n').map((line:string,i:number)=><span key={i}>{i>0&&<br className="desktop-break"/>}{line}</span>)}</p>
     <div className={s.actions}>
      <a className="button primary" href="#projetos">Conheça meus projetos <Icon name="arrow"/></a>
      <a className="button secondary" href="#contato">Fale comigo</a>
      <a className={s.videoLink} href="#videos"><Icon name="play-circle"/>Explore os vídeos</a>
     </div>
     <div className={s.metrics} aria-label="Indicadores do portfólio">
      {(profile.metrics||[]).map((item:Content,i:number)=><div key={i}><strong>{item.value}</strong><span>{item.label.split('\n').map((line:string,j:number)=><span key={j}>{j>0&&<br/>}{line}</span>)}</span></div>)}
     </div>
    </div>
    <div className={s.visual}>
     <div className={s.portrait}><Image src={photo} unoptimized={photo.startsWith('/api/media/')} alt="Carlos André sorrindo em um escritório moderno" width={1122} height={1402} priority sizes="(max-width: 650px) 90vw, (max-width: 1100px) 360px, 440px"/></div>
     <p className={`handwritten ${s.signature}`}>{(profile.signature||[]).map((line:string,i:number)=><span key={i}>{i>0&&<br/>}{line}</span>)}<span className={s.signatureName}>{profile.title}</span></p>
    </div>
   </div>
   <div className={s.panels} aria-label="Áreas de atuação e propósito">
    {panels.map(service=><a href="#consultoria" className={s.panel} key={service.shortTitle}><Icon name={service.icon as IconName}/><span><strong>{service.shortTitle}</strong><span className={s.tagline}>{service.tagline}</span></span></a>)}
    <blockquote className={`${s.panel} ${s.quote}`}><p>“{profile.quote}”</p><cite>{profile.title}</cite></blockquote>
   </div>
  </div>
 </section>;
}
