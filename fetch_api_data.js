import { F1Api } from '@f1api/sdk';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const f1Api = new F1Api();
const dataDir = path.join(__dirname, 'data');

// Ensure data directory exists
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

/**
 * Convert array of objects to CSV
 */
function arrayToCSV(data, headers = null) {
  if (data.length === 0) return '';
  
  // Get headers from first object if not provided
  const cols = headers || Object.keys(data[0]);
  
  // CSV header
  let csv = cols.join(',') + '\n';
  
  // CSV rows
  for (let row of data) {
    csv += cols.map(col => {
      let val = row[col] ?? '';
      // Escape quotes and wrap in quotes if contains comma/newline
      if (typeof val === 'string' && (val.includes(',') || val.includes('\n') || val.includes('"'))) {
        val = '"' + val.replace(/"/g, '""') + '"';
      }
      return val;
    }).join(',') + '\n';
  }
  
  return csv;
}

/**
 * Save data to CSV file
 */
function saveCSV(filename, data) {
  const filepath = path.join(dataDir, filename);
  const csv = arrayToCSV(data);
  fs.writeFileSync(filepath, csv);
  console.log(`✓ Saved ${data.length} records to ${filename}`);
}

/**
 * Fetch 2026 season data
 */
async function fetch2026Data() {
  console.log('=' .repeat(70));
  console.log('F1 API SDK - 2026 SEASON DATA FETCHER');
  console.log('=' .repeat(70));
  
  try {
    console.log('\n📊 [1] FETCHING DRIVERS');
    console.log('-'.repeat(70));
    const drivers = await f1Api.getDrivers();
    console.log(`✓ Fetched ${drivers.length} drivers`);
    
    console.log('\n📊 [2] FETCHING 2026 RACES');
    console.log('-'.repeat(70));
    const races2026 = await f1Api.getRacesByYear(2026);
    console.log(`✓ Fetched ${races2026.length} races for 2026`);
    
    console.log('\n📊 [3] FETCHING 2026 DRIVER STANDINGS');
    console.log('-'.repeat(70));
    const standings2026 = await f1Api.getStandingsByYear(2026);
    console.log(`✓ Fetched standings for 2026`);
    
    console.log('\n📊 [4] FETCHING RACE RESULTS & QUALIFYING');
    console.log('-'.repeat(70));
    
    let allResults = [];
    let allQualifying = [];
    
    for (const race of races2026) {
      const raceNum = race.round;
      const raceName = race.name;
      console.log(`  Round ${raceNum}: ${raceName}`);
      
      try {
        // Get race results
        const results = await f1Api.getResultsByYearAndRound(2026, raceNum);
        if (results && results.length > 0) {
          const enrichedResults = results.map(r => ({
            season: 2026,
            round: raceNum,
            race_name: raceName,
            circuit_name: race.circuit?.name || 'Unknown',
            driver_id: r.driver?.id,
            driver_code: r.driver?.code,
            driver_name: r.driver?.name,
            driver_number: r.driver?.number,
            constructor_id: r.constructor?.id,
            constructor_name: r.constructor?.name,
            grid_position: r.grid,
            finish_position: r.position,
            points: r.points,
            status: r.status,
            time: r.time,
          }));
          allResults.push(...enrichedResults);
          console.log(`    ✓ Results: ${results.length} drivers`);
        }
      } catch (e) {
        console.log(`    ⚠ Results not available yet`);
      }
      
      try {
        // Get qualifying results
        const qualifying = await f1Api.getQualifyingByYearAndRound(2026, raceNum);
        if (qualifying && qualifying.length > 0) {
          const enrichedQual = qualifying.map(q => ({
            season: 2026,
            round: raceNum,
            race_name: raceName,
            circuit_name: race.circuit?.name || 'Unknown',
            grid_position: q.position,
            driver_id: q.driver?.id,
            driver_code: q.driver?.code,
            driver_name: q.driver?.name,
            driver_number: q.driver?.number,
            constructor_id: q.constructor?.id,
            constructor_name: q.constructor?.name,
            q1_time: q.Q1,
            q2_time: q.Q2,
            q3_time: q.Q3,
          }));
          allQualifying.push(...enrichedQual);
          console.log(`    ✓ Qualifying: ${qualifying.length} drivers`);
        }
      } catch (e) {
        console.log(`    ⚠ Qualifying not available yet`);
      }
    }
    
    // Save to CSV
    console.log('\n📁 SAVING DATA TO CSV');
    console.log('-'.repeat(70));
    
    // Parse standings to flat structure
    const standingsFlat = [];
    if (standings2026 && standings2026.length > 0) {
      const standingsList = standings2026[0]?.standingsLists || [];
      if (standingsList.length > 0) {
        const driverStandings = standingsList[0]?.driverStandings || [];
        driverStandings.forEach((standing, idx) => {
          standingsFlat.push({
            position: idx + 1,
            driver_id: standing.driver?.id,
            driver_code: standing.driver?.code,
            driver_name: standing.driver?.name,
            driver_number: standing.driver?.number,
            constructor_id: standing.constructor?.id,
            constructor_name: standing.constructor?.name,
            points: standing.points,
            wins: standing.wins,
          });
        });
      }
    }
    
    saveCSV('2026_standings.csv', standingsFlat);
    saveCSV('2026_race_results.csv', allResults);
    saveCSV('2026_qualifying.csv', allQualifying);
    
    // Summary
    console.log('\n' + '='.repeat(70));
    console.log('2026 SEASON DATA SUMMARY');
    console.log('='.repeat(70));
    
    console.log(`\n📊 STANDINGS: ${standingsFlat.length} drivers`);
    if (standingsFlat.length > 0) {
      console.log('  Top 5:');
      standingsFlat.slice(0, 5).forEach(d => {
        console.log(`    ${d.position}. ${d.driver_code} ${d.driver_name} (${d.constructor_name}) - ${d.points} pts`);
      });
    }
    
    console.log(`\n🏁 RACE RESULTS: ${allResults.length} total entries`);
    const roundsWithResults = [...new Set(allResults.map(r => r.round))].sort((a, b) => a - b);
    if (roundsWithResults.length > 0) {
      console.log(`  Races completed: ${roundsWithResults.join(', ')}`);
    }
    
    console.log(`\n🏆 QUALIFYING: ${allQualifying.length} total entries`);
    const roundsWithQual = [...new Set(allQualifying.map(q => q.round))].sort((a, b) => a - b);
    if (roundsWithQual.length > 0) {
      console.log(`  Qualifying sessions: ${roundsWithQual.join(', ')}`);
      
      // Show Suzuka grid if available
      const suzukaQual = allQualifying.filter(q => q.round === 3);
      if (suzukaQual.length > 0) {
        console.log(`\n  Suzuka (Round 3) Grid (${suzukaQual.length} drivers):`);
        suzukaQual.slice(0, 12).forEach(q => {
          console.log(`    ${q.grid_position}. ${q.driver_code} ${q.driver_name} (${q.constructor_name})`);
        });
      }
    }
    
    console.log('\n' + '='.repeat(70));
    console.log('✓ DATA COLLECTION COMPLETE - Ready for Python analysis');
    console.log('='.repeat(70));
    
  } catch (error) {
    console.error(`❌ Error: ${error.message}`);
    console.error(error);
  }
}

// Run
fetch2026Data();
