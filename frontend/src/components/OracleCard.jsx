import { TEAM_COLORS } from '../constants/teamColors';
import { useApi } from '../hooks/useApi';
import { Countdown } from './Countdown';

function Skeleton() {
  return <div className="h-12 bg-[#1a1a1a] rounded animate-pulse"></div>;
}

export function OracleCard({ onRaceSelect = null }) {
  const { data: nextPred, loading: loadingNext } = useApi('/api/predictions/next');
  const { data: metrics, loading: loadingMetrics } = useApi('/api/metrics');
  const { data: calendar, loading: loadingCalendar } = useApi('/api/calendar');
  const { data: status } = useApi('/api/pipeline/status');

  if (loadingNext || loadingMetrics || loadingCalendar) {
    return <Skeleton />;
  }

  const predictions = nextPred?.rows || [];
  const round = nextPred?.round || '?';
  const raceName = nextPred?.race_name || 'Unknown';
  const alpha = metrics?.overall?.prequali?.alpha || 0.5;
  const predicted_p1 = predictions[0];

  // Find race in calendar to get date
  const race = calendar?.races?.find((r) => r.round === round);
  const raceDate = race?.date;

  // Get country flag emoji (simple mapping)
  const flagMap = {
    Australian: '🇦🇺',
    Chinese: '🇨🇳',
    Bahrain: '🇧🇭',
    Japanese: '🇯🇵',
    Saudi: '🇸🇦',
    Miami: '🇺🇸',
    Monaco: '🇲🇨',
    Canadian: '🇨🇦',
    Spanish: '🇪🇸',
    Austrian: '🇦🇹',
    British: '🇬🇧',
    Belgian: '🇧🇪',
    Hungarian: '🇭🇺',
    Dutch: '🇳🇱',
    Italian: '🇮🇹',
    Azerbaijan: '🇦🇿',
    Singapore: '🇸🇬',
    States: '🇺🇸',
    Mexico: '🇲🇽',
    Paulo: '🇧🇷',
    Vegas: '🇺🇸',
    Qatar: '🇶🇦',
    Abu: '🇦🇪',
  };

  const flagEmoji = Object.entries(flagMap).find(([key]) => raceName.includes(key))?.[1] || '🏁';

  const isUpdating = status?.status === 'running';
  const teamColor = predicted_p1 ? TEAM_COLORS[predicted_p1.constructor_id] || '#777777' : '#777777';

  return (
    <div
      className="relative bg-[#111111] border border-[rgba(255,255,255,0.07)] rounded p-8 overflow-hidden cursor-pointer hover:border-[rgba(255,255,255,0.14)] transition"
      onClick={() => onRaceSelect?.(round)}
    >
      {/* Ghost text background */}
      <div className="absolute top-4 right-4 text-6xl font-black font-barlow text-white opacity-5">
        R{round}
      </div>

      {/* Main content */}
      <div className="relative z-10 space-y-6">
        {/* Header with flag and race name */}
        <div className="space-y-2">
          <div className="text-5xl">{flagEmoji}</div>
          <h1 className="text-6xl font-black font-barlow text-white leading-tight">{raceName}</h1>
        </div>

        {/* Countdown */}
        {raceDate && <Countdown targetDate={raceDate} className="py-4" />}

        {/* Predicted P1 */}
        {predicted_p1 && (
          <div className="border-l-4 rounded pl-4 space-y-2" style={{ borderColor: teamColor }}>
            <div className="text-xs text-[#777777] uppercase tracking-wider">Predicted Winner</div>
            <div className="text-4xl font-black font-barlow text-white">{predicted_p1.driver_id.toUpperCase()}</div>
            <div className="text-sm text-[#777777]">{predicted_p1.constructor_id}</div>
          </div>
        )}

        {/* Alpha confidence */}
        <div className="flex items-center gap-3">
          <div className="bg-[#1a1a1a] border border-[rgba(255,255,255,0.07)] rounded px-3 py-1 text-xs">
            <span className="text-[#777777]">Model confidence: </span>
            <span className="text-white font-semibold">{(alpha * 100).toFixed(0)}%</span>
          </div>
          {isUpdating && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-[#E10600] rounded-full animate-pulse"></div>
              <span className="text-xs text-[#E10600]">Model updating…</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
