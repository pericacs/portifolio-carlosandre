import type { CSSProperties } from 'react';
export type Crop = readonly [number, number, number, number];
// Visual windows into the original reference; all layout and text are HTML.
export function Artwork({ crop: [x,y,width,height], label, source }: {crop: Crop; label: string; source?:string}) {
  if(source)return <img className="artwork" src={source} alt={label} style={{width:'100%',height:'auto'}}/>;
  const style = { aspectRatio: `${width} / ${height}`, backgroundImage: 'url("/images/reference-artwork.png")', backgroundSize: `${887/width*100}% ${1774/height*100}%`, backgroundPosition: `${x/(887-width)*100}% ${y/(1774-height)*100}%` } as CSSProperties;
  return <div className="artwork" style={style} role={label ? 'img' : undefined} aria-label={label || undefined} aria-hidden={!label || undefined} />;
}
