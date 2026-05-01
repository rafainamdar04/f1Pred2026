import { TEAM_COLORS, TEAM_ABBR } from '../constants/teamColors';
import { useApi } from '../hooks/useApi';

function Skeleton() {
  return <div className="h-12 bg-[#1a1a1a] rounded animate-pulse"></div>;
}

export function WDCStandings() {
  const { data: standings, loading, error } = useApi('/api/standings/drivers');

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} />
        ))}
      </div>
    );
  }

  if (error || !standings?.drivers) {
    return <div className="text-[#E10600] text-sm">Failed to load standings</div>;
  }

  const drivers = standings.drivers || [];
  const maxPoints = drivers[0]?.points || 1;

  return (
    <div className="space-y-2">
      {drivers.map((driver, idx) => {
        const teamColor = TEAM_COLORS[driver.constructor_name] || '#777777';
        const fillPercent = (driver.points / maxPoints) * 100;
        const isLeader = idx === 0;

        return (
          <div key={driver.driver_id} className="relative">
            <div
              className="absolute inset-0 rounded transition-all duration-1000"
              style={{
                backgroundColor: teamColor,
                opacity: 0.05,
                width: `${fillPercent}%`,
              }}
            ></div>
            <div className="relative flex items-center justify-between px-4 py-3 border-l-4 rounded" style={{ borderColor: teamColor }}>
              <div className="flex items-center gap-3 flex-1">
                <div className={`text-lg font-black font-barlow ${isLeader ? 'text-[#E10600]' : 'text-[#777777]'}`}>
                  {driver.position}
                </div>
                <div>
                  <div className="text-white font-medium">{driver.driver_name}</div>
                  <div className="text-xs text-[#777777]">{driver.constructor_name}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xl font-black text-white font-barlow">{driver.points}</div>
                <div className="text-xs text-[#777777]">pts</div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
