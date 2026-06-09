import { useParams, Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { useCountUp } from '../hooks/useCountUp';
import { getTeamColor } from '../constants/teamColors';
import { getDriverImage } from '../constants/drivers';

const S = {
  wrap: { maxWidth: '1180px', margin: '0 auto', padding: '0 48px' },
  page: { padding: '56px 0 80px' },
};

function StatChip({ value, label, highlight }) {
  return (
    <div style={{
      background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)',
      borderRadius: '3px', padding: '14px 18px',
    }}>
      <div style={{
        fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900,
        fontSize: '28px', color: highlight || '#fff', lineHeight: 1,
      }}>{value ?? '—'}</div>
      <div style={{
        fontSize: '8px', letterSpacing: '1.8px', textTransform: 'uppercase',
        color: '#444', marginTop: '5px',
      }}>{label}</div>
    </div>
  );
}

function AnimStatChip({ rawValue, label, highlight, prefix = '' }) {
  const animated = useCountUp(typeof rawValue === 'number' ? rawValue : 0);
  const display = typeof rawValue === 'number' ? `${prefix}${animated}` : (rawValue ?? '—');
  return <StatChip value={display} label={label} highlight={highlight} />;
}

function DeltaBadge({ delta }) {
  if (delta === null || delta === undefined) return <span style={{ color: '#333' }}>—</span>;
  if (delta === 0) return <span style={{ color: '#555', fontFamily: "'DM Mono', monospace", fontSize: '12px' }}>±0</span>;
  const up = delta > 0;
  return (
    <span style={{
      color: up ? '#34d058' : '#E10600',
      fontFamily: "'DM Mono', monospace", fontSize: '12px',
    }}>
      {up ? '+' : ''}{delta}
    </span>
  );
}

function ErrorBadge({ error }) {
  if (error === null || error === undefined) return <span style={{ color: '#333' }}>—</span>;
  const color = error <= 2 ? '#34d058' : error <= 4 ? '#f0b429' : '#E10600';
  return (
    <span style={{ color, fontFamily: "'DM Mono', monospace", fontSize: '12px' }}>
      {error === 0 ? '✓' : `±${error}`}
    </span>
  );
}

function StatusBadge({ status }) {
  const finished = status === 'Finished' || status === 'Lapped';
  const color = finished ? '#444' : '#E10600';
  return (
    <span style={{ fontSize: '10px', color, letterSpacing: '.5px' }}>{status || '—'}</span>
  );
}

function AccuracyStrip({ accuracy, tc }) {
  if (!accuracy) return null;
  const stats = [
    { val: accuracy.prequali_mae != null ? accuracy.prequali_mae.toFixed(1) : '—', lbl: 'Pre-Q MAE' },
    { val: accuracy.postquali_mae != null ? accuracy.postquali_mae.toFixed(1) : '—', lbl: 'Post-Q MAE' },
    {
      val: accuracy.prequali_within2_rate != null
        ? `${(accuracy.prequali_within2_rate * 100).toFixed(0)}%` : '—',
      lbl: 'Pre-Q within ±2',
    },
    {
      val: accuracy.postquali_within2_rate != null
        ? `${(accuracy.postquali_within2_rate * 100).toFixed(0)}%` : '—',
      lbl: 'Post-Q within ±2',
    },
  ];
  return (
    <div style={{
      marginTop: '16px',
      background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)',
      borderRadius: '3px', padding: '20px 24px',
    }}>
      <div style={{
        fontSize: '9px', fontWeight: 600, letterSpacing: '2.5px',
        textTransform: 'uppercase', color: '#444', marginBottom: '16px',
      }}>Model accuracy for this driver</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
        {stats.map(s => (
          <div key={s.lbl}>
            <div style={{
              fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900,
              fontSize: '26px', color: tc, lineHeight: 1,
            }}>{s.val}</div>
            <div style={{ fontSize: '8px', letterSpacing: '1.5px', textTransform: 'uppercase', color: '#444', marginTop: '4px' }}>{s.lbl}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Sparkline({ rounds, tc }) {
  if (!rounds || rounds.length === 0) return null;
  const MAX_H = 56;

  const barHeight = (r) => {
    if (r.finish_position == null) return 4;
    return Math.max(4, ((22 - r.finish_position) / 21) * MAX_H);
  };

  return (
    <div style={{
      marginTop: '16px',
      background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)',
      borderRadius: '3px', padding: '20px 24px',
    }}>
      <div style={{
        fontSize: '9px', fontWeight: 600, letterSpacing: '2.5px',
        textTransform: 'uppercase', color: '#444', marginBottom: '4px',
      }}>Season performance</div>
      <div style={{ fontSize: '10px', color: '#333', marginBottom: '16px' }}>Finish position by round · taller bar = better result</div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: `${MAX_H + 24}px` }}>
        {rounds.map(r => {
          const h = barHeight(r);
          const dnf = r.finish_position == null || r.status === 'DNF' || r.status === 'DNS';
          const isWin = r.finish_position === 1;
          const color = dnf ? 'rgba(225,6,0,.4)' : isWin ? tc : `${tc}66`;
          return (
            <div key={r.round} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', justifyContent: 'flex-end' }}>
              <div style={{
                width: '100%', height: `${h}px`,
                background: color,
                borderRadius: '1px 1px 0 0',
                transition: 'height .6s cubic-bezier(.16,1,.3,1)',
                position: 'relative',
              }}>
                {isWin && (
                  <div style={{
                    position: 'absolute', top: '-14px', left: '50%', transform: 'translateX(-50%)',
                    fontSize: '8px', color: tc,
                  }}>P1</div>
                )}
              </div>
              <div style={{ fontSize: '7px', color: '#333', letterSpacing: '.5px' }}>R{r.round}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function DriverProfile() {
  const { driverId } = useParams();
  const { data: profile, loading, error } = useApi(`/api/drivers/${driverId}`);

  if (loading) {
    return (
      <div style={S.wrap}>
        <div style={{ ...S.page, color: '#444', fontSize: '13px' }}>Loading…</div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div style={S.wrap}>
        <div style={S.page}>
          <Link to="/drivers" style={{ fontSize: '11px', color: '#444', textDecoration: 'none', letterSpacing: '1px' }}>
            ← Drivers
          </Link>
          <div style={{ marginTop: '40px', color: '#444', fontSize: '13px' }}>Driver not found.</div>
        </div>
      </div>
    );
  }

  const tc = getTeamColor(profile.constructor_name);
  const code = profile.driver_id?.toUpperCase().slice(0, 3) ?? '???';
  const imgSrc = getDriverImage(profile.driver_id);

  return (
    <div style={S.wrap}>
      <div style={S.page}>
        {/* Back link */}
        <Link to="/drivers" style={{
          fontSize: '10px', fontWeight: 600, letterSpacing: '2px',
          textTransform: 'uppercase', color: '#444', textDecoration: 'none',
          display: 'inline-flex', alignItems: 'center', gap: '6px',
          marginBottom: '32px',
        }}>
          <span style={{ fontSize: '14px' }}>←</span> Drivers
        </Link>

        {/* Header card */}
        <div style={{
          background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)',
          borderRadius: '3px', overflow: 'hidden', marginBottom: '16px',
          position: 'relative',
        }}>
          <div style={{ position: 'absolute', inset: 0, background: tc, opacity: .03, pointerEvents: 'none' }} />

          {/* Portrait photo strip at top */}
          {imgSrc && (
            <div style={{
              height: '6px', background: tc, width: '100%',
            }} />
          )}

          <div style={{
            padding: '32px 36px',
            display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
            flexWrap: 'wrap', gap: '20px',
          }}>
            <div>
              <div style={{
                fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900,
                fontSize: '11px', letterSpacing: '3px', color: '#333',
                marginBottom: '8px',
              }}>{code}</div>
              <div style={{
                fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900,
                fontSize: 'clamp(36px, 4vw, 60px)', color: '#fff',
                lineHeight: .9, letterSpacing: '-1.5px', marginBottom: '12px',
              }}>{profile.driver_name}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '3px', height: '20px', borderRadius: '1px', background: tc }} />
                <span style={{ fontSize: '13px', color: '#666' }}>{profile.constructor_name}</span>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '24px' }}>
              {/* Driver portrait */}
              {imgSrc && (
                <div style={{
                  width: '100px', height: '120px',
                  borderRadius: '3px', overflow: 'hidden',
                  background: `linear-gradient(135deg, ${tc}22 0%, #070707 100%)`,
                  border: `1px solid ${tc}33`,
                  flexShrink: 0, position: 'relative',
                }}>
                  <img
                    src={imgSrc}
                    alt={profile.driver_name}
                    style={{
                      position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)',
                      height: '140px', width: 'auto',
                      objectFit: 'cover', objectPosition: 'top center',
                    }}
                    onError={e => { e.currentTarget.parentElement.style.display = 'none'; }}
                  />
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                {profile.driver_number && (
                  <div style={{
                    fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900,
                    fontSize: '72px', color: 'rgba(255,255,255,.06)', lineHeight: 1,
                    letterSpacing: '-3px', userSelect: 'none',
                  }}>#{profile.driver_number}</div>
                )}
                {profile.position && (
                  <div style={{
                    background: tc, color: '#000', fontFamily: "'Barlow Condensed', sans-serif",
                    fontWeight: 900, fontSize: '11px', letterSpacing: '2px',
                    padding: '3px 10px', borderRadius: '2px',
                  }}>P{profile.position} CHAMPIONSHIP</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Season stats — animated */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(6, 1fr)',
          gap: '8px', marginBottom: '16px',
        }}>
          <AnimStatChip rawValue={profile.points} label="Points" highlight={tc} />
          <AnimStatChip rawValue={profile.wins} label="Wins" />
          <AnimStatChip rawValue={profile.podiums} label="Podiums" />
          <StatChip value={profile.avg_finish != null ? `P${profile.avg_finish}` : null} label="Avg finish" />
          <StatChip value={profile.best_finish != null ? `P${profile.best_finish}` : null} label="Best finish" />
          <StatChip value={profile.dnf_count} label="DNFs" highlight={profile.dnf_count > 0 ? '#E10600' : undefined} />
        </div>

        {/* Race history table */}
        <div style={{
          background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)',
          borderRadius: '3px', overflow: 'hidden',
        }}>
          <div style={{
            padding: '16px 24px', borderBottom: '1px solid rgba(255,255,255,.055)',
            fontSize: '9px', fontWeight: 600, letterSpacing: '2.5px',
            textTransform: 'uppercase', color: '#444',
          }}>Race-by-race</div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['Rnd', 'Race', 'Grid', 'Finish', 'Δ', 'Pts', 'Status', 'PreQ', 'PostQ', 'PreQ err', 'PostQ err'].map(h => (
                    <th key={h} style={{
                      fontSize: '8px', letterSpacing: '1.5px', textTransform: 'uppercase',
                      color: '#333', padding: '10px 16px', textAlign: 'left',
                      borderBottom: '1px solid rgba(255,255,255,.04)',
                      background: '#0a0a0a', fontWeight: 600, whiteSpace: 'nowrap',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(profile.rounds ?? []).map(r => (
                  <tr key={r.round} style={{ borderBottom: '1px solid rgba(255,255,255,.025)' }}>
                    <td style={{ padding: '11px 16px', fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '15px', color: '#555' }}>
                      R{r.round}
                    </td>
                    <td style={{ padding: '11px 16px', fontSize: '11px', color: '#888', whiteSpace: 'nowrap' }}>
                      {r.race_name.replace(' Grand Prix', ' GP')}
                    </td>
                    <td style={{ padding: '11px 16px', fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '16px', color: '#555' }}>
                      {r.grid_position != null ? `P${r.grid_position}` : '—'}
                    </td>
                    <td style={{ padding: '11px 16px', fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '16px', color: r.finish_position === 1 ? tc : '#fff' }}>
                      {r.finish_position != null ? `P${r.finish_position}` : '—'}
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <DeltaBadge delta={r.position_delta} />
                    </td>
                    <td style={{ padding: '11px 16px', fontFamily: "'DM Mono', monospace", fontSize: '12px', color: r.points > 0 ? '#ccc' : '#444' }}>
                      {r.points > 0 ? `+${r.points}` : '0'}
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <StatusBadge status={r.status} />
                    </td>
                    <td style={{ padding: '11px 16px', fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '15px', color: '#555' }}>
                      {r.prequali_rank != null ? `P${r.prequali_rank}` : '—'}
                    </td>
                    <td style={{ padding: '11px 16px', fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '15px', color: '#555' }}>
                      {r.postquali_rank != null ? `P${r.postquali_rank}` : '—'}
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <ErrorBadge error={r.prequali_error} />
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <ErrorBadge error={r.postquali_error} />
                    </td>
                  </tr>
                ))}
                {(!profile.rounds || profile.rounds.length === 0) && (
                  <tr>
                    <td colSpan={11} style={{ padding: '40px', textAlign: 'center', color: '#333', fontSize: '12px' }}>
                      No race data yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Season sparkline */}
        <Sparkline rounds={profile.rounds} tc={tc} />

        {/* Accuracy strip */}
        <AccuracyStrip accuracy={profile.accuracy} tc={tc} />
      </div>
    </div>
  );
}
