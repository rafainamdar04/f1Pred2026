import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { useCountdown } from '../hooks/useCountdown';
import { getTeamColor, getTeamAbbr } from '../constants/teamColors';

const S = {
  wrap: { maxWidth: '1180px', margin: '0 auto', padding: '0 48px' },
  label: { fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#444' },
  chip: (variant) => ({
    display: 'inline-flex', alignItems: 'center', gap: '5px',
    fontSize: '9px', fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase',
    padding: '3px 8px', borderRadius: '2px',
    ...(variant === 'red'   ? { background: 'rgba(225,6,0,.1)',     color: '#E10600', border: '1px solid rgba(225,6,0,.2)' } :
       variant === 'muted' ? { background: 'rgba(255,255,255,.04)', color: '#444',    border: '1px solid rgba(255,255,255,.055)' } :
                             { background: 'rgba(52,208,88,.08)',   color: '#34d058', border: '1px solid rgba(52,208,88,.2)' }),
  }),
  panel: {
    background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px', overflow: 'hidden',
  },
  panelHead: {
    padding: '14px 20px', borderBottom: '1px solid rgba(255,255,255,.055)',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  },
};

/* ── Countdown panel ── */
const TZ_OPTIONS = [
  { label: 'UTC +00:00', offset: 0 },
  { label: 'CET +01:00', offset: 1 },
  { label: 'IST +05:30', offset: 5.5 },
  { label: 'JST +09:00', offset: 9 },
  { label: 'AEST +10:00', offset: 10 },
  { label: 'EDT −04:00', offset: -4 },
  { label: 'PDT −07:00', offset: -7 },
];

function CountdownPanel({ raceStartUtc }) {
  const [tzOffset, setTzOffset] = useState(0);
  const t = useCountdown(raceStartUtc);

  const localTime = (() => {
    if (!raceStartUtc) return '—';
    const d = new Date(new Date(raceStartUtc).getTime() + tzOffset * 3600000);
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${d.getUTCDate()} ${months[d.getUTCMonth()]} ${d.getUTCFullYear()} · ${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}`;
  })();

  const selectedTzLabel = TZ_OPTIONS.find(o => o.offset === tzOffset)?.label ?? 'UTC +00:00';

  const pad = (n) => String(Math.max(0, n)).padStart(2, '0');
  const blocks = [
    { val: t ? t.days : '--', unit: 'Days' },
    { val: t ? pad(t.hours) : '--', unit: 'Hrs' },
    { val: t ? pad(t.minutes) : '--', unit: 'Min' },
    { val: t ? pad(t.seconds) : '--', unit: 'Sec' },
  ];

  return (
    <div style={{
      background: '#101010', border: '1px solid rgba(255,255,255,.055)',
      borderTop: '2px solid #E10600', borderRadius: '3px', padding: '28px 24px 24px',
    }}>
      <div style={{ ...S.label, marginBottom: '20px' }}>Race countdown</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', marginBottom: '20px' }}>
        {blocks.map(b => (
          <div key={b.unit} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
            <div style={{
              fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900,
              fontSize: '40px', lineHeight: 1, color: '#fff',
              background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)',
              borderRadius: '2px', width: '100%', textAlign: 'center',
              padding: '8px 4px', letterSpacing: '-1px',
            }}>{b.val}</div>
            <div style={{ fontSize: '7px', letterSpacing: '2px', textTransform: 'uppercase', color: '#444' }}>{b.unit}</div>
          </div>
        ))}
      </div>
      <div style={{ paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,.055)' }}>
        <div style={S.label}>Race start · {selectedTzLabel}</div>
        <div style={{ fontFamily: "'DM Mono', monospace", fontSize: '14px', color: '#dedede', marginTop: '4px' }}>{localTime}</div>
        <select
          value={tzOffset}
          onChange={e => setTzOffset(parseFloat(e.target.value))}
          style={{
            width: '100%', marginTop: '14px', padding: '8px 10px',
            background: '#141414', border: '1px solid rgba(255,255,255,.10)',
            color: '#888', fontFamily: "'DM Mono', monospace", fontSize: '11px',
            borderRadius: '2px', cursor: 'pointer', outline: 'none', appearance: 'none',
          }}
        >
          {TZ_OPTIONS.map(o => (
            <option key={o.label} value={o.offset}>{o.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}

/* ── WDC row ── */
function DriverRow({ driver, rank, maxPts }) {
  const tc = getTeamColor(driver.constructor_name);
  const fillPct = maxPts > 0 ? (driver.points / maxPts) * 70 : 0;
  const posClass = rank === 1 ? '#E10600' : rank <= 3 ? '#dedede' : '#444';
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '34px 3px 1fr 60px',
      gap: '10px', alignItems: 'center',
      padding: '9px 18px 9px 14px',
      borderBottom: '1px solid rgba(255,255,255,.02)',
      position: 'relative', overflow: 'hidden',
      transition: 'background .16s',
    }}>
      {/* background fill */}
      <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${fillPct}%`, background: tc, opacity: .045, transition: 'width 1.2s cubic-bezier(.16,1,.3,1)' }} />
      <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 800, fontSize: '16px', color: posClass, textAlign: 'center', position: 'relative' }}>{rank}</div>
      <div style={{ height: '26px', background: tc, borderRadius: '1px', flexShrink: 0 }} />
      <div style={{ minWidth: 0, position: 'relative' }}>
        <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '15px', color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {driver.driver_name || driver.driver_id?.toUpperCase()}
        </div>
        <div style={{ fontSize: '9px', color: '#444', marginTop: '1px' }}>{driver.constructor_name}</div>
      </div>
      <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 800, fontSize: '18px', color: '#fff', textAlign: 'right', lineHeight: 1, position: 'relative' }}>
        {driver.points}
        <small style={{ display: 'block', fontFamily: "'DM Sans', sans-serif", fontSize: '7px', fontWeight: 400, color: '#444', letterSpacing: '1px', marginTop: '2px' }}>PTS</small>
      </div>
    </div>
  );
}

/* ── WCC row ── */
function ConstructorRow({ team, rank, maxPts }) {
  const tc = getTeamColor(team.constructor_name);
  const abbr = getTeamAbbr(team.constructor_name);
  const fillPct = maxPts > 0 ? (team.points / maxPts) * 45 : 0;
  const barFill = maxPts > 0 ? (team.points / maxPts) * 100 : 0;
  const posClass = rank === 1 ? '#E10600' : rank <= 3 ? '#dedede' : '#444';
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '34px 1fr 60px',
      gap: '10px', alignItems: 'center',
      padding: '11px 18px 11px 14px',
      borderBottom: '1px solid rgba(255,255,255,.02)',
      position: 'relative', overflow: 'hidden',
    }}>
      <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${fillPct}%`, background: tc, opacity: .055, transition: 'width 1.3s cubic-bezier(.16,1,.3,1)' }} />
      <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 800, fontSize: '16px', color: posClass, textAlign: 'center', position: 'relative' }}>{rank}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, position: 'relative' }}>
        <div style={{ width: '30px', height: '30px', borderRadius: '2px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: tc, fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: '9px', color: '#fff', letterSpacing: '.3px' }}>{abbr}</div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '15px', color: '#fff' }}>{team.constructor_name}</div>
          <div style={{ height: '1px', background: 'rgba(255,255,255,.055)', marginTop: '5px', overflow: 'hidden' }}>
            <div style={{ height: '100%', background: tc, width: `${barFill}%`, transition: 'width 1.4s cubic-bezier(.16,1,.3,1)' }} />
          </div>
        </div>
      </div>
      <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 800, fontSize: '18px', color: '#fff', textAlign: 'right', lineHeight: 1, position: 'relative' }}>
        {team.points}
        <small style={{ display: 'block', fontFamily: "'DM Sans', sans-serif", fontSize: '7px', fontWeight: 400, color: '#444', letterSpacing: '1px', marginTop: '2px' }}>PTS</small>
      </div>
    </div>
  );
}

/* ── Section header ── */
function SectionHeader({ eyebrow, title, meta }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '20px' }}>
      <div>
        <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#444', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '14px', height: '1px', background: '#E10600', display: 'inline-block' }} />
          {eyebrow}
        </div>
        <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: 'clamp(24px, 2.5vw, 36px)', color: '#fff', letterSpacing: '-.5px', lineHeight: 1 }}>{title}</div>
      </div>
      {meta && <div style={{ fontSize: '10px', color: '#444', textAlign: 'right', lineHeight: 1.8, fontFamily: "'DM Mono', monospace" }}>{meta}</div>}
    </div>
  );
}

/* ── Main ── */
export function Home() {
  const navigate = useNavigate();
  const { data: nextPred } = useApi('/api/predictions/next/postquali');
  const { data: prePred } = useApi('/api/predictions/next/prequali');
  const { data: calendar } = useApi('/api/calendar');
  const { data: metrics } = useApi('/api/metrics');
  const { data: driverStandings } = useApi('/api/standings/drivers');
  const { data: constructorStandings } = useApi('/api/standings/constructors');
  const { data: status } = useApi('/api/status');

  const predictions = nextPred || prePred;
  const round = predictions?.round;
  const raceName = predictions?.race_name || '';
  const gpName = raceName.replace(' Grand Prix', '');
  const modelPick = predictions?.rows?.[0];
  const alpha = predictions?.alpha ?? 0;
  const createdAt = predictions?.created_at ?? null;

  const race = calendar?.races?.find(r => r.round === round);
  const raceDate = race?.date || null;

  const roundsComplete = status?.rounds_completed ?? 0;
  const hitRate = metrics?.overall?.prequali?.top3_hit ?? null;
  const topDriver = driverStandings?.drivers?.[0];
  const topTeam = constructorStandings?.constructors?.[0];
  const drivers = driverStandings?.drivers || [];
  const constructors = constructorStandings?.constructors || [];
  const maxDrvPts = drivers[0]?.points || 1;
  const maxTeamPts = constructors[0]?.points || 1;

  const formatDate = (d) => {
    if (!d) return '—';
    const dt = new Date(d);
    return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const formatRelative = (value) => {
    if (!value) return 'unknown';
    const then = new Date(value).getTime();
    if (Number.isNaN(then)) return 'unknown';
    const diffMinutes = Math.max(0, Math.floor((Date.now() - then) / 60000));
    if (diffMinutes < 1) return 'just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    const hours = Math.floor(diffMinutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  return (
    <div style={S.wrap}>
      {/* ── Hero ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '64px', padding: '72px 0 64px', alignItems: 'start' }}>
        {/* Left */}
        <div>
          <div style={{ fontSize: '10px', fontWeight: 500, letterSpacing: '4px', color: '#444', textTransform: 'uppercase', marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ width: '24px', height: '1px', background: '#E10600', display: 'inline-block' }} />
            Round {String(round || '?').padStart(2, '0')} &nbsp;·&nbsp; {race?.short || '...'}
          </div>

          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <span style={S.chip('red')}>Next Race</span>
            <span style={S.chip('muted')}>{race?.short || 'TBC'}</span>
          </div>

          <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: 'clamp(56px, 7vw, 96px)', lineHeight: .92, letterSpacing: '-3px', color: '#fff', marginBottom: '20px' }}>
            {gpName || 'Formula 1'}<br />Grand Prix
          </div>

          <div style={{ fontSize: '12px', color: '#888', marginBottom: '32px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ color: '#444' }}>—</span>
            {race?.name || '2026 Season'}
          </div>

          <div style={{ display: 'flex', gap: '32px' }}>
            {[
              { val: formatDate(raceDate), lbl: 'Race Date' },
              { val: modelPick ? modelPick.driver_id.toUpperCase() : '—', lbl: "Model's pick · P1", color: '#27F4D2' },
              { val: `${(alpha * 100).toFixed(0)}%`, lbl: 'Qualifying weight' },
              { val: formatRelative(createdAt), lbl: 'Prediction freshness' },
            ].map(item => (
              <div key={item.lbl} style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '17px', color: item.color || '#dedede' }}>{item.val}</div>
                <div style={{ fontSize: '9px', letterSpacing: '1.5px', textTransform: 'uppercase', color: '#444' }}>{item.lbl}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Countdown */}
        <CountdownPanel raceStartUtc={race?.race_start_utc ?? (raceDate ? `${raceDate}T14:00:00Z` : null)} />
      </div>

      {/* ── Stats row ── */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '1px', background: 'rgba(255,255,255,.055)',
        border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px',
        overflow: 'hidden', marginBottom: '80px',
      }}>
        {[
          { val: roundsComplete, lbl: 'Races complete' },
          { val: topDriver ? `${topDriver.points}` : '—', lbl: topDriver ? `${topDriver.driver_name || topDriver.driver_id} pts` : 'Championship leader', color: '#27F4D2' },
          { val: topTeam ? `${topTeam.points}` : '—', lbl: topTeam ? `${topTeam.constructor_name} WCC` : 'Constructors leader' },
          { val: hitRate !== null ? `${(hitRate * 100).toFixed(0)}%` : '—', lbl: 'Model hit rate', color: '#F59E0B' },
        ].map(s => (
          <div key={s.lbl} style={{ background: '#0c0c0c', padding: '22px 24px' }}>
            <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: '36px', color: s.color || '#fff', lineHeight: 1, letterSpacing: '-1px', marginBottom: '6px' }}>{s.val}</div>
            <div style={{ fontSize: '9px', letterSpacing: '2px', textTransform: 'uppercase', color: '#444' }}>{s.lbl}</div>
          </div>
        ))}
      </div>

      {/* ── Championship Standings ── */}
      <SectionHeader
        eyebrow="FIA Formula One"
        title="Championship Standings"
        meta={`After R${roundsComplete} · ${race?.short || '—'}`}
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1.15fr .85fr', gap: '16px', marginBottom: '80px' }}>
        {/* WDC */}
        <div style={S.panel}>
          <div style={S.panelHead}>
            <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 800, fontSize: '16px', color: '#fff' }}>Drivers</div>
            <span style={S.chip('muted')}>WDC · R{roundsComplete}</span>
          </div>
          {drivers.length === 0 ? (
            <div style={{ padding: '24px', fontSize: '12px', color: '#444' }}>Loading standings…</div>
          ) : (
            drivers.map((d, i) => <DriverRow key={d.driver_id || i} driver={d} rank={i + 1} maxPts={maxDrvPts} />)
          )}
        </div>

        {/* WCC */}
        <div style={S.panel}>
          <div style={S.panelHead}>
            <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 800, fontSize: '16px', color: '#fff' }}>Constructors</div>
            <span style={S.chip('muted')}>WCC · R{roundsComplete}</span>
          </div>
          {constructors.length === 0 ? (
            <div style={{ padding: '24px', fontSize: '12px', color: '#444' }}>Loading standings…</div>
          ) : (
            constructors.map((t, i) => <ConstructorRow key={t.constructor_id || i} team={t} rank={i + 1} maxPts={maxTeamPts} />)
          )}
        </div>
      </div>
    </div>
  );
}
