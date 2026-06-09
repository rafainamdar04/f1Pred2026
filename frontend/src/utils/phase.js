// Client-side race-weekend phase, mirroring the backend's _race_phase.
//
// On a static-snapshot deploy the calendar JSON is regenerated only on the CI
// cadence, so a baked-in `phase` would go stale between runs. The appointed
// times (prequali_at_utc / postquali_at_utc / result_at_utc) are fixed
// timestamps, so we recompute phase + availability from the current clock here
// — the lifecycle stays live (Upcoming -> Pre-Quali Out -> Post-Quali Out ->
// Complete) on every render, while only the prediction *content* waits for CI.

function ts(value) {
  if (!value) return null;
  const t = new Date(value).getTime();
  return Number.isNaN(t) ? null : t;
}

export function computeRacePhase(race, now = Date.now()) {
  if (!race) {
    return { phase: 'upcoming', prequali_available: false, postquali_available: false, result_available: false };
  }
  const pre = ts(race.prequali_at_utc);
  const post = ts(race.postquali_at_utc);
  const res = ts(race.result_at_utc);

  const prequali_available = pre != null && now >= pre;
  const postquali_available = post != null && now >= post;
  const result_available = res != null && now >= res;

  let phase = 'upcoming';
  if (result_available) phase = 'completed';
  else if (postquali_available) phase = 'postquali';
  else if (prequali_available) phase = 'prequali';

  return { phase, prequali_available, postquali_available, result_available };
}
