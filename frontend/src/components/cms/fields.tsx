'use client';
import {FinalDemos} from './final-demos';
import {useState} from 'react';
import {api,Field} from './api';
import {SmartFields} from './smart-fields';
import {RichEditor} from './editor';
import s from '@/app/admin/admin.module.css';
type Option={id:string;module:string;title:string};
export function CmsField({field:f,value,onChange,options}:{field:Field;value:any;onChange:(v:any)=>void;options:Option[]}){
 const[busy,setBusy]=useState(false),[error,setError]=useState('');
 const id='field-'+f.key;const label=<span>{f.label}{f.required?' *':''}</span>;
 if(f.kind==='finaldemos')return <FinalDemos value={value} onChange={onChange}/>;
 if(['smartblocks','smartmedia'].includes(f.kind))return <SmartFields field={f} value={value} onChange={onChange}/>;
 if(['richtext','finalrich'].includes(f.kind))return <div className={s.cmsField}>{label}<RichEditor label={f.label} value={value||''} onChange={onChange}/></div>;
 if(f.kind==='boolean')return <label className={s.checkField}><input id={id} type="checkbox" checked={!!value} onChange={e=>onChange(e.target.checked)}/>{label}</label>;
 if(['media','document','gallery'].includes(f.kind)){
  const values=f.kind==='gallery'?(value||[]):value?[value]:[];
  return <div className={s.cmsField}>{label}<input id={id} type="file" aria-label={f.label} multiple={f.kind==='gallery'} accept={f.kind==='document'?'.pdf,.docx':'image/png,image/jpeg,image/webp'} disabled={busy} onChange={async e=>{setBusy(true);setError('');try{const urls=[];for(const file of Array.from(e.target.files||[])){const body=new FormData();body.append('file',file);urls.push((await api('/cms/media','POST',body)).url);}onChange(f.kind==='gallery'?[...values,...urls]:urls[0]||'');}catch(e){setError((e as Error).message);}finally{setBusy(false);e.target.value='';}}}/><small>{busy?'Enviando…':'Até 8 MB por arquivo. Salve o conteúdo para manter o vínculo.'}</small>{error&&<p role="alert" className={s.error}>{error}</p>}<div className={s.mediaGrid}>{values.map((url:string,i:number)=><div className={s.mediaTile} key={url+'-'+i}>{f.kind==='document'?<a href={url} target="_blank" rel="noopener noreferrer">Baixar arquivo ↗</a>:<img src={url} alt={f.label}/>}<div><button type="button" className={s.secondary} onClick={()=>onChange(f.kind==='gallery'?values.filter((_:string,j:number)=>j!==i):'')}>Remover</button>{f.kind==='gallery'&&i>0&&<button type="button" className={s.secondary} aria-label="Mover imagem para cima" onClick={()=>{const x=[...values];[x[i],x[i-1]]=[x[i-1],x[i]];onChange(x);}}>↑</button>}</div></div>)}</div></div>;
 }
 if(['links','metrics','services'].includes(f.kind)){
  const keys=f.kind==='links'?['label','url']:f.kind==='metrics'?['value','label']:['title','shortTitle','tagline','description','icon','color'];
  const labels:Record<string,string>={label:'Descrição',url:'URL',value:'Valor',title:'Título',shortTitle:'Título curto',tagline:'Chamada',description:'Descrição',icon:'Ícone',color:'Cor'};
  return <fieldset className={s.repeatField}><legend>{f.label}</legend>{(value||[]).map((item:Record<string,string>,i:number)=><div className={s.repeatRow} key={i}>{keys.map(key=><label className={s.cmsField} key={key}>{labels[key]}<input aria-label={`${f.label} ${i+1} ${labels[key]}`} value={item[key]||''} onChange={e=>onChange(value.map((x:any,j:number)=>j===i?{...x,[key]:e.target.value}:x))}/></label>)}<button type="button" className={s.secondary} onClick={()=>onChange(value.filter((_:any,j:number)=>j!==i))}>Remover</button></div>)}<button className={s.secondary} type="button" onClick={()=>onChange([...(value||[]),Object.fromEntries(keys.map(k=>[k,'']))])}>Adicionar item</button></fieldset>;
 }
 if(f.kind==='order')return <fieldset className={s.repeatField}><legend>{f.label}</legend>{(value||[]).map((item:string,i:number)=><div className={s.orderRow} key={item}><span>{item}</span><button className={s.secondary} type="button" disabled={!i} onClick={()=>{const x=[...value];[x[i],x[i-1]]=[x[i-1],x[i]];onChange(x);}}>↑ Subir</button><button className={s.secondary} type="button" disabled={i===value.length-1} onClick={()=>{const x=[...value];[x[i],x[i+1]]=[x[i+1],x[i]];onChange(x);}}>↓ Descer</button></div>)}</fieldset>;
 if(f.kind==='reference'||f.kind==='references')return <label className={s.cmsField} htmlFor={id}>{label}<select id={id} multiple={f.kind==='references'} value={value||(f.kind==='references'?[]:'')} onChange={e=>onChange(f.kind==='references'?Array.from(e.target.selectedOptions).map(o=>o.value):e.target.value)}>{f.kind==='reference'&&<option value="">Selecione</option>}{options.filter(o=>o.module===f.module).map(o=><option key={o.id} value={o.id}>{o.title}</option>)}</select>{f.kind==='references'&&<small>Use Ctrl/Cmd para selecionar vários registros.</small>}</label>;
 if(f.kind==='select')return <label className={s.cmsField} htmlFor={id}>{label}<select id={id} value={value||''} onChange={e=>onChange(e.target.value)}><option value="">Selecione</option>{f.options?.map(x=><option key={x}>{x}</option>)}</select></label>;
 if(f.kind==='textarea'||f.kind==='lines')return <label className={s.cmsField} htmlFor={id}>{label}<textarea id={id} rows={f.kind==='lines'?6:4} required={f.required} value={f.kind==='lines'?(value||[]).join('\n'):value||''} onChange={e=>onChange(f.kind==='lines'?e.target.value.split('\n'):e.target.value)}/>{f.kind==='lines'&&<small>Um item por linha.</small>}</label>;
 return <label className={s.cmsField} htmlFor={id}>{label}<input id={id} type={['email','url','month','date','number'].includes(f.kind)?f.kind:'text'} list={f.key==='category'?'content-categories':undefined} required={f.required} value={value??''} onChange={e=>onChange(f.kind==='number'?Number(e.target.value):e.target.value)}/>{f.key==='category'&&<datalist id="content-categories">{options.filter(x=>x.module==='content-categories').map(x=><option value={x.title} key={x.id}/>)}</datalist>}</label>;
}
