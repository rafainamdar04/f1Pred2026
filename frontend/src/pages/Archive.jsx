import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { getTeamColor } from '../constants/teamColors';

const S = {
  wrap: { maxWidth: '1180px', margin: '0 auto', padding: '0 48px' },
  chip: (v) => ({
    display: 'inline-flex', alignItems: 'center',
    fontSize: '9px', fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase',
    padding: '3px 8px', borderRadius: '2px',
    ...(v === 'grn' ? { background: 'rgba(52,208,88,.08)',   color: '#34d058', border: '1px solid rgba(52,208,88,.2)' } :
       v === 'amb' ? { background: 'rgba(245,158,11,.08)', color: '#F59E0B', border: '1px solid rgba(245,158,11,.2)' } :
       v === 'red' ? { background: 'rgba(225,6,0,.1)',     color: '#E10600', border: '1px solid rgba(225,6,0,.2)' } :
                    { background: 'rgba(255,255,255,.04)', color: '#444',    border: '1px solid rgba(255,255,255,.055)' }),
  }),
};

function AccuracyBadge({ accuracy }) {
  if (!accuracy) return null;
  const { hits, p1_correct, has_prediction } = accuracy;
  if (!has_prediction) return <span style={S.chip('muted')}>No prediction</span>;
  const variant = p1_correct ? 'grn' : hits >= 2 ? 'amb' : hits === 1 ? 'muted' : 'red';
  return <span style={S.chip(variant)}>{hits}/3 hits{p1_correct ? ' · P1 ✓' : ''}</span>;
}

function RaceCard({ race, actualResult, accuracy, onClick }) {
  const predicted = accuracy?.predicted_top3 ?? [];
  const actual = accuracy?.actual_top3 ?? [];

  return (
    <div
      onClick={onClick}
      style={{
        background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)',
        borderRadius: '3px', padding: '18px 20px', cursor: 'pointer',
        transition: 'border-color .2s',
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(225,6,0,.3)'}
      onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,.055)'}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: '#444' }}>Round {race.round}</div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <AccuracyBadge accuracy={accuracy} />
          <span style={S.chip('grn')}>Done</span>
        </div>
      </div>

      <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '18px', color: '#fff', marginBottom: '10px' }}>
        {race.name?.replace(' Grand Prix', '') || '—'} GP
      </div>

      {actualResult?.winner && (
        <div style={{ fontSize: '11px', color: '#888', marginBottom: '10px' }}>
          Winner: <span style={{ color: '#fff', fontWeight: 500 }}>{actualResult.winner}</span>
        </div>
      )}

      {/* Prediction vs Actual */}
      {(predicted.length > 0 || actual.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,.055)' }}>
          {[['Predicted', predicted], ['Actual', actual]].map(([label, ids]) => (
            <div key={label}>
              <div style={{ fontSize: '8px', letterSpacing: '1.5px', textTransform: 'uppercase', color: '#444', marginBottom: '4px' }}>{label}</div>
              {ids.map((id, i) => (
                <div key={id} style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '12px', color: i === 0 ? '#fff' : '#666', lineHeight: 1.6 }}>
                  {i + 1}. {id.toUpperCase()}
                </div>
              ))}
              {ids.length === 0 && <div style={{ fontSize: '11px', color: '#444' }}>—</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function Archive() {
  const navigate = useNavigate();
  const { data: calendar } = useApi('/api/calendar');
  const { data: history } = useApi('/api/predictions/history');
  const { data: results } = useApi('/api/race-results');
  const { data: allAccuracy } = useApi('/api/predictions/accuracy');

  const accuracyByRound = {};
  if (allAccuracy) {
    allAccuracy.forEach(a => { accuracyByRound[a.round] = a; });
  }

  // Build predictability leaderboard from history
  const driverStats = {};
  if (history) {
    const byRound = {};
    history.forEach(p => {
      if (!byRound[p.round]) byRound[p.round] = [];
      byRound[p.round].push(p);
    });
    Object.values(byRound).forEach(rows => {
      rows.sort((a, b) => (b.final_score ?? 0) - (a.final_score ?? 0));
      rows.forEach((r, i) => { r._rank = i + 1; });
    });
    history.forEach(p => {
      if (!driverStats[p.driver_id]) {
        driverStats[p.driver_id] = { driver_id: p.driver_id, constructor_id: p.constructor_id, rounds: 0, top3: 0, scores: [] };
      }
      driverStats[p.driver_id].rounds += 1;
      if ((p._rank ?? 999) <= 3) driverStats[p.driver_id].top3 += 1;
      driverStats[p.driver_id].scores.push(p.final_score ?? 0);
    });
  }

  const leaderboard = Object.values(driverStats)
    .map(d => ({ ...d, hitRate: d.rounds > 0 ? (d.top3 / d.rounds) * 100 : 0 }))
    .sort((a, b) => b.hitRate - a.hitRate);

  const completedRaces = results?.races ?? [];
  const races = calendar?.races ?? [];
  const completedRounds = new Set(completedRaces.map(r => r.round));

  const overallHits = allAccuracy ? allAccuracy.reduce((s, a) => s + a.hits, 0) : null;
  const totalPossible = allAccuracy ? allAccuracy.length * 3 : null;

  return (
    <div style={S.wrap}>
      <div style={{ padding: '56px 0 80px' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '52px' }}>
          <div>
            <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#444', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '14px', height: '1px', background: '#E10600', display: 'inline-block' }} />
              Season History
            </div>
            <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: 'clamp(24px, 2.5vw, 36px)', color: '#fff', letterSpacing: '-.5px', lineHeight: 1 }}>Season Archive</div>
          </div>
          <div style={{ fontSize: '10px', color: '#444', textAlign: 'right', lineHeight: 1.8, fontFamily: "'DM Mono', monospace" }}>
            {completedRaces.length} races complete<br />
            {overallHits !== null ? `${overallHits}/${totalPossible} top-3 hits overall` : 'All predictions & results'}
          </div>
        </div>

        {/* Completed race cards */}
        {completedRaces.length > 0 && (
          <div style={{ marginBottom: '52px' }}>
            <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#444', marginBottom: '16px' }}>Race Results</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
              {completedRaces.map(race => (
                <RaceCard
                  key={race.round}
                  race={race}
                  actualResult={race}
                  accuracy={accuracyByRound[race.round] ?? null}
                  onClick={() => navigate(`/race/${race.round}`)}
                />
              ))}
            </div>
          </div>
        )}

        {completedRaces.length === 0 && (
          <div style={{ background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px', padding: '40px', textAlign: 'center', fontSize: '12px', color: '#444', marginBottom: '52px' }}>
            No completed races yet
          </div>
        )}

        {/* Predictability leaderboard */}
        <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#444', marginBottom: '16px' }}>Model Predictability Leaderboard</div>
        {leaderboard.length === 0 ? (
          <div style={{ background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px', padding: '40px', textAlign: 'center', fontSize: '12px', color: '#444' }}>
            No prediction history yet
          </div>
        ) : (
          <div style={{ background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['Rank', 'Driver', 'Rounds', 'Top-3 picks', 'Hit Rate'].map(h => (
                    <th key={h} style={{ fontSize: '8px', letterSpacing: '2px', textTransform: 'uppercase', color: '#444', padding: '10px 18px', textAlign: 'left', borderBottom: '1px solid rgba(255,255,255,.055)', background: '#101010', fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((d, idx) => {
                  const tc = getTeamColor(d.constructor_id);
                  const isBest = idx === 0;
                  const isWorst = idx === leaderboard.length - 1;
                  return (
                    <tr key={d.driver_id} style={{ borderBottom: '1px solid rgba(255,255,255,.025)' }}>
                      <td style={{ padding: '10px 18px', fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: '18px', color: '#444' }}>{idx + 1}</td>
                      <td style={{ padding: '10px 18px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ width: '3px', height: '28px', borderRadius: '1px', background: tc, flexShrink: 0 }} />
                          <div>
                            <div style={{ fontSize: '13px', fontWeight: 500, color: '#fff' }}>{d.driver_id.toUpperCase()}</div>
                            <div style={{ fontSize: '10px', color: '#444' }}>{d.constructor_id}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '10px 18px', fontSize: '13px', color: '#fff' }}>{d.rounds}</td>
                      <td style={{ padding: '10px 18px', fontSize: '13px', color: '#fff' }}>{d.top3}</td>
                      <td style={{ padding: '10px 18px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div style={{ flex: 1, maxWidth: '160px', height: '2px', background: '#1a1a1a', borderRadius: '1px', overflow: 'hidden' }}>
                            <div style={{ height: '100%', background: tc, width: `${d.hitRate}%`, transition: 'width .5s ease' }} />
                          </div>
                          <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '16px', color: '#fff', minWidth: '44px', textAlign: 'right' }}>{d.hitRate.toFixed(0)}%</div>
                          {isBest && <span style={{ fontSize: '9px', background: '#27F4D2', color: '#000', padding: '2px 6px', borderRadius: '2px', fontWeight: 700 }}>FAVOURITE</span>}
                          {isWorst && <span style={{ fontSize: '9px', background: '#E10600', color: '#fff', padding: '2px 6px', borderRadius: '2px', fontWeight: 700 }}>CHAOS</span>}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
