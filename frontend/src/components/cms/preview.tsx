import {Schema} from './api';
import s from '@/app/admin/admin.module.css';
export function Preview({data,schema}:{data:Record<string,any>;schema:Schema}){
 return <><div className={s.notice}><strong>Pré-visualização autenticada.</strong> Exibição dos campos PÚBLICOS do rascunho. Campos privados são omitidos.</div><h1>{data.title}</h1><section className={s.panel}><div className={s.cmsForm}>{schema.fields.filter(f=>!['slug','visible','featured','sortOrder','privateNotes','publicationReviewed'].includes(f.key)&&!data.privateFields?.includes(f.key)).map(f=>{const v=data[f.key];if(!v||Array.isArray(v)&&!v.length)return null;
 if(f.kind==='richtext')return <section key={f.key}><h2>{f.label}</h2><div className={s.richPreview} dangerouslySetInnerHTML={{__html:v}}/></section>;
 if(['media','gallery'].includes(f.kind))return <section key={f.key}><h2>{f.label}</h2><div className={s.previewImages}>{(Array.isArray(v)?v:[v]).map((url:string)=><img key={url} src={url} alt={f.label}/>)}</div></section>;
 if(f.kind==='document')return <a key={f.key} href={v} className={s.secondary}>Baixar currículo</a>;
 if(f.kind==='boolean')return <p key={f.key}>{f.label}: Sim</p>;
 if(f.kind==='links')return <section key={f.key}><h2>{f.label}</h2>{v.map((x:any,i:number)=><p key={i}><a href={x.url} rel="noopener noreferrer" target="_blank">{x.label||x.url}</a></p>)}</section>;
 if(['metrics','services'].includes(f.kind))return <section key={f.key}><h2>{f.label}</h2>{v.map((x:any,i:number)=><p key={i}>{x.value||x.title} — {x.label||x.description}</p>)}</section>;
 if(['references','reference'].includes(f.kind))return null;
 return <section key={f.key}><h2>{f.label}</h2>{Array.isArray(v)?v.map((x:string,i:number)=><p key={i}>{x}</p>):<p style={{whiteSpace:'pre-line'}}>{String(v)}</p>}</section>;
 })}</div></section>{data.youtubeId&&<iframe className={s.youtubeFrame} src={'https://www.youtube-nocookie.com/embed/'+data.youtubeId} title={data.title} allowFullScreen/>}</>;
}
