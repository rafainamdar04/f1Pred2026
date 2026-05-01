// Simplified SVG track outlines + metadata keyed by GP name substring
export const CIRCUIT_SVG = {
  Australian:  { path: 'M15,15 L72,15 L82,22 L85,32 L82,40 L72,50 Q60,56 48,52 L38,48 L28,50 L16,46 L10,36 L10,24 Z', viewBox: '0 0 98 68' },
  Chinese:     { path: 'M12,12 L80,12 L88,20 L88,30 L68,30 L68,44 Q68,58 52,58 Q36,58 36,44 L36,30 L12,30 L8,22 Z', viewBox: '0 0 98 68' },
  Japanese:    { path: 'M8,20 Q8,8 22,8 Q38,8 38,22 L38,46 Q38,60 52,60 Q68,60 68,46 Q68,32 54,32 L38,32', viewBox: '0 0 78 68' },
  Bahrain:     { path: 'M14,18 L70,18 L82,28 L82,40 L70,52 Q56,58 42,52 L28,52 L14,40 L8,30 Z', viewBox: '0 0 92 68' },
  Saudi:       { path: 'M12,8 L80,8 L88,16 L88,60 L78,60 L78,24 L24,24 L24,60 L12,60 Z', viewBox: '0 0 100 68' },
  Miami:       { path: 'M12,18 L78,18 L88,28 L88,50 L78,58 L54,58 L54,48 L36,48 L36,58 L12,58 L6,48 L6,28 Z', viewBox: '0 0 96 68' },
  Monaco:      { path: 'M8,56 L8,28 Q8,8 28,8 L60,8 L80,18 L90,32 L78,46 L58,52 Q48,56 48,64 L32,66 Q14,66 8,56', viewBox: '0 0 100 74' },
  Canadian:    { path: 'M14,14 L66,14 L80,22 L84,36 L80,50 L66,58 L46,58 L46,48 L26,48 L14,56 L8,46 L8,24 Z', viewBox: '0 0 94 72' },
  Spanish:     { path: 'M10,28 L10,18 L60,18 L74,18 L84,26 L84,48 L70,58 Q52,62 38,54 L24,58 L10,48 Z', viewBox: '0 0 96 72' },
  Austrian:    { path: 'M22,10 L64,10 L76,20 L80,36 L68,50 L80,58 L68,66 L50,62 L40,66 L22,58 L10,46 L14,28 Z', viewBox: '0 0 92 76' },
  British:     { path: 'M20,12 L62,12 L78,22 L82,40 L70,54 L54,60 L38,58 L22,60 L8,48 L6,30 Z', viewBox: '0 0 90 72' },
  Belgian:     { path: 'M8,16 L48,16 L72,8 L88,18 L88,38 L72,48 L56,44 L40,52 L24,60 L8,52 Z', viewBox: '0 0 96 68' },
  Hungarian:   { path: 'M16,14 L62,14 L76,24 L76,38 L62,50 L48,44 L36,50 L22,60 L10,50 L8,32 Z', viewBox: '0 0 86 72' },
  Dutch:       { path: 'M14,10 Q6,10 6,22 L6,48 Q6,60 18,62 L62,62 Q76,62 78,50 L78,36 L68,28 L78,22 Q80,10 68,10 Z', viewBox: '0 0 86 74' },
  Italian:     { path: 'M10,10 L86,10 L86,58 L10,58 Z M30,10 L30,32 Q30,42 44,42 Q58,42 58,32 L58,10', viewBox: '0 0 98 68' },
  Madrid:      { path: 'M12,8 L72,8 L84,18 L84,32 L70,38 L84,48 L72,60 L12,60 L4,50 L4,18 Z', viewBox: '0 0 90 68' },
  Azerbaijan:  { path: 'M8,10 L80,10 L90,20 L90,58 L80,58 L78,28 L24,28 L24,58 L8,58 Z', viewBox: '0 0 100 68' },
  Singapore:   { path: 'M8,54 L8,20 L22,8 L62,8 L76,20 L90,20 L90,38 L76,52 L56,52 L56,62 L24,62 Z', viewBox: '0 0 100 70' },
  'United States': { path: 'M8,56 L8,24 L22,10 L58,10 L58,28 L44,28 L44,40 L72,40 L86,28 L86,56 L60,56 L60,48 L28,48 L28,56 Z', viewBox: '0 0 96 66' },
  'Mexico City': { path: 'M14,14 L70,14 L82,24 L82,38 L60,38 L60,50 L82,50 L82,58 L14,58 L6,48 L6,24 Z', viewBox: '0 0 90 72' },
  'Sao Paulo':  { path: 'M12,18 Q6,10 16,6 L68,6 Q80,6 82,16 L84,38 Q86,54 72,58 L42,62 Q22,64 14,54 Z', viewBox: '0 0 92 68' },
  'Las Vegas':  { path: 'M8,10 L84,10 L84,20 L54,20 L54,48 L84,48 L84,58 L8,58 L8,48 L38,48 L38,20 L8,20 Z', viewBox: '0 0 94 68' },
  Qatar:        { path: 'M14,12 L74,12 L86,22 L88,38 L80,50 L68,56 L46,58 Q24,60 14,48 L6,36 L8,22 Z', viewBox: '0 0 96 68' },
  'Abu Dhabi':  { path: 'M8,14 L64,14 L76,24 L80,36 L76,44 L64,50 L64,58 L30,58 L30,50 L8,50 L4,40 L4,24 Z', viewBox: '0 0 86 72' },
};

export function getCircuitSvg(raceName) {
  for (const [key, val] of Object.entries(CIRCUIT_SVG)) {
    if (raceName.includes(key)) return val;
  }
  return null;
}
