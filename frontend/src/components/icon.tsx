const paths = {
  arrow:'M4 12h15m-5-5 5 5-5 5', cube:'m12 3 9 5-9 5-9-5 9-5ZM3 8v9l9 5 9-5V8M12 13v9M7.5 5.5l9 5',
  database:'M20 6c0 2-3.6 3-8 3S4 8 4 6s3.6-3 8-3 8 1 8 3ZM4 6v6c0 2 3.6 3 8 3s8-1 8-3V6M4 12v6c0 2 3.6 3 8 3s8-1 8-3v-6',
  brain:'M9 4a3 3 0 0 0-5 3 4 4 0 0 0-1 7 4 4 0 0 0 5 6c2 1 4-1 4-3V7c0-3-2-4-3-3Zm6 0a3 3 0 0 1 5 3 4 4 0 0 1 1 7 4 4 0 0 1-5 6c-2 1-4-1-4-3M7 8l2 2-1 3M17 8l-2 2 1 3M8 17l4-2 4 2',
  people:'M9 7a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm12 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0ZM1 20v-3a5 5 0 0 1 10 0v3H1Zm12 0v-3a5 5 0 0 1 10 0v3H13Z',
  chart:'M4 20V10h4v10M10 20V6h4v14M16 20V2h4v18M3 7l6-4 5 1 6-3',rocket:'M14 4 21 3l-1 7-9 9-6-6 9-9ZM14 4l-7 1-4 5 5 1M20 10l-1 7-5 4-1-5M4 17l-2 5 5-2M15 8h.01',
  cloud:'M7 18a5 5 0 1 1 0-10 7 7 0 0 1 13 3 3.5 3.5 0 0 1-1 7H7Z',code:'m8 7-5 5 5 5m8-10 5 5-5 5M14 4l-4 16',card:'M3 5h18v14H3V5ZM3 10h18M7 15h3',bolt:'m13 2-9 12h7l-1 8 10-13h-8l1-7Z',
  shield:'m12 3 9 4v6c0 4-5 7-9 9-4-2-9-5-9-9V7l9-4Zm-4 9 3 3 5-6',lock:'M6 10h12v11H6V10ZM8 10V6a4 4 0 0 1 8 0v4M12 14v3',mail:'M3 5h18v14H3V5Zm0 0 9 8 9-8',
  phone:'M21 11a9 9 0 0 1-13 8l-6 2 2-6A9 9 0 1 1 21 11ZM8 7c-1 6 3 9 8 9l1-3-3-1-1 1-2-2 1-1-2-3H8Z',linkedin:'M4 9v11M4 4v.01M10 20V9h4v2c4-4 7-1 7 3v6M10 14c0-5 4-5 4 0v6',
  video:'M4 5h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Zm6 4 6 3-6 3V9Z',play:'m9 5 11 7-11 7V5Z','play-circle':'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0ZM10 8l6 4-6 4V8Z',
  calendar:'M4 5h16v16H4V5ZM8 2v6m8-6v6M4 10h16M8 14h1m6 0h1m-8 4h1m6 0h1',document:'M5 3h10l4 4v14H5V3Zm10 0v5h4M8 12h8m-8 4h6',network:'M9 3h6v6H9V3ZM2 16h6v6H2v-6Zm14 0h6v6h-6v-6ZM12 9v4M5 16v-3h14v3',menu:'M3 6h18M3 12h18M3 18h18',close:'m6 6 12 12M6 18 18 6',check:'m5 12 4 4L19 6',
} as const;
export type IconName = keyof typeof paths;
export function Icon({name}: {name: IconName}) { return <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>; }
