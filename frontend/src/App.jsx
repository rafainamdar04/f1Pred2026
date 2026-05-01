import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Home } from './pages/Home';
import { RaceDetail } from './pages/RaceDetail';
import { ModelReport } from './pages/ModelReport';
import { Drivers } from './pages/Drivers';
import { Archive } from './pages/Archive';

const NAV_LINKS = [
  { to: '/', label: 'Dashboard', exact: true },
  { to: '/race', label: 'Races', exact: false },
  { to: '/model', label: 'Model', exact: false },
  { to: '/drivers', label: 'Drivers', exact: false },
];

function NavBar() {
  const { pathname } = useLocation();

  const isActive = ({ to, exact }) =>
    exact ? pathname === to : pathname === to || pathname.startsWith(to + '/');

  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, height: '52px', zIndex: 400,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 48px',
      background: 'rgba(7,7,7,.95)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid rgba(255,255,255,.055)',
    }}>
      {/* Logo */}
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '12px', textDecoration: 'none' }}>
        <div style={{
          fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: '16px',
          background: '#E10600', color: '#fff',
          padding: '3px 10px 2px',
          clipPath: 'polygon(0 0, 88% 0, 100% 50%, 88% 100%, 0 100%)',
          letterSpacing: '.5px', lineHeight: 1,
        }}>F1</div>
        <span style={{
          fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 600, fontSize: '13px',
          letterSpacing: '4px', color: '#444', textTransform: 'uppercase',
        }}>Predict</span>
      </Link>

      {/* Links */}
      <div style={{ display: 'flex', gap: '2px' }}>
        {NAV_LINKS.map(link => {
          const active = isActive(link);
          return (
            <Link key={link.to} to={link.to} style={{
              fontSize: '12px', fontWeight: 500, letterSpacing: '.3px',
              color: active ? '#dedede' : '#444',
              padding: '6px 14px', borderRadius: '3px',
              textDecoration: 'none',
              background: active ? 'rgba(255,255,255,.05)' : 'transparent',
              transition: 'color .18s, background .18s',
            }}>
              {link.label}
            </Link>
          );
        })}
      </div>

      {/* Live dot */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '7px', fontSize: '11px', color: '#444', fontFamily: "'DM Mono', monospace" }}>
        <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#34d058', flexShrink: 0, animation: 'livepulse 2.2s ease-in-out infinite' }} />
        <span>Pre-quali live</span>
      </div>

      <style>{`
        @keyframes livepulse {
          0%,100% { box-shadow: 0 0 0 0 rgba(52,208,88,.5); }
          50%      { box-shadow: 0 0 0 5px rgba(52,208,88,0); }
        }
      `}</style>
    </nav>
  );
}

export default function App() {
  return (
    <Router>
      <NavBar />
      <main style={{ paddingTop: '52px' }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/race" element={<RaceDetail />} />
          <Route path="/race/:round" element={<RaceDetail />} />
          <Route path="/drivers" element={<Drivers />} />
          <Route path="/model" element={<ModelReport />} />
          <Route path="/archive" element={<Archive />} />
        </Routes>
      </main>
    </Router>
  );
}
