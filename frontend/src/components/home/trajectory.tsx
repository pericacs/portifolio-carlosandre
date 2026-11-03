import Link from 'next/link';
import s from './intro.module.css';

type Experience=Record<string,any>;
const primaryOrder=['compass-cef','rpe-tech','alibin'];
const otherOrder=['fastconnect','manager-systems','cetil','senai','unimed','someday'];
const matches=(item:Experience,key:string)=>item.id===key||item.slug===key||item.sourceKey==='initial:experiencias:'+key;

export function HomeTrajectory({experiences}:{experiences:Experience[]}){
 const primary=primaryOrder.map(key=>experiences.find(item=>matches(item,key))).filter((item):item is Experience=>!!item);
 const rank=(item:Experience)=>{const index=otherOrder.findIndex(key=>matches(item,key));return index<0?otherOrder.length:index;};
 const others=experiences.filter(item=>!primary.includes(item)).sort((a,b)=>rank(a)-rank(b));
 const href=(item:Experience)=>'/experiencia#'+encodeURIComponent(item.id);
 return <div className={s.experienceGrid}>
  {primary.map(item=><article className={`card ${s.experienceCard} ${matches(item,'compass-cef')?s.featured:''}`} key={item.id} data-experience={primaryOrder.find(key=>matches(item,key))}>
   <div className={s.wordmark}>{item.logo?<img src={item.logo} alt={item.company}/>:item.wordmark==='CAIXA'?<>CAI<span>X</span>A</>:item.wordmark||item.company}</div>
   <p className={s.period}>{item.period}</p>
   <h3>{item.company}</h3>
   <p className={s.role}>{item.displayRole||item.role}</p>
   <p className={s.summary}>{item.description}</p>
   <div className="tags">{(item.tags||[]).map((tag:string)=><span key={tag}>{tag}</span>)}</div>
   {((item.results||[]).length>0||(item.technologies||[]).length>0)&&<details className={s.experienceDetails}><summary>Resultados e tecnologias</summary>{(item.results||[]).length>0&&<ul>{item.results.map((result:string)=><li key={result}>{result}</li>)}</ul>}{(item.technologies||[]).length>0&&<div className="tags">{item.technologies.map((technology:string)=><span key={technology}>{technology}</span>)}</div>}</details>}
   <Link className={s.experienceLink} href={href(item)}>Ver experiência completa →</Link>
  </article>)}
  <article className={`card ${s.experienceCard} ${s.otherExperiences}`} data-experience="others"><h3>Outras experiências</h3><ul>{others.map((item,index)=><li key={item.id} className={index===0&&matches(item,'fastconnect')?s.fastconnect:undefined}><Link href={href(item)}>{index===0&&matches(item,'fastconnect')?<><strong>{item.company}</strong>{' '}<span>{item.displayRole||item.role}</span></>:item.company}</Link></li>)}</ul><Link className={s.experienceLink} href="/experiencia">Ver toda a trajetória →</Link></article>
 </div>;
}
