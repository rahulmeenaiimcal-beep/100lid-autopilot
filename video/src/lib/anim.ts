import { Easing, interpolate, spring } from "remotion";

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// 0 -> 1 over `dur` frames starting at `start`, eased.
export const ease = (frame: number, start: number, dur = 12) =>
  interpolate(frame, [start, start + dur], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });

export const pop = (frame: number, fps: number, start: number, damping = 12) =>
  spring({ frame: frame - start, fps, config: { damping, stiffness: 160, mass: 0.7 } });

// Fade in at the start of a shot and out at its end.
export const shotFade = (frame: number, duration: number, inF = 6, outF = 6) =>
  Math.min(
    interpolate(frame, [0, inF], [0, 1], clamp),
    interpolate(frame, [duration - outF, duration], [1, 0], clamp)
  );

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

// Deterministic pseudo-random number in [0,1) from a string/number seed.
export const rand = (seed: string | number) => {
  let h = 2166136261;
  const s = String(seed);
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 100000) / 100000;
};
