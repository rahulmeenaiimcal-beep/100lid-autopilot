// Shapes of the data the Python robot hands to the renderer (props.json).
// All frame numbers are absolute frames in the video unless a field says "relative".

export type Emotion =
  | "neutral" | "happy" | "excited" | "curious" | "worried" | "shocked" | "thinking" | "proud";
export type Gesture = "none" | "point" | "raise" | "think" | "wave" | "explain" | "thumbs";

export type CharacterLook = {
  name: string;
  skin: string;
  hair: string;
  hairStyle: "short" | "bald_sides" | "bun" | "long_braid" | "spiky" | "pagdi" | "side_part";
  beard: "none" | "stubble" | "full" | "white_full";
  mustache: boolean;
  glasses: boolean;
  top: string;
  topStyle: "kurta" | "shirt" | "tshirt" | "saree" | "blazer";
  accent: string;
  accessory: "none" | "backpack" | "id_badge" | "shawl" | "gamcha" | "apron" | "dupatta";
  bindi: boolean;
  pagdi?: string;
  height: number; // 0.85 .. 1.1
};

export type Talk = { from: number; to: number; id: string };

export type StageChar = {
  id: string;
  x: number; // 0..1 across the frame
  facing: 1 | -1;
  emotion: Emotion;
  gesture: Gesture;
};

export type VisualItem = { label: string; detail?: string; icon?: string; year?: string };

export type Visual =
  | { kind: "knolling"; title: string; items: VisualItem[] }
  | { kind: "exploded"; title: string; center: VisualItem; items: VisualItem[] }
  | { kind: "cutaway"; title: string; object: string; items: VisualItem[] }
  | { kind: "anatomy"; title: string; object: string; items: VisualItem[] }
  | { kind: "stat"; title: string; value: string; label: string; note?: string; icon?: string }
  | { kind: "timeline"; title: string; items: VisualItem[] }
  | { kind: "compare"; title: string; left: { title: string; points: string[] }; right: { title: string; points: string[] } }
  | { kind: "steps"; title: string; items: VisualItem[] }
  | { kind: "keyfacts"; title: string; items: VisualItem[] };

export type QuizQ = { q: string; options: string[]; answer: number; explain?: string };

export type Shot = {
  from: number;
  duration: number;
  layout: "hook" | "stage" | "board" | "chapter" | "quiz" | "recap" | "outro";
  setting?: string;
  chars?: StageChar[];
  presenter?: string; // character shown in the corner on board/quiz/recap layouts
  visual?: Visual;
  reveal?: number[]; // relative frames at which each visual item appears
  title?: string;
  subtitle?: string;
  sticker?: { text: string; from: number; to: number }[]; // relative frames
  quiz?: QuizQ & { qNo: number; total: number; countFrom: number; countTo: number; revealAt: number };
  recap?: string[];
  nextTitle?: string;
  camera?: "wide" | "close" | "push";
};

export type Caption = { from: number; to: number; text: string };

export type Chapter = { from: number; title: string };

export type EpisodeProps = {
  format: "long" | "short";
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  brand: { name: string; handle: string; accent: string; accent2: string };
  series: string;
  title: string;
  cast: Record<string, CharacterLook>;
  talk: Talk[];
  amp: string; // one digit 0-9 per frame: loudness of the voice at that frame
  shots: Shot[];
  captions: Caption[]; // burned in (Shorts only)
  chapters: Chapter[];
};

export type ThumbProps = {
  width: number;
  height: number;
  brand: { name: string; handle: string; accent: string; accent2: string };
  series: string;
  textTop: string;
  textBig: string;
  textSmall?: string;
  emotion: Emotion;
  character: CharacterLook;
  icon: string;
  palette: number; // 0..5 colour scheme
  layout: number; // 0..2
};
