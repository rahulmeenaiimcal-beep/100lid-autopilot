import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { EpisodeProps, Shot } from "./types";
import { C, FONT_BODY, FONT_HEAD } from "./theme";
import { FontGate } from "./fonts";
import {
  BoardLayout,
  ChapterLayout,
  Ctx,
  HookLayout,
  OutroLayout,
  QuizLayout,
  RecapLayout,
  StageLayout,
} from "./components/Layouts";

const ShotView: React.FC<{ ep: EpisodeProps; shot: Shot }> = ({ ep, shot }) => {
  const f = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const ctx: Ctx = { ep, shot, f, abs: shot.from + f, fps, W: width, H: height, vertical: height > width };
  switch (shot.layout) {
    case "hook":
      return <HookLayout ctx={ctx} />;
    case "board":
      return <BoardLayout ctx={ctx} />;
    case "chapter":
      return <ChapterLayout ctx={ctx} />;
    case "quiz":
      return <QuizLayout ctx={ctx} />;
    case "recap":
      return <RecapLayout ctx={ctx} />;
    case "outro":
      return <OutroLayout ctx={ctx} />;
    default:
      return <StageLayout ctx={ctx} />;
  }
};

// Thin progress bar with chapter ticks (long videos) — tells viewers how much is left.
const Progress: React.FC<{ ep: EpisodeProps }> = ({ ep }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const p = frame / Math.max(1, ep.durationInFrames - 1);
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: 10, background: "rgba(0,0,0,0.15)", zIndex: 50 }}>
      <div style={{ width: `${p * 100}%`, height: "100%", background: C.yellow }} />
      {ep.chapters.map((c, i) => (
        <div key={i} style={{ position: "absolute", left: (c.from / ep.durationInFrames) * width - 2, top: 0, width: 4, height: 10, background: C.ink }} />
      ))}
    </div>
  );
};

const Watermark: React.FC<{ ep: EpisodeProps; vertical: boolean }> = ({ ep, vertical }) => (
  <div
    style={{
      position: "absolute",
      right: vertical ? 30 : 34,
      top: vertical ? 40 : 26,
      background: "rgba(7,59,76,0.85)",
      color: C.yellow,
      fontFamily: FONT_HEAD,
      fontWeight: 800,
      fontSize: vertical ? 34 : 30,
      padding: "2px 16px",
      borderRadius: 12,
      zIndex: 60,
    }}
  >
    {ep.brand.name}
  </div>
);

// Burned-in captions for Shorts (most viewers watch with sound off at first).
const BurnedCaptions: React.FC<{ ep: EpisodeProps }> = ({ ep }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const cap = ep.captions.find((c) => frame >= c.from && frame < c.to);
  if (!cap) return null;
  const words = cap.text.split(" ");
  const t = (frame - cap.from) / Math.max(1, cap.to - cap.from);
  const active = Math.min(words.length - 1, Math.floor(t * words.length));
  const u = width / 1080;
  return (
    <div style={{ position: "absolute", left: 40 * u, right: 40 * u, top: height * 0.665, display: "flex", justifyContent: "center", zIndex: 40 }}>
      <div style={{ background: "rgba(0,0,0,0.72)", borderRadius: 22 * u, padding: `${10 * u}px ${24 * u}px`, textAlign: "center", fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 64 * u, lineHeight: 1.18, color: "#fff" }}>
        {words.map((w, i) => (
          <span key={i} style={{ color: i === active ? C.yellow : "#fff" }}>
            {w}
            {i < words.length - 1 ? " " : ""}
          </span>
        ))}
      </div>
    </div>
  );
};

// English subtitles for long videos: a dark bar in the reserved band at the bottom.
const LongSubs: React.FC<{ ep: EpisodeProps }> = ({ ep }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const subs = ep.subs || [];
  const cue = subs.find((c) => frame >= c.from && frame < c.to);
  if (!cue) return null;
  const u = width / 1920;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: height * 0.018, height: height * 0.105, display: "flex", alignItems: "center", justifyContent: "center", zIndex: 45 }}>
      <div
        style={{
          maxWidth: "78%",
          background: "rgba(10,14,24,0.82)",
          color: "#ffffff",
          fontFamily: FONT_BODY,
          fontWeight: 600,
          fontSize: 44 * u,
          lineHeight: 1.22,
          textAlign: "center",
          padding: `${8 * u}px ${26 * u}px`,
          borderRadius: 14 * u,
        }}
      >
        {cue.text}
      </div>
    </div>
  );
};

export const Episode: React.FC<EpisodeProps> = (ep) => {
  const { width, height } = useVideoConfig();
  const vertical = height > width;
  return (
    <FontGate>
      <AbsoluteFill style={{ background: C.paper }}>
        {ep.shots.map((s, i) => (
          <Sequence key={i} from={s.from} durationInFrames={Math.max(1, s.duration)} layout="none">
            <ShotView ep={ep} shot={s} />
          </Sequence>
        ))}
        {vertical ? <BurnedCaptions ep={ep} /> : <Progress ep={ep} />}
        {!vertical && <LongSubs ep={ep} />}
        <Watermark ep={ep} vertical={vertical} />
      </AbsoluteFill>
    </FontGate>
  );
};
