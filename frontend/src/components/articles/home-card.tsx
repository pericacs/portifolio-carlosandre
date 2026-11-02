import {Article,ArticleCard} from './card';
export function HomeArticleCard({item}:{item:Article}){return <div className="home-article-card"><ArticleCard item={item}/></div>;}
