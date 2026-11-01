const LOADING_PHASES = [
  { upToSeconds: 10, toProgress: 33, message: "Fetching your league's data" },
  { upToSeconds: 25, toProgress: 66, message: 'Calculating' },
  {
    upToSeconds: 45,
    toProgress: 90,
    message: 'Creating your league dashboard',
  },
];

export function computeLoadingState(elapsedSeconds: number): {
  message: string;
  progress: number;
} {
  let from = 0;
  let fromSeconds = 0;
  for (const phase of LOADING_PHASES) {
    if (elapsedSeconds < phase.upToSeconds) {
      const phaseDuration = phase.upToSeconds - fromSeconds;
      const phaseElapsed = elapsedSeconds - fromSeconds;
      const progress =
        from + (phaseElapsed / phaseDuration) * (phase.toProgress - from);
      return { message: phase.message, progress };
    }
    from = phase.toProgress;
    fromSeconds = phase.upToSeconds;
  }
  return {
    message: LOADING_PHASES[LOADING_PHASES.length - 1].message,
    progress: 90,
  };
}
