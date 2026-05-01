import { TEAM_COLORS } from '../constants/teamColors';
import { useCountdown } from '../hooks/useCountdown';

export function Countdown({ targetDate, className = '' }) {
  const timeLeft = useCountdown(targetDate);

  if (!timeLeft) {
    return (
      <div className={className}>
        <span className="text-sm text-[#777777]">Race in progress</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-4 ${className}`}>
      <div className="text-center">
        <div className="text-3xl font-bold text-white">{timeLeft.days}</div>
        <div className="text-xs text-[#777777]">days</div>
      </div>
      <div className="text-2xl text-[#777777]">:</div>
      <div className="text-center">
        <div className="text-3xl font-bold text-white">{String(timeLeft.hours).padStart(2, '0')}</div>
        <div className="text-xs text-[#777777]">hours</div>
      </div>
      <div className="text-2xl text-[#777777]">:</div>
      <div className="text-center">
        <div className="text-3xl font-bold text-white">{String(timeLeft.minutes).padStart(2, '0')}</div>
        <div className="text-xs text-[#777777]">mins</div>
      </div>
      <div className="text-2xl text-[#777777]">:</div>
      <div className="text-center">
        <div className="text-3xl font-bold text-white">{String(timeLeft.seconds).padStart(2, '0')}</div>
        <div className="text-xs text-[#777777]">secs</div>
      </div>
    </div>
  );
}
