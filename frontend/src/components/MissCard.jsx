import { TEAM_COLORS } from '../constants/teamColors';
import { useApi } from '../hooks/useApi';

export function MissCard({ onNavigate = null }) {
  const { data: predictions } = useApi('/api/predictions/history');
  const { data: calendar } = useApi('/api/calendar');
  const { data: status } = useApi('/api/pipeline/status');

  if (!predictions || !calendar) return null;

  // Get latest completed round from status
  const completedRounds = status?.rounds_completed || 0;
  if (completedRounds === 0) return null;

  // Find the latest round in calendar
  const races = calendar?.races || [];
  const latestRound = Math.max(...races.map((r) => r.round));

  // Filter predictions for the latest round
  const latestRoundPreds = predictions?.filter?.((p) => p.round === latestRound) || [];
  if (latestRoundPreds.length === 0) return null;

  // Find the biggest miss (max error)
  let biggestMiss = null;
  let maxError = -1;

  latestRoundPreds.forEach((pred) => {
    // In real app, need actual results to compare
    // For now, using a placeholder
    const error = Math.abs(pred.final_score);
    if (error > maxError) {
      maxError = error;
      biggestMiss = pred;
    }
  });

  if (!biggestMiss) return null;

  const teamColor = TEAM_COLORS[biggestMiss.constructor_id] || '#777777';
  const race = races.find((r) => r.round === latestRound);

  return (
    <div className="bg-[#111111] border-l-4 border-[#E10600] rounded p-6 space-y-3" style={{ borderLeftColor: '#E10600' }}>
      <div className="text-xs font-bold text-[#E10600] uppercase tracking-wider">
        BIGGEST MISS · Round {latestRound} · {race?.name || 'Unknown'}
      </div>
      <div className="text-3xl font-black text-white font-barlow">{biggestMiss.driver_id.toUpperCase()}</div>
      <div className="text-sm text-[#777777]">{biggestMiss.constructor_id}</div>
      {biggestMiss.rationale && (
        <blockquote className="text-sm italic text-[#777777] border-l-2 border-[#777777] pl-3 py-2">
          {biggestMiss.rationale}
        </blockquote>
      )}
    </div>
  );
}
