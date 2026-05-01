import { TEAM_COLORS } from '../constants/teamColors';
import { useApi } from '../hooks/useApi';

function Skeleton() {
  return <div className="h-16 bg-[#1a1a1a] rounded animate-pulse"></div>;
}

export function DeltaShift({ round, onNavigate = null }) {
  const { data: prequali, loading: loadingPre } = useApi(`/api/predictions/${round}/prequali`);
  const { data: postquali, loading: loadingPost } = useApi(`/api/predictions/${round}/postquali`);

  if (loadingPre || loadingPost) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} />
        ))}
      </div>
    );
  }

  const prePredictions = prequali?.rows || [];
  const postPredictions = postquali?.rows || [];

  // Calculate deltas
  const preRanks = {};
  prePredictions.forEach((row, idx) => {
    preRanks[row.driver_id] = idx + 1;
  });

  const postRanks = {};
  postPredictions.forEach((row, idx) => {
    postRanks[row.driver_id] = idx + 1;
  });

  // Find biggest movers
  let biggestRiser = null;
  let biggestFaller = null;
  let riserDelta = 0;
  let fallerDelta = 0;
  let noChangeCount = 0;

  Object.keys(postRanks).forEach((driver) => {
    const pre = preRanks[driver] || 999;
    const post = postRanks[driver];
    const delta = pre - post;

    if (delta === 0) noChangeCount++;
    if (delta > riserDelta) {
      riserDelta = delta;
      biggestRiser = driver;
    }
    if (delta < fallerDelta) {
      fallerDelta = delta;
      biggestFaller = driver;
    }
  });

  const hasPostquali = postPredictions.length > 0;

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      {hasPostquali && (
        <div className="grid grid-cols-3 gap-3 px-4 py-3 bg-[#111111] border border-[rgba(255,255,255,0.07)] rounded">
          <div>
            <div className="text-xs text-[#777777]">Biggest Riser</div>
            <div className="text-white font-semibold">
              {biggestRiser ? `${biggestRiser.toUpperCase()} ↑${riserDelta}` : '—'}
            </div>
          </div>
          <div>
            <div className="text-xs text-[#777777]">Biggest Faller</div>
            <div className="text-white font-semibold">
              {biggestFaller ? `${biggestFaller.toUpperCase()} ↓${Math.abs(fallerDelta)}` : '—'}
            </div>
          </div>
          <div>
            <div className="text-xs text-[#777777]">No Change</div>
            <div className="text-white font-semibold">{noChangeCount} drivers</div>
          </div>
        </div>
      )}

      {/* Two-column layout */}
      <div className="grid grid-cols-2 gap-4">
        {/* Pre-Quali */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-[#777777] uppercase tracking-wider px-2">Pre-Qualifying</h3>
          {prePredictions.map((pred, idx) => {
            const teamColor = TEAM_COLORS[pred.constructor_id] || '#777777';
            return (
              <div
                key={pred.driver_id}
                className="flex items-center gap-3 px-3 py-2 bg-[#111111] border border-[rgba(255,255,255,0.07)] rounded transition"
                style={{ borderLeftColor: teamColor, borderLeftWidth: '4px' }}
              >
                <div className="text-lg font-black font-barlow text-[#777777] w-6">{idx + 1}</div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-white">{pred.driver_id.toUpperCase()}</div>
                  <div className="text-xs text-[#777777]">{pred.constructor_id}</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Post-Quali */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-[#777777] uppercase tracking-wider px-2">Post-Qualifying</h3>
          {hasPostquali ? (
            postPredictions.map((pred, idx) => {
              const teamColor = TEAM_COLORS[pred.constructor_id] || '#777777';
              const preRank = preRanks[pred.driver_id] || 999;
              const delta = preRank - (idx + 1);
              let deltaColor = '#777777';
              let deltaSign = '—';
              if (delta > 0) {
                deltaColor = '#27F4D2';
                deltaSign = `↑${delta}`;
              } else if (delta < 0) {
                deltaColor = '#E10600';
                deltaSign = `↓${Math.abs(delta)}`;
              }

              return (
                <div
                  key={pred.driver_id}
                  className="flex items-center gap-3 px-3 py-2 bg-[#111111] border border-[rgba(255,255,255,0.07)] rounded transition"
                  style={{ borderLeftColor: teamColor, borderLeftWidth: '4px' }}
                >
                  <div className="text-lg font-black font-barlow text-[#777777] w-6">{idx + 1}</div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-white">{pred.driver_id.toUpperCase()}</div>
                    <div className="text-xs text-[#777777]">{pred.constructor_id}</div>
                  </div>
                  <div className="text-sm font-semibold" style={{ color: deltaColor }}>
                    {deltaSign}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="flex flex-col items-center justify-center py-8 px-4 bg-[#111111] border border-[rgba(255,255,255,0.07)] rounded text-center">
              <div className="text-2xl mb-2">🔒</div>
              <div className="text-sm text-[#777777]">Qualifying hasn't happened yet</div>
              <div className="text-xs text-[#777777] mt-1">Check back on Saturday</div>
            </div>
          )}
        </div>
      </div>

      {/* Rationale */}
      {hasPostquali && postquali?.rows?.[0]?.rationale && (
        <div className="px-4 py-3 bg-[#111111] border-l-4 border-[#777777] rounded italic text-[#777777] text-sm">
          <div className="text-xs text-[#777777] uppercase tracking-wider mb-2">Model's Read</div>
          {postquali.rows[0].rationale}
        </div>
      )}
    </div>
  );
}
