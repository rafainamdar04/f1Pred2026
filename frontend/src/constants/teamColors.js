export const TEAM_COLORS = {
  'Mercedes': '#27F4D2',
  'Ferrari': '#E8002D',
  'McLaren': '#FF8000',
  'Red Bull Racing': '#3671C6',
  'Alpine': '#FF87BC',
  'Haas': '#AAAAAA',
  'Haas F1 Team': '#AAAAAA',
  'Williams': '#64C4FF',
  'Aston Martin': '#358C75',
  'Racing Bulls': '#6692FF',
  'RB': '#6692FF',
  'Audi': '#BB0000',
  'Cadillac': '#C0A060',
};

export const TEAM_ABBR = {
  'Mercedes': 'MER',
  'Ferrari': 'FER',
  'McLaren': 'MCL',
  'Red Bull Racing': 'RBR',
  'Alpine': 'ALP',
  'Haas': 'HAA',
  'Haas F1 Team': 'HAA',
  'Williams': 'WIL',
  'Aston Martin': 'AMR',
  'Racing Bulls': 'RB',
  'RB': 'RB',
  'Audi': 'AUD',
  'Cadillac': 'CAD',
};

export const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export function getTeamColor(name) {
  if (!name) return '#444';
  if (TEAM_COLORS[name]) return TEAM_COLORS[name];
  const l = name.toLowerCase();
  if (l.includes('mercedes')) return '#27F4D2';
  if (l.includes('ferrari')) return '#E8002D';
  if (l.includes('mclaren')) return '#FF8000';
  if (l.includes('red bull')) return '#3671C6';
  if (l.includes('alpine')) return '#FF87BC';
  if (l.includes('haas')) return '#AAAAAA';
  if (l.includes('williams')) return '#64C4FF';
  if (l.includes('aston martin')) return '#358C75';
  if (l.includes('racing bulls') || l === 'rb') return '#6692FF';
  if (l.includes('audi') || l.includes('sauber') || l.includes('alfa romeo')) return '#BB0000';
  if (l.includes('cadillac') || l.includes('andretti')) return '#C0A060';
  return '#444';
}

export function getTeamAbbr(name) {
  if (!name) return '???';
  if (TEAM_ABBR[name]) return TEAM_ABBR[name];
  return name.slice(0, 3).toUpperCase();
}
