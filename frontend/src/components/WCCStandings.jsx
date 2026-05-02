import { TEAM_COLORS, TEAM_ABBR } from '../constants/teamColors';
import { useApi } from '../hooks/useApi';

function Skeleton() {
  return <div className="h-14 bg-[#1a1a1a] rounded animate-pulse"></div>;
}

export function WCCStandings() {
  const { data: standings, loading, error } = useApi('/api/standings/constructors');

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} />
        ))}
      </div>
    );
  }

  if (error || !standings?.constructors) {
    return <div className="text-[#E10600] text-sm">Failed to load standings</div>;
  }

  const constructors = standings.constructors || [];
  const maxPoints = constructors[0]?.points || 1;

  return (
    <div className="space-y-3">
      {constructors.map((team, idx) => {
        const teamColor = TEAM_COLORS[team.constructor_name] || '#777777';
        const abbr = TEAM_ABBR[team.constructor_name] || team.constructor_name.slice(0, 3).toUpperCase();
        const fillPercent = (team.points / maxPoints) * 100;
        const hasSprint = (team.sprint_points || 0) > 0;

        return (
          <div key={team.constructor_id} className="space-y-2">
            <div className="flex items-center justify-between px-4 py-3 rounded bg-[#111111] border border-[rgba(255,255,255,0.07)]">
              <div className="flex items-center gap-3 flex-1">
                <div className="text-lg font-black font-barlow text-[#777777]">{team.position}</div>
                <div
                  className="w-10 h-10 rounded flex items-center justify-center text-xs font-black text-white"
                  style={{ backgroundColor: teamColor }}
                >
                  {abbr}
                </div>
                <div>
                  <div className="text-white font-medium">{team.constructor_name}</div>
                  <div className="text-xs text-[#777777]">{team.wins} wins</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xl font-black text-white font-barlow">{team.points}</div>
                <div className="text-xs text-[#777777]">pts</div>
                {hasSprint && (
                  <div className="text-[10px] font-mono mt-0.5" style={{ color: '#F59E0B' }}>
                    {team.sprint_points} sprint
                  </div>
                )}
              </div>
            </div>
            <div className="h-2 bg-[#111111] rounded overflow-hidden border border-[rgba(255,255,255,0.07)]">
              <div
                className="h-full rounded transition-all duration-1000"
                style={{
                  backgroundColor: teamColor,
                  width: `${fillPercent}%`,
                }}
              ></div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
