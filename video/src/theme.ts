// Colours and fonts shared by every scene.
export const FONT_HEAD = "'Baloo 2', 'Hind', sans-serif";
export const FONT_BODY = "'Hind', 'Baloo 2', sans-serif";

export const C = {
  ink: "#1d2433",
  inkSoft: "#4a5468",
  paper: "#fffaf0",
  cream: "#fff3d6",
  white: "#ffffff",
  shadow: "rgba(20, 24, 40, 0.22)",
  yellow: "#ffd23f",
  orange: "#ff8c42",
  red: "#ef476f",
  green: "#06d6a0",
  teal: "#118ab2",
  navy: "#073b4c",
  purple: "#7b5ea7",
  sky: "#8ecae6",
  mat: "#2f6b4f",
  matLine: "rgba(255,255,255,0.12)",
};

// Card colours used in turn for items in a visual.
export const ITEM_COLORS = ["#ffd23f", "#06d6a0", "#8ecae6", "#ffadad", "#cdb4db", "#ffc6a5", "#a0c4ff", "#caffbf"];

export const pick = <T,>(arr: T[], i: number) => arr[((i % arr.length) + arr.length) % arr.length];
