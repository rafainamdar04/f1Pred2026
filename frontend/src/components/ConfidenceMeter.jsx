export function ConfidenceMeter({ alpha, round, conditions }) {
  const historicalPercent = (1 - alpha) * 100;
  const qualifyingPercent = alpha * 100;

  let message = 'Balanced blend of history and qualifying data';
  if (alpha > 0.6) {
    message = 'Qualifying pace dominated this prediction';
  } else if (alpha < 0.4) {
    message = 'Historical data dominated — qualifying may have been untypical';
  }

  return (
    <div className="space-y-3">
      <div className="text-sm font-semibold text-white">How the model decided</div>
      <div className="flex h-8 rounded overflow-hidden border border-[rgba(255,255,255,0.07)]">
        <div
          className="bg-[#3671C6] flex items-center justify-center text-xs font-medium text-white transition-all duration-1000"
          style={{ width: `${historicalPercent}%` }}
        >
          {historicalPercent > 15 && <span>Historical Data</span>}
        </div>
        <div
          className="bg-[#E10600] flex items-center justify-center text-xs font-medium text-white transition-all duration-1000"
          style={{ width: `${qualifyingPercent}%` }}
        >
          {qualifyingPercent > 15 && <span>Qualifying Pace</span>}
        </div>
      </div>
      <p className="text-xs text-[#777777] italic">{message}</p>
    </div>
  );
}
