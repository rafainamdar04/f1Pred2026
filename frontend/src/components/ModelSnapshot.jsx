import { useApi } from '../hooks/useApi';

function Skeleton() {
  return <div className="h-8 bg-[#1a1a1a] rounded animate-pulse"></div>;
}

export function ModelSnapshot({ clickable = false, onClick = null }) {
  const { data: metrics, loading, error } = useApi('/api/metrics');

  if (loading) {
    return (
      <div className="grid grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-[#111111] border border-[rgba(255,255,255,0.07)] rounded p-6">
            <Skeleton />
            <Skeleton />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return <div className="text-[#E10600] text-sm">Failed to load metrics</div>;
  }

  const overall = metrics?.overall || {};
  const prequali = overall.prequali || {};

  const statBoxes = [
    { label: 'Top-3 Hit Rate', value: `${((prequali.top3_hit || 0) * 100).toFixed(1)}%` },
    { label: 'NDCG Score', value: (prequali.ndcg || 0).toFixed(2) },
    { label: 'Avg Position Error', value: `${(prequali.mae || 0).toFixed(1)} places` },
  ];

  const containerClass = clickable ? 'cursor-pointer hover:bg-[#1a1a1a] transition' : '';

  return (
    <div
      className={`grid grid-cols-3 gap-4 ${containerClass}`}
      onClick={onClick}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
    >
      {statBoxes.map((box) => (
        <div
          key={box.label}
          className="bg-[#111111] border border-[rgba(255,255,255,0.07)] rounded p-6 space-y-2"
        >
          <div className="text-3xl font-black text-white font-barlow">{box.value}</div>
          <div className="text-xs text-[#777777] uppercase tracking-wider">{box.label}</div>
        </div>
      ))}
    </div>
  );
}
