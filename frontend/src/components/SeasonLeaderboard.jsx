import { TEAM_COLORS, TEAM_ABBR } from '../constants/teamColors';
import { useApi } from '../hooks/useApi';

export function SeasonLeaderboard({ fullPage = false }) {
  const { data: predictions } = useApi('/api/predictions/history');
  const { data: results } = useApi('/api/race-results');

  if (!predictions || predictions.length === 0) {
    return <div className="text-[#777777] text-sm">No prediction history yet</div>;
  }

  // Calculate stats per driver
  const driverStats = {};

  predictions.forEach((pred) => {
    if (!driverStats[pred.driver_id]) {
      driverStats[pred.driver_id] = {
        driver_id: pred.driver_id,
        constructor_id: pred.constructor_id,
        rounds: 0,
        totalError: 0,
        errors: [],
      };
    }
    driverStats[pred.driver_id].rounds += 1;
    driverStats[pred.driver_id].totalError += Math.abs(pred.final_score);
    driverStats[pred.driver_id].errors.push(Math.abs(pred.final_score));
  });

  // Calculate averages and predictability scores
  const leaderboard = Object.values(driverStats)
    .map((driver) => ({
      ...driver,
      avgError: driver.totalError / driver.rounds,
      predictabilityScore: Math.max(0, 100 - driver.avgError * 10),
    }))
    .sort((a, b) => b.predictabilityScore - a.predictabilityScore);

  const topDriver = leaderboard[0];
  const bottomDriver = leaderboard[leaderboard.length - 1];

  const displayLeaderboard = fullPage ? leaderboard : leaderboard.slice(0, 10);

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[rgba(255,255,255,0.07)]">
              <th className="text-left py-3 px-3 text-xs font-bold text-[#777777] uppercase tracking-wider">Rank</th>
              <th className="text-left py-3 px-3 text-xs font-bold text-[#777777] uppercase tracking-wider">Driver</th>
              <th className="text-left py-3 px-3 text-xs font-bold text-[#777777] uppercase tracking-wider">Rounds</th>
              <th className="text-left py-3 px-3 text-xs font-bold text-[#777777] uppercase tracking-wider">Avg Error</th>
              <th className="text-left py-3 px-3 text-xs font-bold text-[#777777] uppercase tracking-wider">How well the model reads them</th>
            </tr>
          </thead>
          <tbody>
            {displayLeaderboard.map((driver, idx) => {
              const teamColor = TEAM_COLORS[driver.constructor_id] || '#777777';
              const isBest = driver.driver_id === topDriver.driver_id;
              const isWorst = driver.driver_id === bottomDriver.driver_id;

              return (
                <tr key={driver.driver_id} className="border-b border-[rgba(255,255,255,0.07)] hover:bg-[#1a1a1a] transition">
                  <td className="py-3 px-3">
                    <div className="text-lg font-black font-barlow text-[#777777]">{idx + 1}</div>
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-8 rounded"
                        style={{
                          backgroundColor: teamColor,
                        }}
                      ></div>
                      <div>
                        <div className="text-white font-medium">{driver.driver_id.toUpperCase()}</div>
                        <div className="text-xs text-[#777777]">{driver.constructor_id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-white">{driver.rounds}</td>
                  <td className="py-3 px-3 text-white">{driver.avgError.toFixed(1)} pos</td>
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 max-w-xs">
                        <div className="h-2 bg-[#1a1a1a] rounded overflow-hidden">
                          <div
                            className="h-full rounded transition-all duration-500"
                            style={{
                              backgroundColor: teamColor,
                              width: `${driver.predictabilityScore}%`,
                            }}
                          ></div>
                        </div>
                      </div>
                      <div className="text-white font-semibold min-w-[3rem] text-right">{driver.predictabilityScore.toFixed(0)}%</div>
                      {isBest && <span className="text-xs bg-[#27F4D2] text-black px-2 py-1 rounded font-semibold">Model's Favourite</span>}
                      {isWorst && <span className="text-xs bg-[#E10600] text-white px-2 py-1 rounded font-semibold">Chaos Agent</span>}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
