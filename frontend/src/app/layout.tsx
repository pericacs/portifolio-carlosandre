import type { Metadata } from 'next';
import './globals.css';
import {publicData} from '@/lib/public-content';

export async function generateMetadata():Promise<Metadata> {
 const {settings}=await publicData();
 return {title:settings.seoTitle||settings.title||'Carlos André | Technology & Ventures',description:settings.metaDescription||'',robots:{index:false,follow:false},...(settings.favicon?{icons:{icon:settings.favicon}}:{})};
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
