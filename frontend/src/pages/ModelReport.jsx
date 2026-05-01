import { useApi } from '../hooks/useApi';

const S = {
  wrap: { maxWidth: '1180px', margin: '0 auto', padding: '0 48px' },
  card: { background: '#0c0c0c', border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px' },
};

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

/* ── Alpha bar explainer ── */
function AlphaPanel({ alpha, rounds }) {
  const histPct = ((1 - alpha) * 100).toFixed(0);
  const qualiPct = (alpha * 100).toFixed(0);
  const driversScored = rounds.length > 0 ? 22 : 0;

  const verdict = alpha > 0.7
    ? `After ${rounds.length} rounds the model has converged on a high-alpha setting. Qualifying pace has been the dominant predictor of race outcomes.`
    : alpha > 0.5
    ? `The model is using a balanced blend with a slight lean towards qualifying pace. This is consistent with circuits where grid position matters but is not the only factor.`
    : `Historical data is dominating — qualifying may have been untypical or the circuits favour pure race pace over grid position.`;

  return (
    <div style={{
      ...S.card, padding: '24px 28px', marginBottom: '20px',
      display: 'grid', gridTemplateColumns: '1fr 280px', gap: '32px', alignItems: 'center',
    }}>
      <div>
        <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#444', marginBottom: '6px' }}>
          Alpha Blend · How the model weighted its inputs
        </div>
        {/* Bar */}
        <div style={{ height: '8px', background: '#070707', borderRadius: '4px', overflow: 'hidden', display: 'flex', margin: '14px 0 10px' }}>
          <div style={{ height: '100%', background: '#3671C6', borderRadius: '4px 0 0 4px', width: `${histPct}%`, transition: 'width 1s ease' }} />
          <div style={{ height: '100%', background: '#E10600', borderRadius: '0 4px 4px 0', width: `${qualiPct}%`, transition: 'width 1s ease' }} />
        </div>
        {/* Legend */}
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          {[
            { color: '#3671C6', label: `Historical (${histPct}%)` },
            { color: '#E10600', label: `Qualifying Pace (${qualiPct}%)` },
          ].map(item => (
            <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '10px', color: '#888' }}>
              <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: item.color }} />
              {item.label}
            </div>
          ))}
        </div>
        <div style={{ fontSize: '12px', lineHeight: 1.7, color: '#888', marginTop: '16px' }}>{verdict}</div>
      </div>
      {/* Num cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        {[
          { val: `${histPct}%`, lbl: 'Historical', color: '#3671C6' },
          { val: `${qualiPct}%`, lbl: 'Qualifying', color: '#E10600' },
          { val: rounds.length, lbl: 'Rounds trained' },
          { val: driversScored, lbl: 'Drivers scored' },
        ].map(c => (
          <div key={c.lbl} style={{ background: '#101010', border: '1px solid rgba(255,255,255,.055)', borderRadius: '2px', padding: '14px 16px' }}>
            <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: '32px', lineHeight: 1, marginBottom: '4px', color: c.color || '#dedede' }}>{c.val}</div>
            <div style={{ fontSize: '8px', letterSpacing: '1.5px', textTransform: 'uppercase', color: '#444' }}>{c.lbl}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Accuracy timeline ── */
function AccuracyTimeline({ rounds }) {
  const getDotClass = (top3) => {
    if (top3 >= 0.66) return { bg: 'rgba(52,208,88,.12)', border: 'rgba(52,208,88,.5)', color: '#34d058' };
    if (top3 >= 0.33) return { bg: 'rgba(245,158,11,.12)', border: 'rgba(245,158,11,.5)', color: '#F59E0B' };
    return { bg: 'rgba(225,6,0,.12)', border: 'rgba(225,6,0,.4)', color: '#E10600' };
  };

  return (
    <div style={{ ...S.card, padding: '24px 28px', marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#444' }}>Per-Round Accuracy</div>
        <div style={{ display: 'flex', gap: '16px' }}>
          {[
            { color: '#34d058', label: 'Hit ≥ 66%' },
            { color: '#F59E0B', label: '33–66%' },
            { color: '#E10600', label: '<33%' },
          ].map(item => (
            <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '9px', color: '#444' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: item.color + '30', border: `1.5px solid ${item.color}` }} />
              {item.label}
            </div>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', position: 'relative', padding: '4px 0' }}>
        {/* connector line */}
        <div style={{ position: 'absolute', left: '14px', right: '14px', top: '50%', height: '1px', background: 'rgba(255,255,255,.10)', zIndex: 0 }} />
        {rounds.map((r, i) => {
          const top3 = r.prequali?.top3_hit ?? 0;
          const dc = getDotClass(top3);
          return (
            <div key={r.round} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', cursor: 'pointer', position: 'relative', zIndex: 1 }}>
              <div style={{
                width: '28px', height: '28px', borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '9px', fontWeight: 700, fontFamily: "'Barlow Condensed', sans-serif",
                background: dc.bg, border: `2px solid ${dc.border}`, color: dc.color,
                transition: 'transform .2s',
                title: `R${r.round}: ${(top3 * 100).toFixed(0)}%`,
              }}>
                {String(r.round).padStart(2, '0')}
              </div>
              <div style={{ fontSize: '8px', letterSpacing: '1.5px', textTransform: 'uppercase', color: '#444' }}>R{r.round}</div>
            </div>
          );
        })}
        {/* Future placeholders */}
        {[...Array(Math.max(0, 8 - rounds.length))].map((_, i) => (
          <div key={`fut-${i}`} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', position: 'relative', zIndex: 1 }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '9px', fontFamily: "'Barlow Condensed', sans-serif", background: '#070707', border: '2px solid rgba(255,255,255,.055)', color: '#444' }}>
              {String(rounds.length + i + 1).padStart(2, '0')}
            </div>
            <div style={{ fontSize: '8px', letterSpacing: '1.5px', textTransform: 'uppercase', color: '#444' }}>R{rounds.length + i + 1}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Pipeline status ── */
function PipelineGrid({ status }) {
  const lastRun = status?.last_pipeline_run ? new Date(status.last_pipeline_run).toLocaleString() : null;
  const isRunning = status?.status === 'running';

  const pipes = [
    { title: 'Pre-Quali', schedule: 'Thu · 12:00 UTC', ok: !!lastRun, text: lastRun || 'Awaiting run', color: lastRun ? '#34d058' : '#F59E0B' },
    { title: 'Post-Quali', schedule: 'Sat · 18:00 UTC', ok: false, text: 'Awaiting qualifying', color: '#F59E0B' },
    { title: 'Retrain', schedule: 'Sun · 20:00 UTC', ok: !!lastRun, text: lastRun || 'Not yet run', color: lastRun ? '#34d058' : '#F59E0B' },
    { title: 'Pipeline', schedule: status?.next_scheduled ? new Date(status.next_scheduled).toLocaleString() : 'Scheduled', ok: !isRunning, text: isRunning ? 'Running…' : (status?.status || 'Idle'), color: isRunning ? '#E10600' : '#34d058' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
      {pipes.map(p => (
        <div key={p.title} style={{ ...S.card, padding: '18px 20px' }}>
          <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, fontSize: '15px', color: '#fff', marginBottom: '4px' }}>{p.title}</div>
          <div style={{ fontFamily: "'DM Mono', monospace", fontSize: '10px', color: '#444', marginBottom: '10px' }}>{p.schedule}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '10px', fontWeight: 500 }}>
            <div style={{ width: '5px', height: '5px', borderRadius: '50%', flexShrink: 0, background: p.color, animation: isRunning && p.title === 'Pipeline' ? 'livepulse 2s ease-in-out infinite' : 'none' }} />
            <span style={{ color: p.color }}>{p.text}</span>
          </div>
        </div>
      ))}
      <style>{`@keyframes livepulse { 0%,100% { box-shadow: 0 0 0 0 rgba(52,208,88,.5); } 50% { box-shadow: 0 0 0 5px rgba(52,208,88,0); } }`}</style>
    </div>
  );
}

/* ── Main ── */
export function ModelReport() {
  const { data: metrics, loading: metricsLoading } = useApi('/api/metrics');
  const { data: status } = useApi('/api/status');

  if (metricsLoading) {
    return (
      <div style={{ ...S.wrap, padding: '56px 48px' }}>
        {[1,2,3].map(i => (
          <div key={i} style={{ height: '80px', background: '#101010', borderRadius: '3px', marginBottom: '16px', animation: 'pulse 2s infinite' }} />
        ))}
      </div>
    );
  }

  const overall = metrics?.overall ?? {};
  const prequali = overall.prequali ?? {};
  const postquali = overall.postquali ?? {};
  const rounds = metrics?.rounds ?? [];
  const alpha = prequali.alpha ?? 0;

  const metricCards = [
    { val: `${((prequali.top3_hit ?? 0) * 100).toFixed(0)}%`, lbl: 'Top-3 Hit Rate', sub: `${rounds.length} rounds scored`, color: '#34d058' },
    { val: (prequali.ndcg ?? 0).toFixed(2), lbl: 'NDCG Score', sub: '1.0 = perfect ranking' },
    { val: (prequali.mae ?? 0).toFixed(1), lbl: 'MAE · Places', sub: 'Avg position error' },
    { val: alpha.toFixed(2), lbl: 'Alpha (α)', sub: 'Qualifying weight', color: '#F59E0B' },
  ];

  return (
    <div style={S.wrap}>
      <div style={{ padding: '56px 0 80px' }}>
        <SectionHeader
          eyebrow="ML System"
          title="Model Dashboard"
          meta={`${rounds.length} rounds scored\nRetrained Sun 20:00 UTC`}
        />

        {/* 4 metric cards */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '1px', background: 'rgba(255,255,255,.055)',
          border: '1px solid rgba(255,255,255,.055)', borderRadius: '3px',
          overflow: 'hidden', marginBottom: '20px',
        }}>
          {metricCards.map(m => (
            <div key={m.lbl} style={{ background: '#0c0c0c', padding: '28px 24px' }}>
              <div style={{ fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 900, fontSize: '52px', color: m.color || '#fff', lineHeight: 1, letterSpacing: '-2px', marginBottom: '10px' }}>{m.val}</div>
              <div style={{ fontSize: '9px', letterSpacing: '2.5px', textTransform: 'uppercase', color: '#444' }}>{m.lbl}</div>
              <div style={{ fontSize: '11px', color: '#444', marginTop: '4px' }}>{m.sub}</div>
            </div>
          ))}
        </div>

        {/* Alpha split */}
        <AlphaPanel alpha={alpha} rounds={rounds} />

        {/* Accuracy timeline */}
        <AccuracyTimeline rounds={rounds} />

        {/* Pipeline status */}
        <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#444', marginBottom: '16px' }}>
          Pipeline Status
        </div>
        <PipelineGrid status={status} />
      </div>
    </div>
  );
}
