import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { getTeamColor } from '../constants/teamColors';
import { getCircuitSvg } from '../constants/circuits';

const S = {
  wrap: { maxWidth: '1180px', margin: '0 auto', padding: '0 48px' },
  chip: (v) => ({
    display: 'inline-flex', alignItems: 'center',
    fontSize: '9px', fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase',
    padding: '3px 8px', borderRadius: '2px',
    ...(v === 'red'       ? { background: 'rgba(225,6,0,.1)',     color: '#E10600', border: '1px solid rgba(225,6,0,.2)' }  :
       v === 'grn'       ? { background: 'rgba(52,208,88,.08)',   color: '#34d058', border: '1px solid rgba(52,208,88,.2)' } :
       v === 'amb'       ? { background: 'rgba(245,158,11,.08)', color: '#F59E0B', border: '1px solid rgba(245,158,11,.2)' } :
                           { background: 'rgba(255,255,255,.04)', color: '#444',    border: '1px solid rgba(255,255,255,.055)' }),
  }),
};

/* ── Determine race status from calendar + results ── */
function getRaceStatus(race, resultsRounds, roundsComplete) {
  if (resultsRounds?.includes(race.round)) return 'done';
  if (race.round === roundsComplete + 1) return 'next';
  if (race.round <= roundsComplete) return 'done';
  return 'upcoming';
}

/* ── Circuit card ── */
function CircuitCard({ race, selected, status, onClick }) {
  const svg = getCircuitSvg(race.name);
  const isCancelled = status === 'cancelled';
  const isNext = status === 'next';
  const isDone = status === 'done';

  const fmtDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  };

  return (
    <div
      onClick={isCancelled ? undefined : onClick}
      style={{
        flex: '0 0 130px', borderRadius: '3px', padding: '14px 12px 12px',
        cursor: isCancelled ? 'default' : 'pointer',
        display: 'flex', flexDirection: 'column', gap: '8px',
        position: 'relative', overflow: 'hidden',
        transition: 'border-color .2s, background .2s',
        opacity: isCancelled ? .25 : isDone ? .75 : 1,
        background: selected ? 'rgba(225,6,0,.04)' : '#101010',
        border: selected ? '1px solid #E10600' : isNext ? '1px solid rgba(225,6,0,.35)' : '1px solid rgba(255,255,255,.055)',
        borderStyle: isCancelled ? 'dashed' : 'solid',
      }}
    >
      {/* SVG track */}
      <div style={{ width: '100%', height: '54px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {svg ? (
          <svg viewBox={svg.viewBox} width="106" height="54" style={{ overflow: 'visible' }}>
            <path
              d={svg.path}
              fill="none"
              stroke={selected ? '#E10600' : isDone ? 'rgba(255,255,255,.45)' : 'rgba(255,255,255,.18)'}
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ transition: 'stroke .2s' }}
            />
          </svg>
        ) : (
          <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: '24px', color: selected ? '#E10600' : 'rgba(255,255,255,.18)' }}>
            {race.short}
          </div>
        )}
      </div>
      <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '2.5px', textTransform: 'uppercase', color: '#444' }}>
        {race.short}
      </div>
      <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '13px', color: '#fff', lineHeight: 1.15 }}>
        {race.name.replace(' Grand Prix', '')}
      </div>
      <div style={{ fontSize: '9px', color: '#444' }}>{fmtDate(race.date)}</div>
      <div style={{ marginTop: '2px' }}>
        {isDone      && <span style={S.chip('muted')}>Done</span>}
        {isNext      && <span style={S.chip('red')}>Next</span>}
        {isCancelled && <span style={{ ...S.chip('muted'), opacity: .5 }}>Cancelled</span>}
      </div>
    </div>
  );
}

/* ── Prediction column ── */
function PredCol({ title, rows, updatedAt = null, showDelta = false, preRanks = {} }) {
  const formatRelative = (value) => {
    if (!value) return 'Updated unknown';
    const then = new Date(value).getTime();
    if (Number.isNaN(then)) return 'Updated unknown';
    const diffMinutes = Math.max(0, Math.floor((Date.now() - then) / 60000));
    if (diffMinutes < 1) return 'Updated just now';
    if (diffMinutes < 60) return `Updated ${diffMinutes}m ago`;
    const hours = Math.floor(diffMinutes / 60);
    if (hours < 24) return `Updated ${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `Updated ${days}d ago`;
  };

  if (!rows || rows.length === 0) {
    return (
      <div style={{ background: '#101010', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ padding: '12px 18px', borderBottom: '1px solid rgba(255,255,255,.055)' }}>
          <div style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '2.5px', textTransform: 'uppercase', color: '#888' }}>{title}</div>
          <div style={{ fontSize: '9px', color: '#444', marginTop: '4px' }}>{formatRelative(updatedAt)}</div>
        </div>
        <div style={{ padding: '48px 24px', textAlign: 'center' }}>
          <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '22px', color: '#444', marginBottom: '8px' }}>No Data</div>
          <div style={{ fontSize: '12px', color: '#444' }}>Not available yet</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: '#101010', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px', overflow: 'hidden' }}>
      <div style={{ padding: '12px 18px', borderBottom: '1px solid rgba(255,255,255,.055)' }}>
        <div style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '2.5px', textTransform: 'uppercase', color: '#888' }}>{title}</div>
        <div style={{ fontSize: '9px', color: '#444', marginTop: '4px' }}>{formatRelative(updatedAt)}</div>
      </div>
      {rows.map((row, idx) => {
        const pos = idx + 1;
        const tc = getTeamColor(row.constructor_id || row.constructor_name || '');
        const preRank = preRanks[row.driver_id] || 0;
        const delta = showDelta && preRank ? preRank - pos : null;
        const posColor = pos === 1 ? '#E10600' : pos <= 3 ? '#dedede' : '#444';

        return (
          <div key={row.driver_id || idx} style={{
            display: 'grid', gridTemplateColumns: '28px 3px 1fr auto',
            gap: '8px', alignItems: 'center',
            padding: '8px 16px',
            borderBottom: '1px solid rgba(255,255,255,.02)',
            transition: 'background .15s',
          }}>
            <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 800, fontSize: '16px', color: posColor, textAlign: 'center' }}>{pos}</div>
            <div style={{ height: '24px', background: tc, borderRadius: '1px', flexShrink: 0 }} />
            <div>
              <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '15px', color: '#fff' }}>
                {(row.driver_id || row.driver_name || '').toUpperCase()}
              </div>
              <div style={{ fontSize: '9px', color: '#444', marginTop: '1px' }}>{row.constructor_id || row.constructor_name || ''}</div>
            </div>
            {delta !== null && (
              <div style={{
                fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '15px', textAlign: 'right',
                color: delta > 0 ? '#34d058' : delta < 0 ? '#E10600' : '#444',
              }}>
                {delta > 0 ? `↑${delta}` : delta < 0 ? `↓${Math.abs(delta)}` : '—'}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── Main ── */
export function RaceDetail() {
  const { round: roundParam } = useParams();
  const navigate = useNavigate();
  const { data: calendar } = useApi('/api/calendar');
  const { data: status } = useApi('/api/status');
  const { data: results } = useApi('/api/race-results');

  const roundsComplete = status?.rounds_completed ?? 0;
  const resultsRounds = results?.races?.map(r => r.round) ?? [];

  // Determine initial selected round
  const [selectedRound, setSelectedRound] = useState(roundParam ? parseInt(roundParam, 10) : null);

  // Auto-select next round when calendar loads if no param
  useEffect(() => {
    if (!roundParam && calendar?.races?.length) {
      const nextRace = calendar.races.find(r => r.round > roundsComplete);
      if (nextRace) setSelectedRound(nextRace.round);
      else setSelectedRound(calendar.races[calendar.races.length - 1]?.round ?? null);
    }
  }, [roundParam, calendar, roundsComplete]);

  const { data: prequali } = useApi(selectedRound ? `/api/predictions/${selectedRound}/prequali` : null);
  const { data: postquali } = useApi(selectedRound ? `/api/predictions/${selectedRound}/postquali` : null);

  const races = calendar?.races ?? [];
  const selectedRace = races.find(r => r.round === selectedRound);
  const actualResult = results?.races?.find(r => r.round === selectedRound);

  // Build pre-quali rank map for delta calculation
  const preRanks = {};
  prequali?.rows?.forEach((row, idx) => { preRanks[row.driver_id] = idx + 1; });

  // Actual podium rows for the results column
  const actualRows = actualResult
    ? (actualResult.podium || []).map(p => ({ driver_id: (p.driver_name || '').split(' ').pop(), driver_name: p.driver_name, constructor_name: p.constructor_name || '' }))
    : [];

  const fmtDate = (d) => d ? new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '—';

  return (
    <div style={S.wrap}>
      <div style={{ padding: '56px 0 80px' }}>
        {/* Section header */}
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#444', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '14px', height: '1px', background: '#E10600', display: 'inline-block' }} />
              2026 Season
            </div>
            <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: 'clamp(24px, 2.5vw, 36px)', color: '#fff', letterSpacing: '-.5px', lineHeight: 1 }}>Race Calendar</div>
          </div>
          <div style={{ fontSize: '10px', color: '#444', textAlign: 'right', lineHeight: 1.8, fontFamily: "'DM Mono', monospace" }}>Click a circuit to view<br />prediction breakdown</div>
        </div>

        {/* Circuit scroll */}
        <div style={{ marginBottom: '52px' }}>
          <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '2px', scrollbarWidth: 'none' }}>
            {races.map(race => {
              const status = getRaceStatus(race, resultsRounds, roundsComplete);
              return (
                <CircuitCard
                  key={race.round}
                  race={race}
                  selected={race.round === selectedRound}
                  status={status}
                  onClick={() => {
                    setSelectedRound(race.round);
                    navigate(`/race/${race.round}`, { replace: true });
                  }}
                />
              );
            })}
          </div>
        </div>

        {/* Detail panel */}
        {selectedRace && (
          <div>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '36px', gap: '20px' }}>
              <div>
                <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: 'clamp(40px, 4.5vw, 64px)', color: '#fff', lineHeight: .92, letterSpacing: '-2px', marginBottom: '12px' }}>
                  {selectedRace.name.replace(' Grand Prix', '')}<br />Grand Prix
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={S.chip(resultsRounds.includes(selectedRound) ? 'muted' : selectedRound === roundsComplete + 1 ? 'red' : 'muted')}>
                    {resultsRounds.includes(selectedRound) ? 'Complete' : selectedRound === roundsComplete + 1 ? 'Next Race' : 'Upcoming'}
                  </span>
                  <span style={S.chip('muted')}>Round {selectedRound}</span>
                  <span style={S.chip('muted')}>{fmtDate(selectedRace.date)}</span>
                </div>
              </div>
            </div>

            {/* Comparison grid */}
            {(!prequali && !postquali) ? (
              <div style={{ padding: '48px 24px', textAlign: 'center', background: '#101010', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px' }}>
                <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '22px', color: '#444', marginBottom: '8px' }}>No Predictions Yet</div>
                <div style={{ fontSize: '12px', color: '#444' }}>Predictions will appear once the pipeline runs for this round.</div>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: actualRows.length > 0 ? 'repeat(3, 1fr)' : 'repeat(2, 1fr)', gap: '16px' }}>
                <PredCol
                  title="Pre-Qualifying"
                  rows={prequali?.rows ?? []}
                  updatedAt={prequali?.created_at ?? null}
                />
                <PredCol
                  title="Post-Qualifying"
                  rows={postquali?.rows ?? []}
                  updatedAt={postquali?.created_at ?? null}
                  showDelta
                  preRanks={preRanks}
                />
                {actualRows.length > 0 && (
                  <PredCol
                    title="Actual Result"
                    rows={actualRows}
                  />
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
