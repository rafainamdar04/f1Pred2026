import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { getTeamColor } from '../constants/teamColors';
import { getDriverImage } from '../constants/drivers';

const S = {
  wrap: { maxWidth: '1180px', margin: '0 auto', padding: '0 48px' },
};

function DriverCard({ driver }) {
  const navigate = useNavigate();
  const tc = getTeamColor(driver.constructor_name);
  const lastName = (driver.driver_name || driver.driver_id || '').split(' ').slice(-1)[0];
  const firstName = (driver.driver_name || '').split(' ').slice(0, -1).join(' ');
  const imgSrc = getDriverImage(driver.driver_id);

  return (
    <div
      onClick={() => navigate(`/drivers/${driver.driver_id}`)}
      style={{
        background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)',
        borderRadius: '3px', overflow: 'hidden', cursor: 'pointer',
        transition: 'border-color .18s, background .18s',
        position: 'relative',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = `${tc}55`;
        e.currentTarget.style.background = '#101010';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = 'rgba(255,255,255,.055)';
        e.currentTarget.style.background = '#0c0c0c';
      }}
    >
      {/* Driver photo area */}
      <div style={{
        height: '90px',
        background: `linear-gradient(135deg, ${tc}18 0%, #0a0a0a 80%)`,
        position: 'relative', overflow: 'hidden',
      }}>
        {imgSrc && (
          <img
            src={imgSrc}
            alt={driver.driver_name}
            style={{
              position: 'absolute', bottom: 0, right: '-4px',
              height: '115px', width: 'auto',
              objectFit: 'cover', objectPosition: 'top center',
              filter: 'drop-shadow(-6px 0 10px rgba(0,0,0,.7))',
            }}
            onError={e => { e.currentTarget.style.display = 'none'; }}
          />
        )}
        {driver.driver_number && (
          <div style={{
            position: 'absolute', bottom: '6px', left: '12px',
            fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900,
            fontSize: '34px', color: 'rgba(255,255,255,.07)', lineHeight: 1,
            letterSpacing: '-1px', userSelect: 'none',
          }}>#{driver.driver_number}</div>
        )}
      </div>

      {/* Team color accent */}
      <div style={{ height: '2px', background: tc, width: '100%' }} />

      <div style={{ padding: '14px 16px' }}>
        {/* Position */}
        <div style={{
          fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900,
          fontSize: '11px', color: tc, letterSpacing: '1px', marginBottom: '6px',
        }}>P{driver.position}</div>

        {/* Name */}
        <div style={{ marginBottom: '8px' }}>
          {firstName && (
            <div style={{ fontSize: '11px', color: '#555', marginBottom: '1px' }}>{firstName}</div>
          )}
          <div style={{
            fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900,
            fontSize: '22px', color: '#fff', lineHeight: 1, letterSpacing: '-.3px',
          }}>{lastName}</div>
        </div>

        {/* Team */}
        <div style={{ fontSize: '10px', color: '#444', marginBottom: '12px' }}>
          {driver.constructor_name}
        </div>

        {/* Stats row */}
        <div style={{ display: 'flex', gap: '12px', borderTop: '1px solid rgba(255,255,255,.04)', paddingTop: '10px' }}>
          {[
            { val: driver.points ?? '—', lbl: 'pts' },
            { val: driver.wins ?? 0, lbl: 'wins' },
            { val: driver.podiums ?? 0, lbl: 'pods' },
          ].map(s => (
            <div key={s.lbl}>
              <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: '18px', color: '#fff', lineHeight: 1 }}>
                {s.val}
              </div>
              <div style={{ fontSize: '7px', letterSpacing: '1.5px', textTransform: 'uppercase', color: '#444', marginTop: '3px' }}>{s.lbl}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function Drivers() {
  const { data: standings } = useApi('/api/standings/drivers');
  const drivers = standings?.drivers ?? [];

  return (
    <div style={S.wrap}>
      <div style={{ padding: '56px 0 80px' }}>
        <div style={{ marginBottom: '28px' }}>
          <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#444', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '14px', height: '1px', background: '#E10600', display: 'inline-block' }} />
            2026 Season
          </div>
          <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: 'clamp(24px, 2.5vw, 36px)', color: '#fff', letterSpacing: '-.5px', lineHeight: 1 }}>
            Driver Profiles
          </div>
          <div style={{ marginTop: '8px', fontSize: '11px', color: '#444' }}>
            {drivers.length} drivers · click to view race history and prediction accuracy
          </div>
        </div>

        {drivers.length === 0 ? (
          <div style={{ color: '#444', fontSize: '13px', padding: '60px 0', textAlign: 'center' }}>
            Loading drivers…
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: '10px',
          }}>
            {drivers.map(d => <DriverCard key={d.driver_id} driver={d} />)}
          </div>
        )}
      </div>
    </div>
  );
}
