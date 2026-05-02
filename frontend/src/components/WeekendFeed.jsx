import { useApi } from '../hooks/useApi';

export function WeekendFeed({ round, onNavigate = null }) {
  const { data: status } = useApi('/api/pipeline/status');
  const { data: calendar } = useApi('/api/calendar');

  if (!status || !calendar) {
    return <div className="text-[#777777] text-sm">Loading weekend schedule…</div>;
  }

  const race = calendar.races?.find((r) => r.round === round);
  const isSprint = race?.is_sprint === true;

  const baseSteps = [
    { day: 'Thursday', label: 'Pre-Quali Predictions', icon: '📊', clickable: true },
    ...(isSprint ? [{ day: 'Saturday', label: 'Sprint Race', icon: '⚡', clickable: false, sprint: true }] : []),
    { day: 'Saturday', label: 'Qualifying', icon: '🏁', clickable: false },
    { day: 'Saturday', label: 'Post-Quali Update', icon: '📈', clickable: true },
    { day: 'Sunday', label: 'Race + Results', icon: '🏆', clickable: false },
  ];

  const isCompleted = (idx) => idx === 0;
  const isInProgress = (idx) => idx === (isSprint ? 2 : 1);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="text-xs font-bold text-[#777777] uppercase tracking-wider">Weekend Timeline</div>
        {isSprint && (
          <span
            className="text-[9px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider"
            style={{ background: 'rgba(245,158,11,.12)', color: '#F59E0B', border: '1px solid rgba(245,158,11,.35)' }}
          >
            Sprint
          </span>
        )}
      </div>
      <div className="space-y-2">
        {baseSteps.map((step, idx) => {
          const done = isCompleted(idx);
          const inProgress = isInProgress(idx);
          const borderColor = step.sprint ? 'border-[rgba(245,158,11,0.25)]' : 'border-[rgba(255,255,255,0.07)]';
          const hoverBorder = step.clickable ? 'hover:border-[rgba(255,255,255,0.14)]' : '';

          return (
            <div
              key={idx}
              className={`flex items-center gap-3 px-4 py-3 bg-[#111111] border ${borderColor} rounded transition ${
                step.clickable ? `cursor-pointer ${hoverBorder}` : ''
              }`}
              onClick={() => {
                if (step.clickable && onNavigate) onNavigate(round);
              }}
              role={step.clickable ? 'button' : undefined}
            >
              {/* Circle indicator */}
              <div className="relative w-6 h-6 flex-shrink-0">
                {inProgress ? (
                  <div className="w-full h-full rounded-full border-2 border-[#E10600] border-t-transparent animate-spin"></div>
                ) : (
                  <div
                    className={`w-full h-full rounded-full flex items-center justify-center ${
                      done ? 'bg-[#27F4D2]' : step.sprint ? '' : 'border-2 border-[#777777]'
                    }`}
                    style={step.sprint && !done ? { border: '2px solid #F59E0B' } : undefined}
                  >
                    {done && <div className="text-white text-sm">✓</div>}
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="flex-1">
                <div className="text-xs" style={{ color: step.sprint ? '#F59E0B' : '#777777' }}>{step.day}</div>
                <div className="text-sm font-medium text-white">
                  {step.icon} {step.label}
                </div>
              </div>

              {done && <div className="text-xs bg-[#27F4D2] text-black px-2 py-1 rounded font-semibold">NEW</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
