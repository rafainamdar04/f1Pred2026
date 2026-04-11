import { F1Api } from '@f1api/sdk';

const f1Api = new F1Api();

// List available methods
const methods = Object.getOwnPropertyNames(Object.getPrototypeOf(f1Api))
  .filter(n => !n.startsWith('_') && n !== 'constructor');

console.log('Available F1Api methods:');
methods.forEach(m => console.log(`  - ${m}`));

// Try to get 2025 data first
console.log('\n\nAttempting to fetch 2025 season data...');
try {
  const races2025 = await f1Api.getRacesByYear(2025);
  console.log(`✓ Fetched ${races2025?.length || 0} races for 2025`);
} catch (e) {
  console.log(`✗ Error: ${e.message}`);
}

// Try to get standings
console.log('\nAttempting to fetch standings...');
try {
  const standings = await f1Api.getStandingsByYear(2025);
  console.log(`✓ Fetched standings for 2025:`, standings);
} catch (e) {
  console.log(`✗ Error: ${e.message}`);
}
