import React from "react";
import { AbsoluteFill } from "remotion";
import { ThumbProps } from "./types";
import { C, FONT_HEAD } from "./theme";
import { FontGate } from "./fonts";
import { Character } from "./components/Character";
import { Icon } from "./components/Icon";

// Click-worthy but honest thumbnails: one expressive face, 2-4 huge words,
// one bold object, strong contrast, the same brand badge every time.

const PALETTES = [
  ["#ff6b00", "#ffb700", "#1d0f00"],
  ["#0057ff", "#00c2ff", "#00122e"],
  ["#d90429", "#ff5d73", "#2b0007"],
  ["#00a86b", "#7ae582", "#002417"],
  ["#7209b7", "#f72585", "#14002b"],
  ["#111111", "#3a3a3a", "#000000"],
];

const outline = (px: number, color: string) => {
  const s: string[] = [];
  for (let a = 0; a < 360; a += 30) {
    const r = (a * Math.PI) / 180;
    s.push(`${(Math.cos(r) * px).toFixed(1)}px ${(Math.sin(r) * px).toFixed(1)}px 0 ${color}`);
  }
  s.push(`0 ${px * 1.6}px 0 ${color}`);
  return s.join(",");
};

export const Thumbnail: React.FC<ThumbProps> = (p) => {
  const [a, b, dark] = PALETTES[p.palette % PALETTES.length];
  const flip = p.layout % 2 === 1;
  const W = p.width;
  const H = p.height;
  const u = W / 1280;
  const charH = H * 1.55;
  return (
    <FontGate>
      <AbsoluteFill style={{ background: `linear-gradient(135deg, ${a}, ${b})`, overflow: "hidden" }}>
        <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
          {Array.from({ length: 16 }).map((_, i) => {
            const ang = (i * 22.5 * Math.PI) / 180;
            const cx = flip ? W * 0.3 : W * 0.7;
            const cy = H * 0.5;
            const r = W;
            return (
              <path
                key={i}
                d={`M${cx} ${cy} L${cx + Math.cos(ang) * r} ${cy + Math.sin(ang) * r} L${cx + Math.cos(ang + 0.2) * r} ${cy + Math.sin(ang + 0.2) * r} Z`}
                fill="rgba(255,255,255,0.10)"
              />
            );
          })}
        </svg>
        {/* the object */}
        <div
          style={{
            position: "absolute",
            [flip ? "left" : "right"]: W * 0.06,
            top: H * 0.06,
            width: 300 * u,
            height: 300 * u,
            borderRadius: "50%",
            background: "#fff",
            border: `${12 * u}px solid ${dark}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transform: "rotate(-8deg)",
            boxShadow: `0 ${16 * u}px 0 rgba(0,0,0,0.35)`,
          } as React.CSSProperties}
        >
          <Icon name={p.icon} size={190 * u} color={a} stroke={2.4} />
        </div>
        {/* the face */}
        <div
          style={{
            position: "absolute",
            [flip ? "right" : "left"]: -W * 0.03,
            top: -H * 0.08,
            filter: `drop-shadow(0 0 ${10 * u}px #fff) drop-shadow(0 0 ${4 * u}px #fff)`,
          } as React.CSSProperties}
        >
          <Character look={p.character} emotion={p.emotion} gesture={p.emotion === "shocked" ? "raise" : "point"} frame={7} seed="thumb" height={charH} facing={flip ? -1 : 1} />
        </div>
        {/* words */}
        <div
          style={{
            position: "absolute",
            [flip ? "left" : "right"]: W * 0.035,
            top: H * 0.4,
            width: W * 0.6,
            display: "flex",
            flexDirection: "column",
            alignItems: flip ? "flex-start" : "flex-end",
            gap: 8 * u,
          } as React.CSSProperties}
        >
          {p.textTop && (
            <div style={{ background: C.yellow, color: dark, fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 44 * u, padding: `${2 * u}px ${18 * u}px`, borderRadius: 10 * u, transform: "rotate(-2deg)" }}>
              {p.textTop}
            </div>
          )}
          <div
            style={{
              color: "#fff",
              fontFamily: FONT_HEAD,
              fontWeight: 800,
              fontSize: (p.textBig.length > 14 ? 104 : 128) * u,
              lineHeight: 0.98,
              textAlign: flip ? "left" : "right",
              textShadow: outline(7 * u, dark),
            }}
          >
            {p.textBig}
          </div>
          {p.textSmall && (
            <div style={{ background: "#fff", color: C.red, fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 40 * u, padding: `${2 * u}px ${16 * u}px`, borderRadius: 40 * u, border: `${4 * u}px solid ${dark}` }}>
              {p.textSmall}
            </div>
          )}
        </div>
        <div style={{ position: "absolute", [flip ? "right" : "left"]: 18 * u, bottom: 16 * u, background: C.navy, color: C.yellow, fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 30 * u, padding: `${2 * u}px ${14 * u}px`, borderRadius: 10 * u } as React.CSSProperties}>
          {p.brand.name}
        </div>
      </AbsoluteFill>
    </FontGate>
  );
};
