import {Header} from '@/components/home-interactions';
import {ProjectFooter} from '@/components/smartfamily/project-footer';
import {publicData} from '@/lib/public-content';
import {ArticleListing} from '@/components/articles/listing';
import s from '@/components/articles/articles.module.css';
export const metadata={title:'Artigos',description:'Dados, inteligência artificial e pagamentos: da arquitetura à aplicação no negócio.'};
export default async function Page(){const {modules,profile,settings,contacts}=await publicData();return <><Header profile={profile} settings={settings} contacts={contacts}/><main className={s.page}><header className={s.opening}><p className={s.kicker}>CONHECIMENTO EM PRÁTICA</p><h1>Artigos</h1><p>Dados, inteligência artificial e pagamentos: da arquitetura à aplicação no negócio.</p></header><ArticleListing items={(modules.artigos||[]).filter(x=>!x.planned)}/></main><ProjectFooter profile={profile} settings={settings}/></>;}
