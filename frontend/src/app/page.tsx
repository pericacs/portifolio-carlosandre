import {HomeArticleCard} from '@/components/articles/home-card';
import Link from 'next/link';
import Image from 'next/image';
import { Icon } from '@/components/icon';
import { Artwork } from '@/components/artwork';
import { Header, DetailButton, ContactForm } from '@/components/home-interactions';
import { publicData } from '@/lib/public-content';
import { OrderedSections } from '@/components/cms/ordered-sections';

// Always read the latest published CMS snapshot; no static Home snapshot.
export const dynamic='force-dynamic';

function SectionHeading({ id, title, description, children }: { id: string; title: string; description: string; children?: React.ReactNode }) {
  return <div className="section-heading"><div><h2 id={id}>{title}</h2><p>{description}</p></div>{children}</div>;
}
const projectStatuses:Record<string,{label:string;tone:string}>={smartfamily:{label:'Em produção',tone:'production'},beloria:{label:'Em desenvolvimento',tone:'development'},'onstar-scd':{label:'Em Projeto',tone:'planning'},'orquestrador-ia':{label:'Em Projeto',tone:'planning'}};
function projectStatus(project:Record<string,any>){
  if(project.slug==='onstar-scd'||project.slug==='avallow'){
    const label=project.developmentStage||projectStatuses.beloria.label;
    return label===projectStatuses.beloria.label?projectStatuses.beloria:{label,tone:label==='Em produção'?'production':'planning'};
  }
  return projectStatuses[project.slug];
}
function Tags({ items }: { items: readonly string[] }) { return <div className="tags">{items.map(item => <span key={item}>{item}</span>)}</div>; }

export default async function Home() {
  const {projects,services,experiences,skills,articles,videos,profile,settings,contacts,curriculum}=await publicData();
  return <>
    <a className="skip-link" href="#conteudo">Pular para o conteúdo</a>
    <Header profile={profile} settings={settings} contacts={contacts} />
    <main id="conteudo">
      <section className="hero" id="inicio" aria-labelledby="hero-title">
        <div className="container hero-inner">
          <div className="hero-copy">
            <p className="eyebrow">{profile.subtitle}</p>
            <h1 id="hero-title">{(profile.heroPrefix||'').trim()} <span>{profile.heroHighlight}</span></h1>
            <p className="hero-description">{(profile.heroDescription||'').split('\n').map((line:string,i:number)=><span key={i}>{i>0&&<br className="desktop-break"/>}{line}</span>)}</p>
            <div className="hero-actions"><a className="button primary" href="#projetos">Conheça meus projetos <Icon name="arrow" /></a><a className="button secondary" href="#contato">Fale comigo</a><a className="video-link" href="#videos"><Icon name="play-circle" /> Explore os vídeos</a></div>
            <div className="stats" aria-label="Indicadores do portfólio">
              {(profile.metrics||[]).map((item:any,i:number)=><div key={i}><strong>{item.value}</strong><span>{item.label.split('\n').map((line:string,j:number)=><span key={j} style={{display:'contents'}}>{j>0&&<br/>}{line}</span>)}</span></div>)}
            </div>
          </div>
          <div className="hero-visual">
            <div className="portrait"><Image src={settings.photo||profile.photo||"/images/carlos-andre-executivo.png"} unoptimized={!!(settings.photo||profile.photo||'').startsWith('/api/media/')} alt="Carlos André sorrindo em um escritório moderno" width={1122} height={1402} priority sizes="(max-width: 600px) 85vw, (max-width: 1000px) 45vw, 370px" /></div>
            <p className="handwritten hero-signature">{(profile.signature||[]).map((line:string,i:number)=><span key={i} style={{display:'contents',fontSize:'inherit'}}>{i>0&&<br/>}{line}</span>)}<span>{profile.title}</span></p>
            <div className="hero-pillars">{services.map((service:any) => <a href="#consultoria" className="hero-pillar" key={service.shortTitle}><Icon name={service.icon} /><span><strong>{service.shortTitle}</strong><small>{service.tagline}</small></span></a>)}<blockquote>“{profile.quote}”<cite>{profile.title}</cite></blockquote></div>
          </div>
        </div>
      </section>
      <div className="container main-sections"><OrderedSections order={settings.sectionOrder||[]}>
        <section id="projetos" aria-labelledby="projects-title" className="home-section">
          <SectionHeading id="projects-title" title="Projetos em destaque" description="Soluções reais para problemas do dia a dia. Tecnologia que simplifica, conecta e gera oportunidades."><a className="text-link" href="#portfolio-detalhes">Explore as iniciativas <Icon name="arrow" /></a></SectionHeading>
          <div className="projects-grid" id="portfolio-detalhes">{projects.map(project => <article className="card project-card" key={project.name}>{project.slug==='smartfamily'?<Link className="project-status-image" href="/projetos/smartfamily" aria-label="Ver imagens e detalhes do SmartFamily"><Artwork crop={project.crop} label={project.imageAlt} source={project.cover} /></Link>:<div data-avallow={project.slug==='onstar-scd'||project.slug==='avallow'||undefined} className={projectStatus(project)?'project-status-image':undefined}><Artwork crop={project.crop} label={project.imageAlt} source={project.cover} /></div>}{projectStatus(project)&&<div className={`project-status ${projectStatus(project).tone}`}>{projectStatus(project).label}</div>}<div className="project-body"><span className={`project-icon ${project.color}`} ><Icon name={project.icon} /></span><h3>{project.slug==='smartfamily'?<Link href="/projetos/smartfamily">{project.name}</Link>:project.name}</h3><p>{project.description}</p><div className="card-bottom"><Tags items={project.tags} />{project.slug==='smartfamily'?<Link href="/projetos/smartfamily" aria-label={`Conhecer ${project.name}`} className="icon-link"><Icon name="arrow" /></Link>:<DetailButton label={`Conhecer ${project.name}`} title={project.name} className="icon-link"><p>{project.detail}</p><a className="text-link" href={'/projetos/'+project.slug}>Ver projeto completo →</a>{project.technologies.length > 0 && <><h4>Tecnologias documentadas</h4><Tags items={project.technologies} /></>}<p className="disclosure-note">Apresentação da iniciativa. Estágio de desenvolvimento, demonstração e resultados aguardam confirmação do proprietário.</p></DetailButton>}</div></div></article>)}</div>
        </section>
        <section id="consultoria" aria-labelledby="services-title" className="home-section">
          <SectionHeading id="services-title" title="Como posso ajudar" description="Tecnologia, visão de produto e estratégia para o seu próximo passo."><a href="#contato" className="text-link">Vamos conversar <Icon name="arrow" /></a></SectionHeading>
          <div className="services-grid">{services.map((service:any) => <a className="card service-card" href="#contato" key={service.title}><span className={`icon-tile ${service.color}`}><Icon name={service.icon} /></span><div><h3>{service.title}</h3><p>{service.description}</p></div></a>)}</div>
        </section>
        <section id="experiencia" aria-labelledby="experience-title" className="home-section">
          <SectionHeading id="experience-title" title="Minha trajetória profissional" description="Uma trajetória que conecta tecnologia, dados e negócios."><a href="/experiencia" className="text-link">Conheça minha trajetória <Icon name="arrow" /></a></SectionHeading>
          <div className="experience-grid">{experiences.map((experience:any, index:number) => <article className={`card experience-card ${index === 0 ? 'featured-experience' : ''}`} key={experience.company}><div className={`company-wordmark company-${index}`}>{experience.logo?<img src={experience.logo} alt={experience.company} style={{maxWidth:'100%',height:38,objectFit:'contain'}}/>:experience.wordmark==='CAIXA'?<>CAI<span>X</span>A</>:experience.wordmark}</div><p className="experience-period">{experience.period}</p><h3>{experience.company}</h3><p className="experience-role">{experience.displayRole}</p><p>{experience.description}</p><Tags items={experience.tags} /></article>)}<article className="card experience-card earlier-experience"><h3>Outras experiências</h3><ul>{curriculum.experiences.filter(x=>!x.featured).map(x=><li key={x.id}>{x.company}</li>)}</ul></article></div>
          <p className="section-note">Resultados declarados no currículo. A data final da Compass UOL está pendente de confirmação; vínculos simultâneos foram preservados.</p>
        </section>
        <section id="competencias" aria-labelledby="skills-title" className="home-section">
          <SectionHeading id="skills-title" title="Skills & Conhecimentos" description="Tecnologias, metodologias e domínios que conectam ideias a soluções."><a className="text-link" href="/experiencia#competencias">Ver todas as competências <Icon name="arrow" /></a></SectionHeading>
          <div className="skills-grid">{skills.map(skill => <article className="card skill-card" key={skill.title}><h3><span className={skill.color}><Icon name={skill.icon} /></span>{skill.title}</h3><p>{skill.description}</p></article>)}</div>
        </section>
        <section id="artigos" aria-labelledby="articles-title" className="home-section">
          <SectionHeading id="articles-title" title="Artigos" description="Ideias e experiências sobre tecnologia, dados, IA e negócios."><Link className="text-link" href="/artigos">Ver todos os artigos <Icon name="arrow" /></Link></SectionHeading>
          <div className="projects-grid">{articles.map(article=><HomeArticleCard key={article.slug} item={article}/>)}</div>
        </section>
        <section id="videos" aria-labelledby="videos-title" className="home-section videos-section">
          <SectionHeading id="videos-title" title="Vídeos" description="Tutoriais, demonstrações e casos práticos em vídeo."><span className="section-status">Conteúdo em preparação <Icon name="video" /></span></SectionHeading>
          <div className="videos-grid">{videos.map(video => <article className="video-card" key={video.title}><DetailButton title={video.title} label={`Ver informações: ${video.title}`} className="video-thumbnail" customIcon={<><Artwork crop={video.crop} label="" source={video.cover} /><span className="play-mark"><Icon name="play" /></span><span className="video-status">{video.planned?'Em preparação':video.duration||'Assistir'}</span></>}><p>Uma prévia dos temas previstos para este espaço.</p><p className="disclosure-note">{video.planned?'Este vídeo ainda não está publicado. O player será disponibilizado quando houver uma URL real do YouTube cadastrada.':<a href={'/videos/'+video.slug}>Assistir ao vídeo →</a>}</p></DetailButton><h3>{video.title}</h3></article>)}</div>
        </section>
      </OrderedSections></div>
      <section className="contact-section" id="contato" aria-labelledby="contact-title">
        <div className="contact-landscape" aria-hidden="true"><Artwork crop={[613,1119,274,161]} label="" source={settings.banner} /></div>
        <div className="container contact-inner">
          <div className="contact-intro"><p className="eyebrow">VAMOS CONVERSAR?</p><h2 id="contact-title">Grandes ideias começam<br />com uma <span>conversa.</span></h2><p>Seja para um projeto, consultoria, parceria ou investimento,<br className="desktop-break" /> vamos conectar ideias e criar soluções que geram impacto real.</p><div className="contact-values"><div><span className="value-icon"><Icon name="bolt" /></span><span><strong>Novas possibilidades</strong><small>Ideias que ganham forma</small></span></div><div><span className="value-icon"><Icon name="shield" /></span><span><strong>Conversa com propósito</strong><small>Seu contexto vem primeiro</small></span></div><div><span className="value-icon"><Icon name="people" /></span><span><strong>Foco em soluções</strong><small>Do desafio ao próximo passo</small></span></div></div></div>
          <p className="handwritten contact-signature">{(profile.signature||[]).map((line:string,i:number)=><span key={i} style={{display:'contents',fontSize:'inherit'}}>{i>0&&<br/>}{line}</span>)}<span>{profile.title}</span></p>
          <div className="contact-grid"><ContactForm /><aside className="card contact-channels"><h3>Outros canais de contato</h3><p>Escolha como prefere conversar.</p><div className="channel-list">{([{ name: 'LinkedIn', icon: 'linkedin', description: 'Conexões profissionais', color: 'blue' },{ name: 'E-mail', icon: 'mail', description: contacts.email, color: 'blue' },{ name: 'WhatsApp', icon: 'phone', description: 'Uma conversa mais próxima', color: 'green' },{ name: 'YouTube', icon: 'video', description: 'Conteúdo, tutoriais e insights', color: 'red' }] as const).map(channel => <div key={channel.name}>{(channel.name === "E-mail" || channel.name === "WhatsApp" || channel.name === "LinkedIn" && contacts.linkedin || channel.name === "YouTube" && contacts.youtube) ? <a className="channel" href={channel.name === "E-mail" ? "mailto:"+contacts.email : channel.name === "WhatsApp" ? "https://wa.me/"+contacts.whatsapp : channel.name === "LinkedIn" ? contacts.linkedin : contacts.youtube} target={channel.name === "WhatsApp" ? "_blank" : undefined} rel="noopener noreferrer"><span className={`icon-tile ${channel.color}`}><Icon name={channel.icon} /></span><span><strong>{channel.name}</strong><small>{channel.description}</small></span><Icon name="arrow" /></a> : <div className="channel"><span className={`icon-tile ${channel.color}`}><Icon name={channel.icon} /></span><span><strong>{channel.name}</strong><small>{channel.description}</small></span><span className="channel-pending">Em breve</span></div>}</div>)}</div><div className="contact-extras"><div className="schedule"><Icon name="calendar" /><h4>Agendar uma conversa</h4><p>Um espaço para conhecer seu projeto.</p>{settings.scheduleUrl?<a href={settings.scheduleUrl} target="_blank" rel="noopener noreferrer">Agendar uma conversa →</a>:<span>Agenda disponível em breve</span>}</div><div className="privacy-note"><Icon name="lock" /><h4>Seus dados, seu controle</h4><p>Seus dados são usados para responder ao contato e seguem nossa política de privacidade.</p></div></div><p className="channels-note"><a href="/privacidade">Política de privacidade</a></p></aside></div>
          <div className="closing-cta"><div><p className="eyebrow">VAMOS CONSTRUIR O PRÓXIMO CAPÍTULO?</p><h3>Vamos construir o próximo capítulo?</h3><p>Projetos, consultoria, parcerias ou investimento. Uma boa conversa pode ser o começo.</p></div><a className="button white" href="#formulario">Vamos conversar <Icon name="arrow" /></a></div>
        </div>
      </section>
    </main>
    <footer className="footer"><div className="container footer-inner"><a href="#inicio" aria-label="Carlos André, início"><span className="brand"><strong>{(profile.title||'').toUpperCase()}</strong><span>{profile.professionalTitle}</span></span></a><nav aria-label="Navegação do rodapé"><a href="#inicio">Início</a><a href="/sobre">Sobre</a><a href="#projetos">Projetos</a><a href="/experiencia">Experiência</a><a href="#artigos">Artigos</a><a href="#videos">Vídeos</a><a href="#consultoria">Consultoria</a><a href="#contato">Contato</a></nav><p>{(settings.footer||[]).map((line:string,i:number)=><span style={{display:'contents'}} key={i}>{i>0&&<br/>}{line}</span>)}</p></div></footer>
  </>;
}
