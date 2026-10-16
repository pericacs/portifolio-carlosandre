import {ProjectFooter} from '@/components/smartfamily/project-footer';
import {SmartFamilyPresentation} from '@/components/smartfamily/presentation';
import {Header} from '@/components/home-interactions';
import {notFound} from 'next/navigation';
import {PublicDetail} from '@/components/cms/public-detail';
import {publicData} from '@/lib/public-content';
export async function generateMetadata({params}:{params:Promise<{slug:string}>}){const {slug}=await params;const {modules}=await publicData();const item=modules.projetos?.find(x=>x.slug===slug);return {title:item?.seoTitle||item?.title,description:item?.metaDescription||item?.description};}
export default async function Page({params,searchParams}:{params:Promise<{slug:string}>;searchParams:Promise<{lang?:string}>}){const {slug}=await params;const {lang}=await searchParams;if(slug==='smartfamily'){const {modules,profile,settings,contacts}=await publicData();const item=modules.projetos.find(x=>x.slug===slug);if(!item)notFound();return <><Header profile={profile} settings={settings} contacts={contacts}/><SmartFamilyPresentation item={item}/><ProjectFooter profile={profile} settings={settings}/></>;}return <PublicDetail module="projetos" slug={slug} english={lang==='en'}/>;}