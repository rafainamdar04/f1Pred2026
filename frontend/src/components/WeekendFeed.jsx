import { useApi } from '../hooks/useApi';

export function WeekendFeed({ round, onNavigate = null }) {
  const { data: status } = useApi('/api/pipeline/status');
  const { data: calendar } = useApi('/api/calendar');

  if (!status || !calendar) {
    return <div className="text-[#777777] text-sm">Loading weekend schedule…</div>;
  }

  const race = calendar.races?.find((r) => r.round === round);
  const raceDate = race?.date ? new Date(race.date) : null;

  // Simple step indicators for the weekend
  const steps = [
    { day: 'Thursday', label: 'Pre-Quali Predictions', icon: '📊' },
    { day: 'Saturday', label: 'Qualifying happens', icon: '🏁' },
    { day: 'Saturday', label: 'Post-Quali Update', icon: '📈' },
    { day: 'Sunday', label: 'Race + Results', icon: '🏆' },
  ];

  const now = new Date();
  const isCompleted = (idx) => {
    // Placeholder logic - in real app, check against pipeline status timestamps
    return idx === 0; // First step always "done" for demo
  };

  const isInProgress = (idx) => {
    return idx === 1; // Second step in progress
  };

  return (
    <div className="space-y-3">
      <div className="text-xs font-bold text-[#777777] uppercase tracking-wider">Weekend Timeline</div>
      <div className="space-y-2">
        {steps.map((step, idx) => {
          const done = isCompleted(idx);
          const inProgress = isInProgress(idx);
          const isClickable = idx === 0 || idx === 2;

          return (
            <div
              key={idx}
              className={`flex items-center gap-3 px-4 py-3 bg-[#111111] border border-[rgba(255,255,255,0.07)] rounded transition ${
                isClickable ? 'cursor-pointer hover:border-[rgba(255,255,255,0.14)]' : ''
              }`}
              onClick={() => {
                if (isClickable && onNavigate) {
                  onNavigate(round);
                }
              }}
              role={isClickable ? 'button' : undefined}
            >
              {/* Circle indicator */}
              <div className="relative w-6 h-6 flex-shrink-0">
                {inProgress ? (
                  <div className="w-full h-full rounded-full border-2 border-[#E10600] border-t-transparent animate-spin"></div>
                ) : (
                  <div
                    className={`w-full h-full rounded-full flex items-center justify-center ${
                      done ? 'bg-[#27F4D2]' : 'border-2 border-[#777777]'
                    }`}
                  >
                    {done && <div className="text-white text-sm">✓</div>}
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="flex-1">
                <div className="text-xs text-[#777777]">{step.day}</div>
                <div className="text-sm font-medium text-white">
                  {step.icon} {step.label}
                </div>
              </div>

              {/* Badge */}
              {done && <div className="text-xs bg-[#27F4D2] text-black px-2 py-1 rounded font-semibold">NEW</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
