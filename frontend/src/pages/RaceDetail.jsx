import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { getTeamColor } from '../constants/teamColors';
import { getCircuitSvg } from '../constants/circuits';
import { computeRacePhase } from '../utils/phase';

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

/* ── Race-week phase → header chip ── */
const PHASE_CHIP = {
  completed: { v: 'muted', label: 'Complete' },
  postquali: { v: 'grn',   label: 'Post-Quali Out' },
  prequali:  { v: 'red',   label: 'Pre-Quali Out' },
  upcoming:  { v: 'muted', label: 'Upcoming' },
};

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
      <div style={{ marginTop: '2px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
        {isDone      && <span style={S.chip('muted')}>Done</span>}
        {isNext      && <span style={S.chip('red')}>Next</span>}
        {isCancelled && <span style={{ ...S.chip('muted'), opacity: .5 }}>Cancelled</span>}
        {race.is_sprint && <span style={S.chip('amb')}>Sprint</span>}
      </div>
    </div>
  );
}

/* ── Status badge for DNF / DNS / DSQ / Lapped ── */
const STATUS_STYLE = {
  DNF:    { bg: 'rgba(225,6,0,.15)',     color: '#E10600', border: '1px solid rgba(225,6,0,.3)'     },
  DNS:    { bg: 'rgba(255,255,255,.06)', color: '#555',    border: '1px solid rgba(255,255,255,.1)' },
  DSQ:    { bg: 'rgba(245,158,11,.12)', color: '#F59E0B', border: '1px solid rgba(245,158,11,.3)'  },
  Lapped: { bg: 'rgba(255,255,255,.04)', color: '#555',    border: '1px solid rgba(255,255,255,.07)'},
};

function StatusBadge({ status }) {
  const s = STATUS_STYLE[status];
  if (!s) return null;
  return (
    <div style={{
      fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '11px',
      letterSpacing: '1px', padding: '2px 6px', borderRadius: '2px',
      background: s.bg, color: s.color, border: s.border, textAlign: 'center', lineHeight: 1.4,
    }}>
      {status}
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

  const maxScore = rows[0]?.final_score ?? 1;

  return (
    <div style={{ background: '#101010', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px', overflow: 'hidden' }}>
      <div style={{ padding: '12px 18px', borderBottom: '1px solid rgba(255,255,255,.055)' }}>
        <div style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '2.5px', textTransform: 'uppercase', color: '#888' }}>{title}</div>
        <div style={{ fontSize: '9px', color: '#444', marginTop: '4px' }}>{formatRelative(updatedAt)}</div>
      </div>
      {rows.map((row, idx) => {
        const pos = row.finish_position ?? (idx + 1);
        const status = row.status || 'Finished';
        const isOut = status === 'DNF' || status === 'DNS' || status === 'DSQ';
        const isP1 = pos === 1 && !isOut;
        const tc = getTeamColor(row.constructor_id || row.constructor_name || '');
        const preRank = preRanks[row.driver_id] || 0;
        const delta = showDelta && preRank ? preRank - pos : null;
        const posColor = isOut ? '#333' : isP1 ? '#fff' : pos <= 3 ? '#dedede' : pos <= 10 ? '#666' : '#333';
        const rowOpacity = isOut ? 0.45 : status === 'Lapped' ? 0.7 : 1;
        const scorePct = maxScore > 0 && row.final_score != null
          ? Math.min(100, (row.final_score / maxScore) * 60)
          : (isOut ? 0 : Math.max(0, 60 - (pos - 1) * 3));

        return (
          <div key={row.driver_id || idx} style={{
            display: 'grid', gridTemplateColumns: '36px 3px 1fr auto',
            gap: '8px', alignItems: 'center',
            padding: isP1 ? '9px 16px' : '6px 16px',
            borderBottom: '1px solid rgba(255,255,255,.02)',
            opacity: rowOpacity,
            position: 'relative', overflow: 'hidden',
            background: isP1 ? 'rgba(255,255,255,.018)' : 'transparent',
          }}>
            {/* Score bar — proportional to final_score, sits behind everything */}
            <div style={{
              position: 'absolute', left: 0, top: 0, bottom: 0,
              width: `${scorePct}%`, background: tc, opacity: .055,
              pointerEvents: 'none',
            }} />

            {/* Position or status badge */}
            {isOut ? (
              <StatusBadge status={status} />
            ) : status === 'Lapped' ? (
              <div style={{ textAlign: 'center', position: 'relative' }}>
                <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 800, fontSize: '14px', color: posColor }}>{pos}</div>
                <div style={{ fontSize: '7px', color: '#444', letterSpacing: '1px' }}>LAP</div>
              </div>
            ) : (
              <div style={{
                fontFamily: "'Barlow Condensed', sans-serif",
                fontWeight: isP1 ? 900 : 800,
                fontSize: isP1 ? '20px' : '16px',
                color: posColor, textAlign: 'center', position: 'relative',
              }}>{pos}</div>
            )}

            <div style={{ height: isP1 ? '30px' : '24px', background: tc, borderRadius: '1px', flexShrink: 0, opacity: isOut ? 0.4 : 1, position: 'relative' }} />

            <div style={{ position: 'relative' }}>
              <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: isP1 ? 800 : 700, fontSize: isP1 ? '15px' : '14px', color: isOut ? '#555' : '#fff' }}>
                {(row.driver_id || row.driver_name || '').replace(/_/g, ' ').toUpperCase()}
              </div>
              <div style={{ fontSize: '9px', color: '#333', marginTop: '1px' }}>{row.constructor_id || row.constructor_name || ''}</div>
            </div>

            {/* Delta arrow */}
            {delta !== null ? (
              <div style={{
                fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '14px', textAlign: 'right', position: 'relative',
                color: delta > 0 ? '#34d058' : delta < 0 ? '#E10600' : '#444',
              }}>
                {delta > 0 ? `↑${delta}` : delta < 0 ? `↓${Math.abs(delta)}` : '—'}
              </div>
            ) : (
              row.points > 0 ? (
                <div style={{ fontSize: '10px', color: '#444', textAlign: 'right', fontFamily: "'DM Mono', monospace", position: 'relative' }}>
                  +{row.points}
                </div>
              ) : null
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

  const races = calendar?.races ?? [];
  const selectedRace = races.find(r => r.round === selectedRound);
  // Recompute phase from the appointed timestamps so the lifecycle stays live
  // even when the calendar is a static snapshot (see utils/phase.js).
  const { phase, prequali_available: prequaliReady, postquali_available: postqualiReady, result_available: resultReady }
    = computeRacePhase(selectedRace);

  // Only fetch each prediction once it has reached its appointed publication time.
  const { data: prequali } = useApi(selectedRound && prequaliReady ? `/api/predictions/${selectedRound}/prequali` : null);
  const { data: postquali } = useApi(selectedRound && postqualiReady ? `/api/predictions/${selectedRound}/postquali` : null);
  const { data: accuracy } = useApi(selectedRound && resultsRounds.includes(selectedRound) ? `/api/predictions/${selectedRound}/accuracy` : null);

  const actualResult = results?.races?.find(r => r.round === selectedRound);

  // Rank maps for delta arrows
  const preRanks = {};
  prequali?.rows?.forEach((row, idx) => { preRanks[row.driver_id] = idx + 1; });

  const postqualiRanks = {};
  postquali?.rows?.forEach((row, idx) => { postqualiRanks[row.driver_id] = idx + 1; });

  // All 22 drivers with status for the actual result column
  const actualRows = actualResult
    ? (actualResult.podium || []).map(p => ({
        driver_id: p.driver_id || '',
        driver_name: p.driver_name || '',
        constructor_name: p.constructor_name || '',
        constructor_id: p.constructor_id || '',
        finish_position: p.finish_position ?? null,
        points: p.points ?? 0,
        status: p.status || 'Finished',
      }))
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
                  <span style={S.chip(PHASE_CHIP[phase]?.v ?? 'muted')}>
                    {PHASE_CHIP[phase]?.label ?? 'Upcoming'}
                  </span>
                  <span style={S.chip('muted')}>Round {selectedRound}</span>
                  <span style={S.chip('muted')}>{fmtDate(selectedRace.date)}</span>
                  {(selectedRace.is_sprint || actualResult?.is_sprint) && (
                    <span style={S.chip('amb')}>Sprint Weekend</span>
                  )}
                </div>
              </div>
            </div>

            {/* Accuracy banner — only shown for completed rounds */}
            {accuracy && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap',
                background: '#101010', border: '1px solid rgba(255,255,255,.055)',
                borderRadius: '3px', padding: '14px 20px', marginBottom: '24px',
              }}>
                <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '2.5px', textTransform: 'uppercase', color: '#444', marginRight: '4px' }}>Model accuracy</div>
                <div style={{
                  ...S.chip(accuracy.p1_correct ? 'grn' : accuracy.hits >= 2 ? 'amb' : 'red'),
                  fontSize: '10px', padding: '4px 10px',
                }}>
                  {accuracy.hits}/3 top-3 hits{accuracy.p1_correct ? ' · P1 correct' : ''}
                </div>
                <div style={{ display: 'flex', gap: '10px', marginLeft: 'auto' }}>
                  {['Predicted', 'Actual'].map((label, li) => {
                    const ids = li === 0 ? accuracy.predicted_top3 : accuracy.actual_top3;
                    return (
                      <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '9px', color: '#444', letterSpacing: '1px', textTransform: 'uppercase' }}>{label}:</span>
                        {ids.map((id, i) => (
                          <span key={id} style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '13px', color: i === 0 ? '#fff' : '#888' }}>
                            {id.toUpperCase()}{i < ids.length - 1 ? '' : ''}
                          </span>
                        ))}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Sprint result section */}
            {actualResult?.sprint_podium?.length > 0 && (
              <div style={{ marginBottom: '24px' }}>
                <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#F59E0B', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ width: '14px', height: '1px', background: '#F59E0B', display: 'inline-block' }} />
                  Sprint Race Result
                </div>
                <div style={{ background: '#101010', border: '1px solid rgba(245,158,11,.2)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ padding: '10px 18px', borderBottom: '1px solid rgba(245,158,11,.15)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '2.5px', textTransform: 'uppercase', color: '#F59E0B' }}>Top 8 — Sprint</div>
                    <div style={{ fontSize: '9px', color: '#444' }}>Points awarded: 8-7-6-5-4-3-2-1</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}>
                    {actualResult.sprint_podium.map((p, idx) => {
                      const tc = getTeamColor(p.constructor_name || '');
                      const posColor = idx === 0 ? '#F59E0B' : idx < 3 ? '#dedede' : '#666';
                      return (
                        <div key={p.driver_id || idx} style={{
                          display: 'grid', gridTemplateColumns: '28px 3px 1fr auto',
                          gap: '8px', alignItems: 'center',
                          padding: '8px 16px',
                          borderBottom: '1px solid rgba(255,255,255,.02)',
                        }}>
                          <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 800, fontSize: '16px', color: posColor, textAlign: 'center' }}>{idx + 1}</div>
                          <div style={{ height: '24px', background: tc, borderRadius: '1px', flexShrink: 0 }} />
                          <div>
                            <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '14px', color: '#fff' }}>
                              {(p.driver_name || p.driver_id || '').split(' ').pop().toUpperCase()}
                            </div>
                            <div style={{ fontSize: '9px', color: '#444' }}>{p.constructor_name || ''}</div>
                          </div>
                          <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '15px', color: '#F59E0B', textAlign: 'right' }}>
                            +{p.points}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Comparison grid — gated by race-week phase */}
            {(() => {
              const showActual = resultReady && actualRows.length > 0;
              const fmtOpen = (d) => d
                ? new Date(d).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) + ' UTC'
                : 'soon';

              if (phase === 'upcoming') {
                return (
                  <div style={{ padding: '48px 24px', textAlign: 'center', background: '#101010', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px' }}>
                    <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '22px', color: '#666', marginBottom: '8px' }}>Upcoming</div>
                    <div style={{ fontSize: '12px', color: '#444' }}>Pre-qualifying prediction opens {fmtOpen(selectedRace?.prequali_at_utc)}</div>
                  </div>
                );
              }

              if (!prequali && !postquali && !showActual) {
                return (
                  <div style={{ padding: '48px 24px', textAlign: 'center', background: '#101010', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px' }}>
                    <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '22px', color: '#444', marginBottom: '8px' }}>Prediction Pending</div>
                    <div style={{ fontSize: '12px', color: '#444' }}>The {phase === 'prequali' ? 'pre-qualifying' : 'post-qualifying'} run hasn’t completed yet.</div>
                  </div>
                );
              }

              const n = [prequali, postquali, showActual ? true : null].filter(Boolean).length;
              return (
                <div style={{ display: 'grid', gridTemplateColumns: n === 3 ? 'repeat(3, 1fr)' : n === 2 ? 'repeat(2, 1fr)' : '1fr', gap: '16px' }}>
                  {prequali && (
                    <PredCol
                      title="Pre-Qualifying"
                      rows={prequali.rows ?? []}
                      updatedAt={prequali.created_at ?? null}
                    />
                  )}
                  {postquali && (
                    <PredCol
                      title="Post-Qualifying"
                      rows={postquali.rows ?? []}
                      updatedAt={postquali.created_at ?? null}
                      showDelta
                      preRanks={preRanks}
                    />
                  )}
                  {showActual && (
                    <PredCol
                      title="Actual Result"
                      rows={actualRows}
                      showDelta={Object.keys(postqualiRanks).length > 0}
                      preRanks={postqualiRanks}
                    />
                  )}
                </div>
              );
            })()}
          </div>
        )}
      </div>
    </div>
  );
}
