import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { getTeamColor } from '../constants/teamColors';

const S = {
  wrap: { maxWidth: '1180px', margin: '0 auto', padding: '0 48px' },
};

/* ── Accuracy ring ── */
function AccuracyRing({ pct, color = '#27F4D2' }) {
  const r = 40;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  return (
    <div style={{ position: 'relative', width: '88px', height: '88px', flexShrink: 0 }}>
      <svg width="88" height="88" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="44" cy="44" r={r} fill="none" stroke="#1a1a1a" strokeWidth="8" />
        <circle cx="44" cy="44" r={r} fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: 'stroke-dasharray 1s ease' }}
        />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: '22px', color: '#fff', lineHeight: 1 }}>{pct.toFixed(0)}%</div>
        <div style={{ fontSize: '7px', letterSpacing: '1.5px', color: '#444', textTransform: 'uppercase', marginTop: '2px' }}>hit rate</div>
      </div>
    </div>
  );
}

/* ── Driver list button ── */
function DriverBtn({ driver, selected, onClick }) {
  const tc = getTeamColor(driver.constructor_name);
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: '8px',
        padding: '10px 14px', borderBottom: '1px solid rgba(255,255,255,.02)',
        cursor: 'pointer', transition: 'background .15s',
        position: 'relative',
        background: selected ? 'rgba(255,255,255,.04)' : 'transparent',
      }}
    >
      {selected && <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '2px', background: tc, borderRadius: '0 1px 1px 0' }} />}
      <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 800, fontSize: '13px', color: '#444', minWidth: '20px', textAlign: 'right' }}>
        {driver.position || driver.driver_number || '—'}
      </div>
      <div>
        <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '13px', color: '#fff' }}>
          {(driver.driver_name || driver.driver_id || '').split(' ').slice(-1)[0]}
        </div>
        <div style={{ fontSize: '8px', color: '#444', marginTop: '1px' }}>{driver.constructor_name || driver.constructor_id}</div>
      </div>
    </div>
  );
}

/* ── Profile panel ── */
function ProfilePanel({ driver, driverPredictions }) {
  if (!driver) return (
    <div style={{ background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px', display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px' }}>
      <div style={{ fontSize: '12px', color: '#444' }}>Select a driver</div>
    </div>
  );

  const tc = getTeamColor(driver.constructor_name);
  const driverName = driver.driver_name || driver.driver_id?.toUpperCase() || '—';
  const code = driver.driver_id?.toUpperCase?.() || driverName.slice(0, 3).toUpperCase();

  // Compute top-3 accuracy from predictions (position in list = rank)
  const predRounds = driverPredictions.length;
  const top3Count = driverPredictions.filter(p => p.predicted_rank <= 3).length;
  const top5Count = driverPredictions.filter(p => p.predicted_rank <= 5).length;
  const accuracy = predRounds > 0 ? (top3Count / predRounds) * 100 : 0;

  return (
    <div style={{ background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '28px 28px 24px', borderBottom: '1px solid rgba(255,255,255,.055)', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: tc, opacity: .035, pointerEvents: 'none' }} />
        <span style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: '11px', letterSpacing: '3px', color: '#444', marginBottom: '10px', display: 'block' }}>
          {code}
        </span>
        <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: 'clamp(32px, 3.5vw, 52px)', color: '#fff', lineHeight: .95, letterSpacing: '-1px', marginBottom: '10px' }}>
          {driverName}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '3px', height: '18px', borderRadius: '1px', background: tc }} />
          <div style={{ fontSize: '12px', color: '#888' }}>{driver.constructor_name || driver.constructor_id}</div>
        </div>
      </div>

      {/* Accuracy section */}
      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '32px', alignItems: 'center', padding: '24px 28px', borderBottom: '1px solid rgba(255,255,255,.055)' }}>
        <AccuracyRing pct={accuracy} color={tc} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
          {[
            { val: predRounds, lbl: 'Rounds' },
            { val: top3Count, lbl: 'Top-3 picks' },
            { val: top5Count, lbl: 'Top-5 picks' },
            { val: driver.points ?? '—', lbl: 'Champ pts' },
          ].map(s => (
            <div key={s.lbl} style={{ background: '#101010', border: '1px solid rgba(255,255,255,.055)', borderRadius: '2px', padding: '12px 14px' }}>
              <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: '24px', color: '#fff', lineHeight: 1 }}>{s.val}</div>
              <div style={{ fontSize: '8px', letterSpacing: '1.5px', textTransform: 'uppercase', color: '#444', marginTop: '4px' }}>{s.lbl}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Prediction history table */}
      {driverPredictions.length > 0 ? (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['Round', 'Race', 'Predicted', 'Score', 'Mode'].map(h => (
                  <th key={h} style={{ fontSize: '8px', letterSpacing: '2px', textTransform: 'uppercase', color: '#444', padding: '10px 18px', textAlign: 'left', borderBottom: '1px solid rgba(255,255,255,.055)', background: '#101010', fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {driverPredictions.map((pred, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,.025)', transition: 'background .15s' }}>
                  <td style={{ padding: '10px 18px', fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '16px', color: '#fff' }}>R{pred.round}</td>
                  <td style={{ padding: '10px 18px', fontSize: '12px', color: '#888' }}>{pred.race_name || '—'}</td>
                  <td style={{ padding: '10px 18px', fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '16px', color: pred.predicted_rank <= 3 ? '#34d058' : '#fff' }}>
                    P{pred.predicted_rank}
                  </td>
                  <td style={{ padding: '10px 18px', fontFamily: "'DM Mono', monospace", fontSize: '12px', color: '#888' }}>{pred.final_score?.toFixed(3)}</td>
                  <td style={{ padding: '10px 18px', fontSize: '11px', color: '#444' }}>{pred.mode || pred.alpha?.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ padding: '40px 28px', textAlign: 'center', fontSize: '12px', color: '#444' }}>
          No prediction history for this driver yet.
        </div>
      )}
    </div>
  );
}

/* ── Main ── */
export function Drivers() {
  const [selectedId, setSelectedId] = useState(null);

  const { data: standings } = useApi('/api/standings/drivers');
  const { data: history } = useApi('/api/predictions/history');
  const { data: calendar } = useApi('/api/calendar');

  const drivers = standings?.drivers ?? [];

  // Auto-select first driver
  useEffect(() => {
    if (!selectedId && drivers.length > 0) setSelectedId(drivers[0].driver_id);
  }, [drivers, selectedId]);

  const selectedDriver = drivers.find(d => d.driver_id === selectedId) ?? null;

  // Build per-driver prediction list with predicted rank
  // Group history by round, compute rank within each round
  const driverPredictions = (() => {
    if (!history) return [];
    const byRound = {};
    history.forEach(p => {
      if (!byRound[p.round]) byRound[p.round] = [];
      byRound[p.round].push(p);
    });
    // Sort each round by final_score desc (higher = better), assign rank
    Object.values(byRound).forEach(rows => {
      rows.sort((a, b) => (b.final_score ?? 0) - (a.final_score ?? 0));
      rows.forEach((r, i) => { r.predicted_rank = i + 1; });
    });

    // Filter for selected driver
    return history
      .filter(p => p.driver_id === selectedId)
      .map(p => {
        const roundRows = byRound[p.round] ?? [];
        const me = roundRows.find(r => r.driver_id === p.driver_id);
        return { ...p, predicted_rank: me?.predicted_rank ?? 999 };
      })
      .sort((a, b) => a.round - b.round);
  })();

  return (
    <div style={S.wrap}>
      <div style={{ padding: '56px 0 80px' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#444', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '14px', height: '1px', background: '#E10600', display: 'inline-block' }} />
              2026 Grid
            </div>
            <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: 'clamp(24px, 2.5vw, 36px)', color: '#fff', letterSpacing: '-.5px', lineHeight: 1 }}>Driver Profiles</div>
          </div>
          <div style={{ fontSize: '10px', color: '#444', textAlign: 'right', lineHeight: 1.8, fontFamily: "'DM Mono', monospace" }}>
            Model accuracy per driver<br />{drivers.length} drivers in standings
          </div>
        </div>

        {/* 2-col layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '16px' }}>
          {/* Driver list */}
          <div style={{
            background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px',
            overflow: 'hidden', position: 'sticky', top: 'calc(52px + 20px)',
            maxHeight: 'calc(100vh - 52px - 40px)', overflowY: 'auto',
          }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,.055)', fontSize: '9px', fontWeight: 600, letterSpacing: '2.5px', textTransform: 'uppercase', color: '#444', position: 'sticky', top: 0, background: '#0c0c0c', zIndex: 1 }}>
              {drivers.length} Drivers
            </div>
            {drivers.map(d => (
              <DriverBtn
                key={d.driver_id}
                driver={d}
                selected={d.driver_id === selectedId}
                onClick={() => setSelectedId(d.driver_id)}
              />
            ))}
          </div>

          {/* Profile panel */}
          <ProfilePanel driver={selectedDriver} driverPredictions={driverPredictions} />
        </div>
      </div>
    </div>
  );
}
