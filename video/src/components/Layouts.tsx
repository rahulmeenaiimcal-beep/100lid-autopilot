import React from "react";
import { interpolate } from "remotion";
import { CharacterLook, EpisodeProps, Shot, StageChar, Talk } from "../types";
import { C, FONT_BODY, FONT_HEAD, ITEM_COLORS, pick } from "../theme";
import { clamp, ease, pop } from "../lib/anim";
import { Character } from "./Character";
import { Setting } from "./Settings";
import { Device } from "./Devices";
import { Icon } from "./Icon";

export type Ctx = {
  ep: EpisodeProps;
  shot: Shot;
  f: number; // frame relative to shot
  abs: number; // absolute frame
  fps: number;
  W: number;
  H: number;
  vertical: boolean;
};

export const talkerAt = (talk: Talk[], abs: number) => {
  for (let i = 0; i < talk.length; i++) {
    const t = talk[i];
    if (abs >= t.from && abs < t.to) return t.id;
  }
  return null;
};

export const ampAt = (amp: string, abs: number) => {
  const c = amp.charCodeAt(abs);
  if (!c || c < 48 || c > 57) return 0;
  return (c - 48) / 9;
};

const CharOnStage: React.FC<{
  ctx: Ctx;
  sc: StageChar;
  look: CharacterLook;
  height: number;
  x: number;
  bottom: number;
  dim?: boolean;
}> = ({ ctx, sc, look, height, x, bottom, dim }) => {
  const speaker = talkerAt(ctx.ep.talk, ctx.abs);
  const talking = speaker === sc.id;
  const mouth = talking ? ampAt(ctx.ep.amp, ctx.abs) : 0;
  const w = (height * 400) / 900;
  const enter = ease(ctx.f, 0, 10);
  return (
    <div
      style={{
        position: "absolute",
        left: x - w / 2,
        bottom,
        width: w,
        height,
        filter: dim ? "saturate(0.85) brightness(0.96)" : undefined,
        transform: `translateY(${(1 - enter) * 30}px)`,
      }}
    >
      <Character
        look={look}
        emotion={sc.emotion}
        gesture={talking ? sc.gesture : sc.gesture === "point" ? "none" : sc.gesture}
        mouth={mouth}
        talking={talking}
        frame={ctx.abs}
        seed={sc.id}
        height={height}
        facing={sc.facing}
      />
    </div>
  );
};

const Stickers: React.FC<{ ctx: Ctx; u: number; top: number }> = ({ ctx, u, top }) => {
  const st = ctx.shot.sticker || [];
  return (
    <>
      {st.map((s, i) => {
        if (ctx.f < s.from || ctx.f > s.to + 8) return null;
        const p = pop(ctx.f, ctx.fps, s.from, 9);
        const out = interpolate(ctx.f, [s.to, s.to + 8], [1, 0], clamp);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top,
              display: "flex",
              justifyContent: "center",
              opacity: out,
              zIndex: 20,
            }}
          >
            <div
              style={{
                transform: `scale(${p}) rotate(${(i % 2 ? 1 : -1) * 2}deg)`,
                background: pick([C.yellow, "#fff", C.green, C.sky], i),
                color: C.ink,
                fontFamily: FONT_HEAD,
                fontWeight: 800,
                fontSize: 64 * u,
                padding: `${6 * u}px ${30 * u}px`,
                borderRadius: 20 * u,
                border: `${6 * u}px solid ${C.ink}`,
                boxShadow: `${8 * u}px ${8 * u}px 0 ${C.ink}`,
                maxWidth: "86%",
                textAlign: "center",
                lineHeight: 1.15,
              }}
            >
              {s.text}
            </div>
          </div>
        );
      })}
    </>
  );
};

// --------------------------------------------------------------- STAGE: characters in a setting
export const StageLayout: React.FC<{ ctx: Ctx }> = ({ ctx }) => {
  const { shot, W, H, vertical, ep } = ctx;
  const chars = shot.chars || [];
  const u = vertical ? W / 1080 : W / 1920;
  const speaker = talkerAt(ep.talk, ctx.abs);
  const charH = vertical ? H * 0.5 : H * 0.78;
  const bottom = vertical ? H * 0.2 : H * 0.03;
  const xs = chars.map((c) => c.x * W);
  // camera
  const cam = shot.camera || "wide";
  let scale = 1;
  let ox = W / 2;
  let oy = H * 0.75;
  if (cam === "close") {
    const idx = Math.max(0, chars.findIndex((c) => c.id === speaker));
    scale = vertical ? 1.25 : 1.55;
    ox = xs[idx] ?? W / 2;
    oy = H * (vertical ? 0.62 : 0.62);
  }
  const push = cam === "push" ? interpolate(ctx.f, [0, shot.duration], [1, 1.12], clamp) : 1;
  const settle = interpolate(ctx.f, [0, 14], [1.05, 1], clamp);
  const s = scale * push * settle;
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
      <div style={{ position: "absolute", inset: 0, transformOrigin: `${ox}px ${oy}px`, transform: `scale(${s})` }}>
        {shot.setting !== "none_transparent" && <Setting name={shot.setting} width={W} height={H} frame={ctx.abs} />}
        {chars.map((c, i) => (
          <CharOnStage
            key={c.id + i}
            ctx={ctx}
            sc={c}
            look={ep.cast[c.id]}
            height={charH * (ep.cast[c.id]?.height || 1)}
            x={xs[i]}
            bottom={bottom}
            dim={!!speaker && speaker !== c.id}
          />
        ))}
      </div>
      <Stickers ctx={ctx} u={u} top={vertical ? H * 0.16 : H * 0.07} />
    </div>
  );
};

// --------------------------------------------------------------- BOARD: a visual device + presenter in the corner
export const BoardLayout: React.FC<{ ctx: Ctx }> = ({ ctx }) => {
  const { shot, W, H, vertical, ep, fps } = ctx;
  const u = vertical ? W / 1080 : W / 1920;
  const box = vertical
    ? { x: W * 0.04, y: H * 0.13, w: W * 0.92, h: H * 0.5 }
    : { x: W * 0.035, y: H * 0.06, w: W * 0.72, h: H * 0.88 };
  const enter = pop(ctx.f, fps, 0, 15);
  const presenterDefault = shot.presenter || Object.keys(ep.cast)[0];
  const speaker = talkerAt(ep.talk, ctx.abs);
  const presenter = speaker && ep.cast[speaker] ? speaker : presenterDefault;
  const look = ep.cast[presenter];
  const talking = speaker === presenter;
  const listenerId: string | null = null;
  const pH = vertical ? H * 0.3 : H * 0.72;
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
      <Setting name="studio" width={W} height={H} frame={ctx.abs} />
      <div
        style={{
          position: "absolute",
          left: box.x,
          top: box.y,
          width: box.w,
          height: box.h,
          transform: `translateY(${(1 - enter) * H * 0.4}px) scale(${0.9 + 0.1 * enter})`,
          borderRadius: 30 * u,
          boxShadow: `0 ${16 * u}px 0 rgba(0,0,0,0.18)`,
          border: `${6 * u}px solid ${C.ink}`,
          overflow: "hidden",
        }}
      >
        {shot.visual && (
          <Device v={shot.visual} reveal={shot.reveal || []} f={ctx.f} fps={fps} w={box.w} h={box.h} k={vertical ? 1.55 : 1} />
        )}
      </div>
      {look && (
        <div style={{ position: "absolute", right: vertical ? W * 0.02 : W * 0.0, bottom: vertical ? H * 0.06 : -H * 0.02, width: (pH * 400) / 900, height: pH }}>
          <Character
            look={look}
            emotion={talking ? "happy" : "neutral"}
            gesture={talking ? "explain" : "none"}
            mouth={talking ? ampAt(ep.amp, ctx.abs) : 0}
            talking={talking}
            frame={ctx.abs}
            seed={presenter}
            height={pH}
            facing={-1}
          />
        </div>
      )}
      {listenerId && ep.cast[listenerId] && (
        <div style={{ position: "absolute", left: vertical ? W * 0.02 : W * 0.6, bottom: vertical ? H * 0.06 : -H * 0.06, width: (pH * 0.85 * 400) / 900, height: pH * 0.85 }}>
          <Character
            look={ep.cast[listenerId]}
            emotion="curious"
            gesture="raise"
            mouth={ampAt(ep.amp, ctx.abs)}
            talking
            frame={ctx.abs}
            seed={listenerId}
            height={pH * 0.85}
            facing={1}
          />
        </div>
      )}
    </div>
  );
};

// --------------------------------------------------------------- HOOK: big question over a teaser visual
export const HookLayout: React.FC<{ ctx: Ctx }> = ({ ctx }) => {
  const { shot, W, H, vertical, fps } = ctx;
  const u = vertical ? W / 1080 : W / 1920;
  const slam = pop(ctx.f, fps, 4, 9);
  const shake = ctx.f < 14 ? Math.sin(ctx.f * 3) * 6 * (1 - ctx.f / 14) : 0;
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
      {shot.visual ? (
        <div style={{ position: "absolute", inset: 0, filter: "brightness(0.55) saturate(1.1)" }}>
          <Device v={shot.visual} reveal={shot.reveal || []} f={ctx.f + 20} fps={fps} w={W} h={H} k={vertical ? 1.5 : 1} />
        </div>
      ) : (
        <StageLayout ctx={{ ...ctx, shot: { ...shot, camera: "push" } }} />
      )}
      {shot.chars && shot.visual && (
        <div style={{ position: "absolute", inset: 0 }}>
          <StageLayout ctx={{ ...ctx, shot: { ...shot, setting: "none_transparent" } }} />
        </div>
      )}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: vertical ? H * 0.12 : H * 0.08,
          display: "flex",
          justifyContent: "center",
          transform: `translateX(${shake}px)`,
          zIndex: 30,
        }}
      >
        <div
          style={{
            transform: `scale(${slam}) rotate(-2deg)`,
            background: C.yellow,
            color: C.ink,
            fontFamily: FONT_HEAD,
            fontWeight: 800,
            fontSize: (vertical ? 92 : 96) * u,
            lineHeight: 1.08,
            padding: `${12 * u}px ${40 * u}px`,
            borderRadius: 26 * u,
            border: `${8 * u}px solid ${C.ink}`,
            boxShadow: `${12 * u}px ${12 * u}px 0 ${C.ink}`,
            maxWidth: "88%",
            textAlign: "center",
          }}
        >
          {shot.title}
        </div>
      </div>
      {shot.subtitle && (
        <div style={{ position: "absolute", left: 0, right: 0, top: vertical ? H * 0.255 : H * 0.27, textAlign: "center", zIndex: 30, opacity: ease(ctx.f, 18, 10) }}>
          <span style={{ background: C.red, color: "#fff", fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 54 * u, padding: `${6 * u}px ${24 * u}px`, borderRadius: 14 * u }}>
            {shot.subtitle}
          </span>
        </div>
      )}
    </div>
  );
};

// --------------------------------------------------------------- CHAPTER CARD
export const ChapterLayout: React.FC<{ ctx: Ctx }> = ({ ctx }) => {
  const { shot, W, H, vertical, fps } = ctx;
  const u = vertical ? W / 1080 : W / 1920;
  const wipe = ease(ctx.f, 0, 10);
  const t = pop(ctx.f, fps, 6, 11);
  const color = pick([C.teal, C.purple, C.red, C.navy, C.orange], (shot.title || "").length);
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", background: C.paper }}>
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${wipe * 100}%`, background: color }} />
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", transform: `scale(${t})` }}>
        <div style={{ fontFamily: FONT_HEAD, fontWeight: 700, fontSize: 48 * u, color: "rgba(255,255,255,0.85)", letterSpacing: 4 * u }}>{shot.subtitle}</div>
        <div style={{ fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 110 * u, color: "#fff", textAlign: "center", lineHeight: 1.1, maxWidth: "85%", textShadow: `0 ${8 * u}px 0 rgba(0,0,0,0.25)` }}>
          {shot.title}
        </div>
      </div>
    </div>
  );
};

// --------------------------------------------------------------- QUIZ with countdown
export const QuizLayout: React.FC<{ ctx: Ctx }> = ({ ctx }) => {
  const { shot, W, H, vertical, fps, ep } = ctx;
  const q = shot.quiz!;
  const u = vertical ? W / 1080 : W / 1920;
  const revealed = ctx.f >= q.revealAt;
  const countT = interpolate(ctx.f, [q.countFrom, q.countTo], [0, 1], clamp);
  const secsLeft = Math.max(0, Math.ceil((q.countTo - ctx.f) / fps));
  const enter = pop(ctx.f, fps, 0, 14);
  const cols = vertical ? 1 : 2;
  const presenter = shot.presenter || Object.keys(ep.cast)[0];
  const speaker = talkerAt(ep.talk, ctx.abs);
  const pH = vertical ? H * 0.24 : H * 0.55;
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", background: "linear-gradient(160deg,#3a0ca3,#7209b7)" }}>
      <div style={{ position: "absolute", top: vertical ? H * 0.1 : H * 0.06, left: W * 0.05, right: W * 0.05, transform: `scale(${enter})` }}>
        <div style={{ fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 46 * u, color: C.yellow }}>
          QUIZ · प्रश्न {q.qNo}/{q.total}
        </div>
        <div style={{ fontFamily: FONT_HEAD, fontWeight: 800, fontSize: (vertical ? 70 : 76) * u, color: "#fff", lineHeight: 1.15, marginTop: 10 * u, maxWidth: vertical ? undefined : W * 0.8 }}>{q.q}</div>
      </div>
      <div
        style={{
          position: "absolute",
          left: W * 0.05,
          right: vertical ? W * 0.05 : W * 0.3,
          top: vertical ? H * 0.34 : H * 0.42,
          display: "grid",
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gap: 22 * u,
        }}
      >
        {q.options.map((o, i) => {
          const t = pop(ctx.f, fps, 8 + i * 5, 13);
          const correct = i === q.answer;
          const bg = revealed ? (correct ? C.green : "rgba(255,255,255,0.35)") : "#fff";
          return (
            <div
              key={i}
              style={{
                transform: `scale(${t * (revealed && correct ? 1 + 0.04 * Math.sin(ctx.f / 3) : 1)})`,
                background: bg,
                borderRadius: 22 * u,
                padding: `${16 * u}px ${22 * u}px`,
                display: "flex",
                alignItems: "center",
                gap: 16 * u,
                border: `${5 * u}px solid ${revealed && correct ? "#fff" : "transparent"}`,
                boxShadow: `0 ${8 * u}px 0 rgba(0,0,0,0.25)`,
              }}
            >
              <div style={{ minWidth: 60 * u, height: 60 * u, borderRadius: "50%", background: pick(ITEM_COLORS, i), display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 34 * u, color: C.ink }}>
                {"ABCD"[i]}
              </div>
              <div style={{ fontFamily: FONT_BODY, fontWeight: 700, fontSize: 50 * u, color: C.ink, lineHeight: 1.2 }}>{o}</div>
            </div>
          );
        })}
      </div>
      {!revealed && ctx.f >= q.countFrom && (
        <div style={{ position: "absolute", right: vertical ? W * 0.08 : W * 0.06, top: vertical ? H * 0.6 : H * 0.42, width: 170 * u, height: 170 * u }}>
          <svg width={170 * u} height={170 * u}>
            <circle cx={85 * u} cy={85 * u} r={72 * u} fill="rgba(0,0,0,0.25)" stroke="rgba(255,255,255,0.25)" strokeWidth={14 * u} />
            <circle
              cx={85 * u}
              cy={85 * u}
              r={72 * u}
              fill="none"
              stroke={C.yellow}
              strokeWidth={14 * u}
              strokeDasharray={`${2 * Math.PI * 72 * u}`}
              strokeDashoffset={`${2 * Math.PI * 72 * u * countT}`}
              transform={`rotate(-90 ${85 * u} ${85 * u})`}
              strokeLinecap="round"
            />
            <text x={85 * u} y={110 * u} textAnchor="middle" fontSize={76 * u} fontWeight={800} fill="#fff" fontFamily={FONT_HEAD}>
              {secsLeft}
            </text>
          </svg>
        </div>
      )}
      {revealed && q.explain && (
        <div style={{ position: "absolute", left: W * 0.05, right: vertical ? W * 0.05 : W * 0.3, bottom: vertical ? H * 0.3 : H * 0.06, background: "rgba(255,255,255,0.95)", borderRadius: 20 * u, padding: `${14 * u}px ${22 * u}px`, fontFamily: FONT_BODY, fontWeight: 600, fontSize: 44 * u, color: C.ink, opacity: ease(ctx.f, q.revealAt + 4, 10) }}>
          ✅ {q.explain}
        </div>
      )}
      {ep.cast[presenter] && (
        <div style={{ position: "absolute", right: vertical ? W * 0.62 : W * 0.02, bottom: vertical ? H * 0.02 : -H * 0.03, width: (pH * 400) / 900, height: pH }}>
          <Character
            look={ep.cast[presenter]}
            emotion={revealed ? "excited" : "curious"}
            gesture={revealed ? "thumbs" : "think"}
            mouth={speaker === presenter ? ampAt(ep.amp, ctx.abs) : 0}
            talking={speaker === presenter}
            frame={ctx.abs}
            seed={presenter}
            height={pH}
            facing={-1}
          />
        </div>
      )}
    </div>
  );
};

// --------------------------------------------------------------- RECAP (screenshot this)
export const RecapLayout: React.FC<{ ctx: Ctx }> = ({ ctx }) => {
  const { shot, W, H, vertical, fps } = ctx;
  const u = vertical ? W / 1080 : W / 1920;
  const items = shot.recap || [];
  const reveal = shot.reveal || [];
  const badge = pop(ctx.f, fps, 10, 8);
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", background: "#0b2545" }}>
      <div style={{ position: "absolute", left: W * 0.06, right: W * 0.06, top: H * 0.06, bottom: H * 0.06, background: "#fffef6", borderRadius: 30 * u, padding: 40 * u, boxSizing: "border-box" }}>
        <div style={{ fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 70 * u, color: C.ink }}>{shot.title || "Quick Recap"}</div>
        {items.map((it, i) => {
          const start = reveal[i] ?? i * 25;
          const t = ease(ctx.f, start, 10);
          return (
            <div key={i} style={{ display: "flex", gap: 18 * u, alignItems: "flex-start", marginTop: 18 * u, opacity: t, transform: `translateX(${(1 - t) * 40 * u}px)` }}>
              <div style={{ minWidth: 50 * u, height: 50 * u, borderRadius: 12 * u, background: C.green, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 36 * u, marginTop: 4 * u }}>✓</div>
              <div style={{ fontFamily: FONT_BODY, fontWeight: 700, fontSize: (vertical ? 50 : 52) * u, color: C.ink, lineHeight: 1.25 }}>{it}</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", right: W * 0.08, top: H * 0.08, transform: `rotate(8deg) scale(${badge})`, background: C.red, color: "#fff", fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 40 * u, padding: `${10 * u}px ${22 * u}px`, borderRadius: 14 * u, display: "flex", alignItems: "center", gap: 10 * u }}>
        <Icon name="photo" size={40 * u} color="#fff" /> Screenshot लें!
      </div>
    </div>
  );
};

// --------------------------------------------------------------- OUTRO
export const OutroLayout: React.FC<{ ctx: Ctx }> = ({ ctx }) => {
  const { shot, W, H, vertical, fps, ep } = ctx;
  const u = vertical ? W / 1080 : W / 1920;
  const p1 = pop(ctx.f, fps, 0, 12);
  const p2 = pop(ctx.f, fps, 14, 10);
  const click = ctx.f > 40 && ctx.f < 52;
  const chars = Object.keys(ep.cast).slice(0, 2);
  const pH = vertical ? H * 0.32 : H * 0.5;
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
      <Setting name="studio" width={W} height={H} frame={ctx.abs} />
      <div style={{ position: "absolute", left: 0, right: 0, top: vertical ? H * 0.12 : H * 0.1, display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${p1})` }}>
        <div style={{ fontFamily: FONT_HEAD, fontWeight: 700, fontSize: 44 * u, color: C.inkSoft }}>अगला वीडियो · Next</div>
        <div style={{ marginTop: 10 * u, background: C.navy, color: "#fff", fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 64 * u, padding: `${14 * u}px ${36 * u}px`, borderRadius: 24 * u, maxWidth: "80%", textAlign: "center", lineHeight: 1.15 }}>
          {shot.nextTitle || ep.series}
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: vertical ? H * 0.42 : H * 0.48, display: "flex", justifyContent: "center", transform: `scale(${p2 * (click ? 0.92 : 1)})` }}>
        <div style={{ background: click || ctx.f > 52 ? "#606060" : "#ff0000", color: "#fff", fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 56 * u, padding: `${14 * u}px ${40 * u}px`, borderRadius: 50 * u, display: "flex", alignItems: "center", gap: 14 * u }}>
          🔔 {ctx.f > 52 ? "SUBSCRIBED" : "SUBSCRIBE"}
        </div>
      </div>
      {chars.map((id, i) => (
        <div key={id} style={{ position: "absolute", left: i === 0 ? W * 0.06 : undefined, right: i === 1 ? W * 0.06 : undefined, bottom: -H * 0.02, width: (pH * 400) / 900, height: pH }}>
          <Character look={ep.cast[id]} emotion="happy" gesture="wave" frame={ctx.abs} seed={id} height={pH} facing={i === 0 ? 1 : -1} talking={talkerAt(ep.talk, ctx.abs) === id} mouth={talkerAt(ep.talk, ctx.abs) === id ? ampAt(ep.amp, ctx.abs) : 0} />
        </div>
      ))}
    </div>
  );
};
