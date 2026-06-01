import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { getTeamColor } from '../constants/teamColors';

const S = {
  wrap: { maxWidth: '1180px', margin: '0 auto', padding: '0 48px' },
  chip: (v) => ({
    display: 'inline-flex', alignItems: 'center',
    fontSize: '9px', fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase',
    padding: '3px 8px', borderRadius: '2px',
    ...(v === 'grn'  ? { background: 'rgba(52,208,88,.08)',   color: '#34d058', border: '1px solid rgba(52,208,88,.2)' }  :
       v === 'amb'  ? { background: 'rgba(245,158,11,.08)', color: '#F59E0B', border: '1px solid rgba(245,158,11,.2)' } :
       v === 'red'  ? { background: 'rgba(225,6,0,.1)',     color: '#E10600', border: '1px solid rgba(225,6,0,.2)' }   :
                     { background: 'rgba(255,255,255,.04)', color: '#444',    border: '1px solid rgba(255,255,255,.055)' }),
  }),
};

const fmtDate = (d) => {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};

function AccuracyBadge({ accuracy }) {
  if (!accuracy) return null;
  const { hits, p1_correct, has_prediction } = accuracy;
  if (!has_prediction) return <span style={S.chip('muted')}>No prediction</span>;
  const variant = p1_correct ? 'grn' : hits >= 2 ? 'amb' : hits === 1 ? 'muted' : 'red';
  return <span style={S.chip(variant)}>{hits}/3 hits{p1_correct ? ' · P1 ✓' : ''}</span>;
}

function CompletedRaceCard({ race, calRace, accuracy, onClick }) {
  const predicted = accuracy?.predicted_top3 ?? [];
  const actual    = accuracy?.actual_top3 ?? [];
  const isSprint  = race.is_sprint || calRace?.is_sprint;
  const sprintP1  = race.sprint_podium?.[0];

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
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: '#444' }}>Round {race.round}</div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          {isSprint && <span style={S.chip('amb')}>Sprint</span>}
          <AccuracyBadge accuracy={accuracy} />
          <span style={S.chip('grn')}>Done</span>
        </div>
      </div>

      {/* Race name */}
      <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '18px', color: '#fff', marginBottom: '10px' }}>
        {race.name?.replace(' Grand Prix', '') || '—'} GP
      </div>

      {/* Race winner */}
      {race.winner && (
        <div style={{ fontSize: '11px', color: '#888', marginBottom: isSprint && sprintP1 ? '4px' : '10px' }}>
          Race winner: <span style={{ color: '#fff', fontWeight: 500 }}>{race.winner}</span>
        </div>
      )}

      {/* Sprint winner */}
      {isSprint && sprintP1 && (
        <div style={{ fontSize: '11px', color: '#888', marginBottom: '10px' }}>
          Sprint winner: <span style={{ color: '#F59E0B', fontWeight: 500 }}>
            {(sprintP1.driver_name || sprintP1.driver_id || '').split(' ').pop()}
          </span>
          <span style={{ color: '#555', marginLeft: '6px' }}>+{sprintP1.points} pts</span>
        </div>
      )}

      {/* Sprint top 3 points row */}
      {isSprint && race.sprint_podium?.length > 0 && (
        <div style={{ display: 'flex', gap: '6px', marginBottom: '10px', flexWrap: 'wrap' }}>
          {race.sprint_podium.slice(0, 3).map((p, i) => {
            const tc = getTeamColor(p.constructor_name || '');
            return (
              <div key={p.driver_id || i} style={{
                display: 'flex', alignItems: 'center', gap: '4px',
                background: 'rgba(245,158,11,.06)', border: '1px solid rgba(245,158,11,.15)',
                borderRadius: '2px', padding: '3px 8px',
              }}>
                <div style={{ width: '2px', height: '14px', background: tc, borderRadius: '1px' }} />
                <span style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '11px', color: i === 0 ? '#F59E0B' : '#888' }}>
                  {i + 1}. {(p.driver_name || p.driver_id || '').split(' ').pop().toUpperCase()}
                </span>
                <span style={{ fontSize: '9px', color: '#555' }}>+{p.points}</span>
              </div>
            );
          })}
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

function UpcomingRaceCard({ race, onClick }) {
  const isSprint = race.is_sprint;
  return (
    <div
      onClick={onClick}
      style={{
        background: '#0a0a0a', border: '1px solid rgba(255,255,255,.03)',
        borderRadius: '3px', padding: '18px 20px', cursor: 'pointer',
        opacity: 0.7, transition: 'opacity .2s, border-color .2s',
      }}
      onMouseEnter={e => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.borderColor = 'rgba(255,255,255,.1)'; }}
      onMouseLeave={e => { e.currentTarget.style.opacity = '0.7'; e.currentTarget.style.borderColor = 'rgba(255,255,255,.03)'; }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: '#333' }}>Round {race.round}</div>
        <div style={{ display: 'flex', gap: '6px' }}>
          {isSprint && <span style={S.chip('amb')}>Sprint</span>}
          <span style={S.chip('muted')}>Upcoming</span>
        </div>
      </div>
      <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '18px', color: '#555', marginBottom: '8px' }}>
        {race.name?.replace(' Grand Prix', '') || '—'} GP
      </div>
      <div style={{ fontSize: '11px', color: '#333' }}>{fmtDate(race.date)}</div>
    </div>
  );
}

export function Archive() {
  const navigate = useNavigate();
  const { data: calendar }    = useApi('/api/calendar');
  const { data: history }     = useApi('/api/predictions/history');
  const { data: results }     = useApi('/api/race-results');
  const { data: allAccuracy } = useApi('/api/predictions/accuracy');
  const { data: status }      = useApi('/api/status');

  const accuracyByRound = {};
  if (allAccuracy) allAccuracy.forEach(a => { accuracyByRound[a.round] = a; });

  const resultsByRound = {};
  if (results?.races) results.races.forEach(r => { resultsByRound[r.round] = r; });

  const calByRound = {};
  if (calendar?.races) calendar.races.forEach(r => { calByRound[r.round] = r; });

  const roundsComplete = status?.rounds_completed ?? (results?.races?.length ?? 0);
  const allCalendarRaces = calendar?.races ?? [];
  const completedRaces   = allCalendarRaces.filter(r => r.round <= roundsComplete && resultsByRound[r.round]);
  const upcomingRaces    = allCalendarRaces.filter(r => r.round > roundsComplete || !resultsByRound[r.round]);

  // Predictability leaderboard from history
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

  const overallHits    = allAccuracy ? allAccuracy.reduce((s, a) => s + a.hits, 0) : null;
  const totalPossible  = allAccuracy ? allAccuracy.length * 3 : null;
  const sprintRounds   = allCalendarRaces.filter(r => r.is_sprint).length;

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
            {completedRaces.length} / {allCalendarRaces.length} races complete<br />
            {sprintRounds > 0 && `${sprintRounds} sprint weekends · `}
            {overallHits !== null ? `${overallHits}/${totalPossible} top-3 hits` : 'All predictions & results'}
          </div>
        </div>

        {/* Completed races */}
        {completedRaces.length > 0 && (
          <div style={{ marginBottom: '52px' }}>
            <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#444', marginBottom: '16px' }}>
              Completed — {completedRaces.length} races
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
              {completedRaces.map(calRace => {
                const race = resultsByRound[calRace.round] ?? calRace;
                return (
                  <CompletedRaceCard
                    key={calRace.round}
                    race={race}
                    calRace={calRace}
                    accuracy={accuracyByRound[calRace.round] ?? null}
                    onClick={() => navigate(`/race/${calRace.round}`)}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* Upcoming races */}
        {upcomingRaces.length > 0 && (
          <div style={{ marginBottom: '52px' }}>
            <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#333', marginBottom: '16px' }}>
              Remaining — {upcomingRaces.length} races
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px' }}>
              {upcomingRaces.map(race => (
                <UpcomingRaceCard
                  key={race.round}
                  race={race}
                  onClick={() => navigate(`/race/${race.round}`)}
                />
              ))}
            </div>
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
                  const isBest  = idx === 0;
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
                          {isBest  && <span style={{ fontSize: '9px', background: '#27F4D2', color: '#000', padding: '2px 6px', borderRadius: '2px', fontWeight: 700 }}>FAVOURITE</span>}
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
