import React from "react";
import { interpolate } from "remotion";
import { Visual, VisualItem } from "../types";
import { C, FONT_BODY, FONT_HEAD, ITEM_COLORS, pick } from "../theme";
import { clamp, ease, pop, rand } from "../lib/anim";
import { Icon } from "./Icon";

// "Visual devices": the eye-catching explainer moments.
// Every device fills a w x h box and reveals its items at the frames in `reveal`
// (relative to the start of the shot), so each item appears exactly when the
// narrator starts talking about it.

export type DeviceProps = {
  v: Visual;
  reveal: number[];
  f: number; // frame relative to shot start
  fps: number;
  w: number;
  h: number;
  k?: number; // text scale (bigger on vertical Shorts)
};

const at = (reveal: number[], i: number, fallbackGap = 30) =>
  reveal[i] !== undefined ? reveal[i] : (reveal[reveal.length - 1] ?? 0) + (i - reveal.length + 1) * fallbackGap;

const Title: React.FC<{ text: string; f: number; u: number; color?: string; bg?: string }> = ({
  text,
  f,
  u,
  color = C.ink,
  bg = C.yellow,
}) => {
  const t = ease(f, 0, 14);
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: 18 * u,
        display: "flex",
        justifyContent: "center",
        transform: `translateY(${(1 - t) * -40 * u}px)`,
        opacity: t,
        zIndex: 5,
      }}
    >
      <div
        style={{
          background: bg,
          color,
          fontFamily: FONT_HEAD,
          fontWeight: 800,
          fontSize: 62 * u,
          padding: `${6 * u}px ${34 * u}px`,
          borderRadius: 18 * u,
          boxShadow: `0 ${8 * u}px 0 rgba(0,0,0,0.18)`,
          maxWidth: "88%",
          textAlign: "center",
          lineHeight: 1.15,
        }}
      >
        {text}
      </div>
    </div>
  );
};

const Label: React.FC<{
  item: VisualItem;
  u: number;
  width: number;
  align?: "left" | "center" | "right";
  big?: boolean;
  color?: string;
}> = ({ item, u, width, align = "center", big, color = C.ink }) => (
  <div style={{ width, textAlign: align, color }}>
    <div style={{ fontFamily: FONT_HEAD, fontWeight: 800, fontSize: (big ? 58 : 48) * u, lineHeight: 1.1 }}>{item.label}</div>
    {item.detail ? (
      <div style={{ fontFamily: FONT_BODY, fontWeight: 600, fontSize: 34 * u, lineHeight: 1.2, opacity: 0.85, marginTop: 4 * u }}>
        {item.detail}
      </div>
    ) : null}
  </div>
);

// ---------------------------------------------------------------- KNOLLING
// Objects slide in at angles and snap into a neat 90-degree grid on a cutting mat.
export const Knolling: React.FC<DeviceProps> = ({ v, reveal, f, fps, w, h, k }) => {
  const u = (w / 1600) * (k || 1);
  const items = (v as any).items as VisualItem[];
  const n = Math.max(1, items.length);
  const cols = n <= 3 ? n : n <= 4 ? 2 : n <= 6 ? 3 : 4;
  const rows = Math.ceil(n / cols);
  const top = 150 * u;
  const pad = 40 * u;
  const cellW = (w - pad * 2) / cols;
  const cellH = (h - top - pad) / rows;
  const tile = Math.min(cellW, cellH) * 0.62;
  const zoom = interpolate(f, [0, 600], [1.04, 1], clamp);
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", borderRadius: 30 * u, background: C.mat }}>
      <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})` }}>
        <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
          {Array.from({ length: Math.ceil(w / (40 * u)) }).map((_, i) => (
            <line key={"v" + i} x1={i * 40 * u} y1={0} x2={i * 40 * u} y2={h} stroke={C.matLine} strokeWidth={i % 5 === 0 ? 2 : 1} />
          ))}
          {Array.from({ length: Math.ceil(h / (40 * u)) }).map((_, i) => (
            <line key={"h" + i} x1={0} y1={i * 40 * u} x2={w} y2={i * 40 * u} stroke={C.matLine} strokeWidth={i % 5 === 0 ? 2 : 1} />
          ))}
          {Array.from({ length: Math.ceil(w / (20 * u)) }).map((_, i) => (
            <line key={"r" + i} x1={i * 20 * u} y1={h} x2={i * 20 * u} y2={h - (i % 5 === 0 ? 22 : 10) * u} stroke="rgba(255,255,255,0.5)" strokeWidth={2} />
          ))}
        </svg>
        {items.map((it, i) => {
          const start = at(reveal, i);
          const p = pop(f, fps, start, 14);
          const col = i % cols;
          const row = Math.floor(i / cols);
          const lastRowCount = row === rows - 1 ? n - row * cols : cols;
          const rowOffset = ((cols - lastRowCount) * cellW) / 2;
          const cx = pad + rowOffset + col * cellW + cellW / 2;
          const cy = top + row * cellH + cellH / 2 - 10 * u;
          const ang = (rand(it.label + i) - 0.5) * 70;
          const fromX = (rand(i + "x") > 0.5 ? 1 : -1) * w * 0.7;
          const fromY = (rand(i + "y") - 0.5) * h;
          const x = interpolate(p, [0, 1], [cx + fromX, cx]);
          const y = interpolate(p, [0, 1], [cy + fromY, cy]);
          const rot = interpolate(p, [0, 1], [ang, 0]);
          const color = pick(ITEM_COLORS, i);
          if (f < start - 1) return null;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: x - cellW / 2,
                top: y - tile / 2,
                width: cellW,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                transform: `rotate(${rot}deg)`,
              }}
            >
              <div
                style={{
                  width: tile,
                  height: tile * 0.82,
                  background: color,
                  borderRadius: 22 * u,
                  boxShadow: `${10 * u}px ${14 * u}px 0 rgba(0,0,0,0.30)`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  border: `${5 * u}px solid rgba(255,255,255,0.8)`,
                }}
              >
                <Icon name={it.icon} size={tile * 0.46} color={C.ink} stroke={2.2} />
              </div>
              <div
                style={{
                  marginTop: 12 * u,
                  background: "#fff",
                  borderRadius: 10 * u,
                  padding: `${4 * u}px ${14 * u}px`,
                  boxShadow: `0 ${5 * u}px 0 rgba(0,0,0,0.2)`,
                  maxWidth: cellW * 0.95,
                }}
              >
                <Label item={{ label: it.label }} u={u * 0.95} width={undefined as any} />
              </div>
            </div>
          );
        })}
      </div>
      <Title text={v.title} f={f} u={u} />
    </div>
  );
};

// ---------------------------------------------------------------- EXPLODED VIEW
// The topic sits in the centre; its parts fly outward along dashed lines.
export const Exploded: React.FC<DeviceProps> = ({ v, reveal, f, fps, w, h, k }) => {
  const u = (w / 1600) * (k || 1);
  const vv = v as Extract<typeof v, { kind: "exploded" }>;
  const items = vv.items;
  const n = Math.max(1, items.length);
  const cx = w / 2;
  const cy = h / 2 + 50 * u;
  const rx = w * 0.3;
  const ry = h * 0.3;
  const coreP = pop(f, fps, 2, 10);
  const shake = f < (reveal[0] ?? 20) ? Math.sin(f * 2.2) * 3 * u * coreP : 0;
  const coreR = 150 * u;
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", borderRadius: 30 * u, background: "radial-gradient(circle at 50% 55%, #fff7e0, #ffe0a3)" }}>
      <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
        {items.map((it, i) => {
          const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;
          const p = ease(f, at(reveal, i), 16);
          const x = cx + Math.cos(a) * rx * p;
          const y = cy + Math.sin(a) * ry * p;
          return (
            <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke={C.ink} strokeWidth={4 * u} strokeDasharray={`${14 * u} ${10 * u}`} opacity={0.5 * p} />
          );
        })}
        {[0, 1, 2].map((k) => (
          <circle
            key={k}
            cx={cx}
            cy={cy}
            r={coreR * (1.25 + k * 0.35) + ((f * 1.5 + k * 30) % 60) * u}
            fill="none"
            stroke={C.orange}
            strokeWidth={3 * u}
            opacity={0.25}
          />
        ))}
      </svg>
      <div
        style={{
          position: "absolute",
          left: cx - coreR + shake,
          top: cy - coreR,
          width: coreR * 2,
          height: coreR * 2,
          borderRadius: "50%",
          background: C.navy,
          border: `${8 * u}px solid ${C.yellow}`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          transform: `scale(${coreP})`,
          boxShadow: `0 ${14 * u}px 0 rgba(0,0,0,0.25)`,
          zIndex: 3,
        }}
      >
        <Icon name={vv.center?.icon} size={coreR * 0.75} color={C.yellow} stroke={2} />
        <div style={{ color: "#fff", fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 32 * u, textAlign: "center", lineHeight: 1, marginTop: 4 * u, maxWidth: coreR * 1.7 }}>
          {vv.center?.label}
        </div>
      </div>
      {items.map((it, i) => {
        const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;
        const start = at(reveal, i);
        if (f < start - 1) return null;
        const p = pop(f, fps, start, 13);
        const x = cx + Math.cos(a) * rx * p;
        const y = cy + Math.sin(a) * ry * p;
        const cardW = Math.min(520 * u, (w * 0.95) / Math.min(n, 3));
        const color = pick(ITEM_COLORS, i);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x - cardW / 2,
              top: y - 70 * u,
              width: cardW,
              transform: `scale(${0.5 + 0.5 * p}) rotate(${(1 - p) * 25}deg)`,
              background: "#fff",
              borderRadius: 22 * u,
              border: `${5 * u}px solid ${color}`,
              boxShadow: `0 ${10 * u}px 0 rgba(0,0,0,0.2)`,
              padding: `${12 * u}px ${14 * u}px`,
              display: "flex",
              alignItems: "center",
              gap: 12 * u,
              zIndex: 4,
            }}
          >
            <div style={{ minWidth: 70 * u, height: 70 * u, borderRadius: 16 * u, background: color, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Icon name={it.icon} size={44 * u} color={C.ink} />
            </div>
            <Label item={it} u={u * 0.95} width={undefined as any} align="left" />
          </div>
        );
      })}
      <Title text={v.title} f={f} u={u} />
    </div>
  );
};

// ---------------------------------------------------------------- CUTAWAY
// A solid object is sliced open; the front falls away to show the layers inside.
const SHELLS: Record<string, string> = {
  building: "M0 300 L400 60 L800 300 L800 900 L0 900 Z",
  bank: "M0 300 L400 60 L800 300 L800 900 L0 900 Z",
  house: "M40 380 L400 80 L760 380 L760 900 L40 900 Z",
  piggybank: "M80 500 Q80 160 400 160 Q720 160 720 500 Q720 880 400 880 Q80 880 80 500 Z",
  phone: "M150 60 Q150 20 200 20 L600 20 Q650 20 650 60 L650 900 Q650 940 600 940 L200 940 Q150 940 150 900 Z",
  pyramid: "M400 40 L780 900 L20 900 Z",
  box: "M60 120 L740 120 L740 900 L60 900 Z",
};

export const Cutaway: React.FC<DeviceProps> = ({ v, reveal, f, fps, w, h, k }) => {
  const u = (w / 1600) * (k || 1);
  const vv = v as Extract<typeof v, { kind: "cutaway" }>;
  const items = vv.items;
  const n = Math.max(1, items.length);
  const shape = SHELLS[vv.object] || SHELLS.box;
  // object occupies the left 45% of the box
  const tall = h / w > 0.8; // vertical Shorts: smaller object, wider labels
  const objH = h * (tall ? 0.52 : 0.78);
  const scale = objH / 960;
  const ox = w * (tall ? 0.03 : 0.06);
  const oy = tall ? h * 0.24 : h * 0.17;
  const cutStart = Math.max(4, (reveal[0] ?? 30) - 26);
  const cut = ease(f, cutStart, 12); // knife sweep
  const open = ease(f, cutStart + 12, 16); // front panel falls away
  const id = `cut${Math.round(w)}`;
  const layerTop = 140;
  const layerBottom = 900;
  const lh = (layerBottom - layerTop) / n;
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", borderRadius: 30 * u, background: "linear-gradient(180deg,#e8f4ff,#cfe7ff)" }}>
      <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <clipPath id={id}>
            <path d={shape} />
          </clipPath>
        </defs>
        <g transform={`translate(${ox} ${oy}) scale(${scale})`}>
          {/* inside layers */}
          <g clipPath={`url(#${id})`}>
            {items.map((it, i) => (
              <g key={i}>
                <rect x={0} y={layerTop + i * lh} width={800} height={lh} fill={pick(ITEM_COLORS, i)} />
                <rect x={0} y={layerTop + i * lh} width={800} height={8} fill="rgba(0,0,0,0.15)" />
                <text x={400} y={layerTop + i * lh + lh / 2 + 22} textAnchor="middle" fontSize={64} fontWeight={800} fill={C.ink} fontFamily={FONT_HEAD} opacity={ease(f, at(reveal, i), 10)}>
                  {i + 1}
                </text>
              </g>
            ))}
            <rect x={0} y={0} width={800} height={layerTop} fill="#9fb3c8" />
          </g>
          {/* front panel: covers everything, then slides away */}
          <g
            clipPath={`url(#${id})`}
            transform={`translate(${open * 520} ${open * 260}) rotate(${open * 18} 800 900)`}
            opacity={1 - open}
          >
            <rect x={0} y={0} width={800} height={960} fill={C.navy} />
            {Array.from({ length: 6 }).map((_, i) => (
              <rect key={i} x={110 + i * 110} y={360} width={50} height={480} rx={10} fill="rgba(255,255,255,0.18)" />
            ))}
          </g>
          <path d={shape} fill="none" stroke={C.ink} strokeWidth={10} />
          {vv.object === "piggybank" && (
            <g fill="#ffadc6" stroke={C.ink} strokeWidth={8}>
              <rect x={330} y={128} width={140} height={22} rx={10} fill={C.ink} />
              <ellipse cx={724} cy={520} rx={40} ry={60} />
              <path d="M220 190 L260 110 L300 180 Z" />
              <rect x={190} y={860} width={70} height={70} rx={14} />
              <rect x={540} y={860} width={70} height={70} rx={14} />
            </g>
          )}
          {/* knife line */}
          {cut > 0 && open < 0.95 && (
            <line x1={-40} y1={-40 + cut * 0} x2={-40 + cut * 900} y2={-40 + cut * 1000} stroke={C.red} strokeWidth={12} strokeDasharray="30 18" />
          )}
        </g>
        {items.map((it, i) => {
          const t = ease(f, at(reveal, i), 14);
          const ly = oy + (layerTop + i * lh + lh / 2) * scale;
          const lx = ox + 760 * scale;
          return (
            <line key={i} x1={lx} y1={ly} x2={lx + (w * 0.12) * t} y2={ly} stroke={C.ink} strokeWidth={4 * u} strokeDasharray={`${10 * u} ${8 * u}`} opacity={t} />
          );
        })}
      </svg>
      {items.map((it, i) => {
        const start = at(reveal, i);
        if (f < start - 1) return null;
        const t = pop(f, fps, start, 14);
        const ly = oy + (layerTop + i * lh + lh / 2) * scale;
        const lx = ox + 760 * scale + w * 0.13;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: lx,
              top: ly - 44 * u,
              width: w - lx - 40 * u,
              transform: `translateX(${(1 - t) * 60 * u}px)`,
              opacity: t,
              display: "flex",
              alignItems: "center",
              gap: 14 * u,
            }}
          >
            <div style={{ minWidth: 54 * u, height: 54 * u, borderRadius: "50%", background: pick(ITEM_COLORS, i), border: `${4 * u}px solid ${C.ink}`, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 30 * u }}>
              {i + 1}
            </div>
            <Label item={it} u={u * 1.05} width={undefined as any} align="left" />
          </div>
        );
      })}
      <Title text={v.title} f={f} u={u} />
    </div>
  );
};

// ---------------------------------------------------------------- ANATOMY / DISSECTION
// A big labelled diagram of an object, with numbered pins and callouts — like a dissection chart.
type Anchor = [number, number];
const OBJECTS: Record<string, { draw: (u: number) => React.ReactNode; anchors: Anchor[] }> = {
  cheque: {
    anchors: [[640, 70], [280, 160], [300, 235], [690, 235], [180, 320], [640, 350], [400, 440]],
    draw: () => (
      <g>
        <rect x={0} y={0} width={800} height={480} rx={18} fill="#e3f2fd" stroke="#90caf9" strokeWidth={6} />
        <rect x={30} y={30} width={220} height={40} rx={8} fill="#1565c0" />
        {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
          <rect key={i} x={560 + i * 26} y={50} width={22} height={34} fill="#fff" stroke="#90a4ae" strokeWidth={2} />
        ))}
        <line x1={60} y1={170} x2={720} y2={170} stroke="#607d8b" strokeWidth={3} />
        <line x1={60} y1={245} x2={560} y2={245} stroke="#607d8b" strokeWidth={3} />
        <rect x={590} y={205} width={180} height={60} rx={6} fill="#fff" stroke="#607d8b" strokeWidth={3} />
        <text x={605} y={248} fontSize={36} fontWeight={700} fill="#37474f">₹</text>
        <rect x={60} y={300} width={260} height={36} rx={4} fill="#fff" stroke="#90a4ae" strokeWidth={2} />
        <path d="M560 360 q30 -40 60 0 t60 0 t50 -10" stroke="#1a237e" strokeWidth={4} fill="none" />
        <line x1={540} y1={380} x2={760} y2={380} stroke="#607d8b" strokeWidth={3} />
        <rect x={0} y={420} width={800} height={60} fill="#bbdefb" />
        <text x={400} y={462} textAnchor="middle" fontSize={34} letterSpacing={6} fill="#37474f" fontFamily="monospace">⑈123456⑈ 110002005⑆ 000123⑈</text>
      </g>
    ),
  },
  card: {
    anchors: [[150, 200], [400, 290], [200, 400], [560, 400], [690, 90], [690, 200]],
    draw: () => (
      <g>
        <defs>
          <linearGradient id="cardg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#118ab2" />
            <stop offset="1" stopColor="#073b4c" />
          </linearGradient>
        </defs>
        <rect x={0} y={0} width={800} height={500} rx={40} fill="url(#cardg)" />
        <rect x={100} y={150} width={110} height={90} rx={14} fill="#ffd166" />
        <path d="M100 195 H210 M155 150 V240" stroke="#c9a227" strokeWidth={4} />
        <text x={80} y={310} fontSize={50} fill="#fff" fontFamily="monospace" letterSpacing={6}>1234 5678 9012 3456</text>
        <text x={80} y={410} fontSize={34} fill="#fff" fontFamily="sans-serif">A K SHARMA</text>
        <text x={520} y={410} fontSize={34} fill="#fff" fontFamily="monospace">12/30</text>
        <circle cx={660} cy={90} r={38} fill="#ef476f" opacity={0.9} />
        <circle cx={710} cy={90} r={38} fill="#ffd166" opacity={0.85} />
        <path d="M670 180 q20 20 0 40 M690 170 q32 30 0 60 M710 160 q44 40 0 80" stroke="#fff" strokeWidth={6} fill="none" />
      </g>
    ),
  },
  passbook: {
    anchors: [[200, 90], [200, 220], [600, 120], [600, 260], [600, 400], [200, 390]],
    draw: () => (
      <g>
        <rect x={0} y={0} width={800} height={500} rx={16} fill="#2a9d8f" />
        <rect x={20} y={20} width={370} height={460} rx={8} fill="#fffdf5" />
        <rect x={410} y={20} width={370} height={460} rx={8} fill="#fffdf5" />
        <rect x={50} y={60} width={300} height={50} rx={6} fill="#264653" />
        {[0, 1, 2, 3, 4].map((i) => (
          <rect key={i} x={50} y={150 + i * 56} width={300} height={22} rx={4} fill="#e9ecef" />
        ))}
        {Array.from({ length: 9 }).map((_, i) => (
          <line key={i} x1={430} y1={80 + i * 44} x2={760} y2={80 + i * 44} stroke="#ced4da" strokeWidth={3} />
        ))}
        {[530, 620, 700].map((x) => (
          <line key={x} x1={x} y1={60} x2={x} y2={460} stroke="#ced4da" strokeWidth={3} />
        ))}
      </g>
    ),
  },
  form: {
    anchors: [[640, 120], [220, 110], [300, 220], [300, 310], [140, 400], [620, 420]],
    draw: () => (
      <g>
        <rect x={0} y={0} width={800} height={500} rx={14} fill="#fff" stroke="#adb5bd" strokeWidth={5} />
        <rect x={40} y={30} width={460} height={44} rx={6} fill="#ffd166" />
        <rect x={570} y={40} width={150} height={170} rx={8} fill="#e9ecef" stroke="#adb5bd" strokeWidth={4} strokeDasharray="12 8" />
        {[0, 1, 2].map((i) => (
          <g key={i}>
            <rect x={40} y={110 + i * 95} width={160} height={24} rx={4} fill="#dee2e6" />
            <line x1={220} y1={134 + i * 95} x2={520} y2={134 + i * 95} stroke="#868e96" strokeWidth={3} />
          </g>
        ))}
        {[0, 1, 2].map((i) => (
          <rect key={i} x={60 + i * 130} y={385} width={36} height={36} rx={6} fill="#fff" stroke="#495057" strokeWidth={4} />
        ))}
        <path d="M66 402 l10 12 l18 -24" stroke="#06d6a0" strokeWidth={6} fill="none" />
        <path d="M540 440 q30 -40 60 0 t60 0" stroke="#1a237e" strokeWidth={4} fill="none" />
        <line x1={520} y1={460} x2={740} y2={460} stroke="#868e96" strokeWidth={3} />
      </g>
    ),
  },
  building: {
    anchors: [[400, 70], [400, 165], [150, 330], [400, 330], [650, 330], [400, 470]],
    draw: () => (
      <g>
        <path d="M60 140 L400 20 L740 140 Z" fill="#073b4c" />
        <rect x={80} y={140} width={640} height={50} fill="#118ab2" />
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <rect key={i} x={110 + i * 110} y={200} width={50} height={230} fill="#e9ecef" stroke="#adb5bd" strokeWidth={3} />
        ))}
        <rect x={60} y={430} width={680} height={30} fill="#adb5bd" />
        <rect x={30} y={460} width={740} height={30} fill="#868e96" />
        <circle cx={400} cy={85} r={30} fill="#ffd166" />
      </g>
    ),
  },
  phone: {
    anchors: [[400, 70], [400, 170], [300, 290], [500, 290], [400, 400], [400, 470]],
    draw: () => (
      <g>
        <rect x={230} y={0} width={340} height={500} rx={44} fill="#2b2d42" />
        <rect x={250} y={30} width={300} height={430} rx={20} fill="#f8f9fa" />
        <rect x={270} y={50} width={260} height={50} rx={10} fill="#7b5ea7" />
        <rect x={300} y={130} width={200} height={80} rx={12} fill="#06d6a0" />
        {[0, 1, 2, 3].map((i) => (
          <rect key={i} x={270 + (i % 2) * 140} y={240 + Math.floor(i / 2) * 80} width={120} height={60} rx={10} fill="#8ecae6" />
        ))}
        <rect x={300} y={400} width={200} height={40} rx={20} fill="#ef476f" />
        <circle cx={400} cy={478} r={10} fill="#8d99ae" />
      </g>
    ),
  },
  generic: {
    anchors: [[400, 40], [700, 160], [700, 360], [400, 470], [100, 360], [100, 160]],
    draw: () => (
      <g>
        <circle cx={400} cy={250} r={210} fill="#ffe8a3" stroke={C.ink} strokeWidth={8} />
        <circle cx={400} cy={250} r={150} fill="#fff" stroke={C.ink} strokeWidth={4} strokeDasharray="16 12" />
      </g>
    ),
  },
};

export const Anatomy: React.FC<DeviceProps> = ({ v, reveal, f, fps, w, h, k }) => {
  const u = (w / 1600) * (k || 1);
  const vv = v as Extract<typeof v, { kind: "anatomy" }>;
  const obj = OBJECTS[vv.object] || OBJECTS.generic;
  const items = vv.items.slice(0, 7);
  const n = items.length;
  // object in the centre, labels in two columns
  const objW = w * 0.4;
  const s = objW / 800;
  const ox = (w - objW) / 2;
  const oy = h * 0.2 + (h * 0.75 - 500 * s) / 2;
  const enter = pop(f, fps, 0, 14);
  const active = items.reduce((acc, _, i) => (f >= at(reveal, i) ? i : acc), -1);
  const tall = h / w > 0.8;
  if (tall) return <AnatomyTall {...{ v, reveal, f, fps, w, h, k: u / (w / 1600) }} obj={obj} items={items} active={active} />;
  const leftIdx = items.map((_, i) => i).filter((i) => (obj.anchors[i] ? obj.anchors[i][0] : 400) < 400);
  const rightIdx = items.map((_, i) => i).filter((i) => !leftIdx.includes(i));
  const slotY = (k: number, count: number) => h * 0.22 + ((k + 0.5) * (h * 0.74)) / Math.max(count, 1);
  const labelPos = (i: number) => {
    const left = leftIdx.includes(i);
    const list = left ? leftIdx : rightIdx;
    const k = list.indexOf(i);
    return { left, y: slotY(k, list.length) };
  };
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", borderRadius: 30 * u, background: "#f4f1ea" }}>
      <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
        {/* paper texture lines */}
        {Array.from({ length: Math.ceil(h / (34 * u)) }).map((_, i) => (
          <line key={i} x1={0} y1={i * 34 * u} x2={w} y2={i * 34 * u} stroke="rgba(0,0,0,0.04)" strokeWidth={2} />
        ))}
        <g transform={`translate(${ox} ${oy}) scale(${s * (0.8 + 0.2 * enter)})`} opacity={enter}>
          {obj.draw(u)}
          <rect x={-14} y={-14} width={828} height={528} rx={24} fill="none" stroke={C.inkSoft} strokeWidth={3} strokeDasharray="14 10" opacity={0.6} />
        </g>
        {items.map((it, i) => {
          const a = obj.anchors[i] || obj.anchors[i % obj.anchors.length];
          const ax = ox + a[0] * s;
          const ay = oy + a[1] * s;
          const t = ease(f, at(reveal, i), 14);
          const lp = labelPos(i);
          const lx = lp.left ? ox - 30 * u : ox + objW + 30 * u;
          const ex = ax + (lx - ax) * t;
          const ey = ay + (lp.y - ay) * t;
          return (
            <g key={i} opacity={t > 0 ? 1 : 0}>
              <line x1={ax} y1={ay} x2={ex} y2={ey} stroke={C.ink} strokeWidth={4 * u} />
              <circle cx={ax} cy={ay} r={22 * u} fill={i === active ? C.red : C.ink} />
              {i === active && <circle cx={ax} cy={ay} r={(30 + ((f * 2) % 30)) * u} fill="none" stroke={C.red} strokeWidth={4 * u} opacity={0.6} />}
              <text x={ax} y={ay + 9 * u} textAnchor="middle" fontSize={26 * u} fontWeight={800} fill="#fff" fontFamily={FONT_HEAD}>
                {i + 1}
              </text>
            </g>
          );
        })}
      </svg>
      {items.map((it, i) => {
        const start = at(reveal, i);
        if (f < start - 1) return null;
        const t = pop(f, fps, start + 6, 14);
        const lp = labelPos(i);
        const colW = ox - 80 * u;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: lp.left ? 24 * u : ox + objW + 40 * u,
              top: lp.y - 46 * u,
              width: colW,
              opacity: t,
              transform: `translateY(${(1 - t) * 20 * u}px)`,
              background: i === active ? "#fff" : "rgba(255,255,255,0.7)",
              borderLeft: `${8 * u}px solid ${i === active ? C.red : C.inkSoft}`,
              borderRadius: 12 * u,
              padding: `${8 * u}px ${12 * u}px`,
              boxShadow: i === active ? `0 ${6 * u}px 0 rgba(0,0,0,0.15)` : "none",
            }}
          >
            <Label item={{ label: `${i + 1}. ${it.label}`, detail: it.detail }} u={u * 0.92} width={undefined as any} align="left" />
          </div>
        );
      })}
      <Title text={v.title} f={f} u={u} bg={C.navy} color="#fff" />
    </div>
  );
};

// Vertical version: the object on top with numbered pins, the labels as a list below.
const AnatomyTall: React.FC<DeviceProps & { obj: { draw: (u: number) => React.ReactNode; anchors: Anchor[] }; items: VisualItem[]; active: number }> = ({
  v, reveal, f, fps, w, h, k, obj, items, active,
}) => {
  const u = (w / 1600) * (k || 1);
  const objW = w * 0.82;
  const s = objW / 800;
  const ox = (w - objW) / 2;
  const oy = h * 0.13;
  const enter = pop(f, fps, 0, 14);
  const listTop = oy + 500 * s + 30 * u;
  const rowH = (h - listTop - 20 * u) / Math.max(1, items.length);
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", borderRadius: 30 * u, background: "#f4f1ea" }}>
      <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
        <g transform={`translate(${ox} ${oy}) scale(${s * (0.8 + 0.2 * enter)})`} opacity={enter}>
          {obj.draw(u)}
        </g>
        {items.map((it, i) => {
          const a = obj.anchors[i] || obj.anchors[i % obj.anchors.length];
          const t = ease(f, at(reveal, i), 10);
          if (t <= 0) return null;
          const ax = ox + a[0] * s;
          const ay = oy + a[1] * s;
          return (
            <g key={i}>
              <circle cx={ax} cy={ay} r={26 * u} fill={i === active ? C.red : C.ink} transform={`translate(${ax} ${ay}) scale(${t}) translate(${-ax} ${-ay})`} />
              {i === active && <circle cx={ax} cy={ay} r={(34 + ((f * 2) % 30)) * u} fill="none" stroke={C.red} strokeWidth={4 * u} opacity={0.6} />}
              <text x={ax} y={ay + 10 * u} textAnchor="middle" fontSize={30 * u} fontWeight={800} fill="#fff" fontFamily={FONT_HEAD}>{i + 1}</text>
            </g>
          );
        })}
      </svg>
      {items.map((it, i) => {
        const start = at(reveal, i);
        if (f < start - 1) return null;
        const t = pop(f, fps, start + 4, 14);
        return (
          <div key={i} style={{ position: "absolute", left: 24 * u, right: 24 * u, top: listTop + i * rowH, opacity: t, transform: `translateX(${(1 - t) * 40 * u}px)`, display: "flex", alignItems: "center", gap: 14 * u }}>
            <div style={{ minWidth: 50 * u, height: 50 * u, borderRadius: "50%", background: i === active ? C.red : C.ink, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 30 * u }}>{i + 1}</div>
            <Label item={it} u={u * 0.85} width={undefined as any} align="left" />
          </div>
        );
      })}
      <Title text={v.title} f={f} u={u} bg={C.navy} color="#fff" />
    </div>
  );
};

// ---------------------------------------------------------------- STAT (big number)
const parseNum = (s: string) => {
  const m = s.match(/^([^\d]*)([\d,]*\.?\d+)(.*)$/);
  if (!m) return null;
  return { pre: m[1], num: parseFloat(m[2].replace(/,/g, "")), dec: (m[2].split(".")[1] || "").length, post: m[3], comma: m[2].includes(",") };
};

export const Stat: React.FC<DeviceProps> = ({ v, f, fps, w, h, k }) => {
  const u = (w / 1600) * (k || 1);
  const vv = v as Extract<typeof v, { kind: "stat" }>;
  const p = parseNum(vv.value);
  const t = interpolate(f, [6, 40], [0, 1], { ...clamp, easing: (x) => 1 - Math.pow(1 - x, 3) });
  let shown = vv.value;
  if (p) {
    const val = p.num * t;
    const txt = p.comma ? val.toLocaleString("en-IN", { maximumFractionDigits: p.dec, minimumFractionDigits: p.dec }) : val.toFixed(p.dec);
    shown = `${p.pre}${txt}${p.post}`;
  }
  const s = pop(f, fps, 2, 9);
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", borderRadius: 30 * u, background: C.navy }}>
      <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
        {Array.from({ length: 18 }).map((_, i) => {
          const a = (i * 20 + f * 0.4) * (Math.PI / 180);
          const r = Math.max(w, h);
          return (
            <path
              key={i}
              d={`M${w / 2} ${h / 2 + 30 * u} L${w / 2 + Math.cos(a) * r} ${h / 2 + Math.sin(a) * r} L${w / 2 + Math.cos(a + 0.12) * r} ${h / 2 + Math.sin(a + 0.12) * r} Z`}
              fill="rgba(255,255,255,0.05)"
            />
          );
        })}
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", paddingTop: 80 * u }}>
        {vv.icon && (
          <div style={{ transform: `scale(${s})`, marginBottom: 10 * u }}>
            <Icon name={vv.icon} size={110 * u} color={C.yellow} />
          </div>
        )}
        <div style={{ fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 210 * u, color: C.yellow, lineHeight: 1, transform: `scale(${0.6 + 0.4 * s})`, textShadow: `0 ${10 * u}px 0 rgba(0,0,0,0.3)` }}>
          {shown}
        </div>
        <div style={{ fontFamily: FONT_HEAD, fontWeight: 700, fontSize: 56 * u, color: "#fff", marginTop: 16 * u, textAlign: "center", maxWidth: "85%", opacity: ease(f, 20, 12) }}>
          {vv.label}
        </div>
        {vv.note && (
          <div style={{ fontFamily: FONT_BODY, fontSize: 30 * u, color: "rgba(255,255,255,0.75)", marginTop: 14 * u, opacity: ease(f, 30, 12) }}>
            {vv.note}
          </div>
        )}
      </div>
      <Title text={v.title} f={f} u={u} />
    </div>
  );
};

// ---------------------------------------------------------------- TIMELINE
export const Timeline: React.FC<DeviceProps> = ({ v, reveal, f, fps, w, h, k }) => {
  const u = (w / 1600) * (k || 1);
  const items = (v as any).items as VisualItem[];
  const n = Math.max(1, items.length);
  const y = h * 0.56;
  const x0 = w * 0.08;
  const x1 = w * 0.92;
  const lastStart = at(reveal, n - 1);
  const grow = interpolate(f, [0, lastStart + 10], [0, 1], clamp);
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", borderRadius: 30 * u, background: "linear-gradient(180deg,#fff8e7,#ffe9c2)" }}>
      <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
        <line x1={x0} y1={y} x2={x0 + (x1 - x0) * grow} y2={y} stroke={C.ink} strokeWidth={10 * u} strokeLinecap="round" />
      </svg>
      {items.map((it, i) => {
        const start = at(reveal, i);
        if (f < start - 1) return null;
        const p = pop(f, fps, start, 12);
        const x = n === 1 ? (x0 + x1) / 2 : x0 + ((x1 - x0) * i) / (n - 1);
        const up = i % 2 === 0;
        const cw = Math.min(480 * u, ((x1 - x0) / Math.max(n - 1, 1)) * 0.95);
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: x - 26 * u, top: y - 26 * u, width: 52 * u, height: 52 * u, borderRadius: "50%", background: pick(ITEM_COLORS, i), border: `${6 * u}px solid ${C.ink}`, transform: `scale(${p})` }} />
            <div
              style={{
                position: "absolute",
                left: Math.max(10 * u, Math.min(w - cw - 10 * u, x - cw / 2)),
                top: up ? y - 330 * u : y + 50 * u,
                width: cw,
                textAlign: "center",
                opacity: p,
                transform: `translateY(${(1 - p) * (up ? 30 : -30) * u}px)`,
              }}
            >
              <div style={{ fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 92 * u, color: C.red, lineHeight: 1 }}>{it.year || ""}</div>
              <Label item={{ label: it.label, detail: it.detail }} u={u * 1.05} width={cw} />
            </div>
          </React.Fragment>
        );
      })}
      <Title text={v.title} f={f} u={u} />
    </div>
  );
};

// ---------------------------------------------------------------- COMPARE
export const Compare: React.FC<DeviceProps> = ({ v, reveal, f, fps, w, h, k }) => {
  const u = (w / 1600) * (k || 1);
  const vv = v as Extract<typeof v, { kind: "compare" }>;
  const rows = Math.max(vv.left.points.length, vv.right.points.length);
  const colW = w * 0.42;
  const vs = pop(f, fps, 6, 8);
  const col = (side: "left" | "right", data: { title: string; points: string[] }, color: string) => (
    <div style={{ position: "absolute", top: 150 * u, bottom: 30 * u, [side]: w * 0.04, width: colW, background: "#fff", borderRadius: 26 * u, borderTop: `${16 * u}px solid ${color}`, boxShadow: `0 ${10 * u}px 0 rgba(0,0,0,0.15)`, padding: 24 * u, boxSizing: "border-box" } as React.CSSProperties}>
      <div style={{ fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 52 * u, color: C.ink, textAlign: "center", marginBottom: 14 * u }}>{data.title}</div>
      {data.points.map((p, i) => {
        const idx = side === "left" ? i * 2 : i * 2 + 1;
        const start = at(reveal, idx, 20);
        const t = ease(f, start, 12);
        return (
          <div key={i} style={{ display: "flex", gap: 12 * u, alignItems: "flex-start", marginTop: 14 * u, opacity: t, transform: `translateX(${(1 - t) * (side === "left" ? -40 : 40) * u}px)` }}>
            <div style={{ minWidth: 20 * u, height: 20 * u, borderRadius: "50%", background: color, marginTop: 14 * u }} />
            <div style={{ fontFamily: FONT_BODY, fontWeight: 600, fontSize: 46 * u, color: C.ink, lineHeight: 1.25 }}>{p}</div>
          </div>
        );
      })}
    </div>
  );
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", borderRadius: 30 * u, background: "linear-gradient(90deg,#d8f3ff,#ffe5ec)" }}>
      {col("left", vv.left, C.teal)}
      {col("right", vv.right, C.red)}
      <div style={{ position: "absolute", left: w / 2 - 70 * u, top: h / 2 - 20 * u, width: 140 * u, height: 140 * u, borderRadius: "50%", background: C.yellow, border: `${8 * u}px solid ${C.ink}`, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 60 * u, transform: `scale(${vs}) rotate(${(1 - vs) * 90}deg)` }}>
        VS
      </div>
      <Title text={v.title} f={f} u={u} />
    </div>
  );
};

// ---------------------------------------------------------------- STEPS
export const Steps: React.FC<DeviceProps> = ({ v, reveal, f, fps, w, h, k }) => {
  const u = (w / 1600) * (k || 1);
  const items = (v as any).items as VisualItem[];
  const n = Math.max(1, items.length);
  const top = 150 * u;
  const rowH = (h - top - 30 * u) / n;
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", borderRadius: 30 * u, background: "linear-gradient(180deg,#f0fff4,#d8f3dc)" }}>
      {items.map((it, i) => {
        const start = at(reveal, i);
        if (f < start - 1) return null;
        const p = pop(f, fps, start, 13);
        const done = i < items.length && f > at(reveal, i + 1, 9999);
        return (
          <div key={i} style={{ position: "absolute", left: w * 0.06 + (i % 2) * w * 0.06, top: top + i * rowH, width: w * 0.82, height: rowH * 0.86, display: "flex", alignItems: "center", gap: 20 * u, opacity: p, transform: `translateX(${(1 - p) * -80 * u}px)` }}>
            <div style={{ minWidth: Math.min(90 * u, rowH * 0.8), height: Math.min(90 * u, rowH * 0.8), borderRadius: "50%", background: done ? C.green : pick(ITEM_COLORS, i), border: `${6 * u}px solid ${C.ink}`, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 46 * u }}>
              {done ? "✓" : i + 1}
            </div>
            <div style={{ background: "#fff", borderRadius: 18 * u, padding: `${10 * u}px ${20 * u}px`, boxShadow: `0 ${6 * u}px 0 rgba(0,0,0,0.12)`, display: "flex", alignItems: "center", gap: 16 * u, flex: 1 }}>
              {it.icon && <Icon name={it.icon} size={50 * u} />}
              <Label item={it} u={u * 1.0} width={undefined as any} align="left" />
            </div>
          </div>
        );
      })}
      <Title text={v.title} f={f} u={u} />
    </div>
  );
};

// ---------------------------------------------------------------- KEY FACTS (Exam Corner)
export const KeyFacts: React.FC<DeviceProps> = ({ v, reveal, f, fps, w, h, k }) => {
  const u = (w / 1600) * (k || 1);
  const items = (v as any).items as VisualItem[];
  const n = Math.max(1, items.length);
  const top = 160 * u;
  const rowH = Math.min(160 * u, (h - top - 30 * u) / n);
  const stamp = pop(f, fps, 8, 8);
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", borderRadius: 30 * u, background: "#fffef6" }}>
      <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
        {Array.from({ length: Math.ceil(h / (46 * u)) }).map((_, i) => (
          <line key={i} x1={0} y1={i * 46 * u} x2={w} y2={i * 46 * u} stroke="#cfe3ff" strokeWidth={2} />
        ))}
        <line x1={110 * u} y1={0} x2={110 * u} y2={h} stroke="#ffadad" strokeWidth={4} />
      </svg>
      {items.map((it, i) => {
        const start = at(reveal, i);
        if (f < start - 1) return null;
        const t = ease(f, start, 10);
        const hl = ease(f, start + 6, 18);
        return (
          <div key={i} style={{ position: "absolute", left: 150 * u, top: top + i * rowH, width: w - 330 * u, opacity: t, display: "flex", alignItems: "center", gap: 16 * u }}>
            <div style={{ fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 44 * u, color: C.red }}>★</div>
            <div style={{ position: "relative" }}>
              <div style={{ position: "absolute", left: -8 * u, top: "35%", height: "55%", width: `calc(${hl * 100}% + ${16 * u}px)`, background: "rgba(255,210,63,0.7)", borderRadius: 8 * u }} />
              <div style={{ position: "relative", fontFamily: FONT_BODY, fontWeight: 700, fontSize: 52 * u, color: C.ink, lineHeight: 1.2 }}>
                {it.label}
                {it.detail ? <span style={{ fontWeight: 500, opacity: 0.8 }}> — {it.detail}</span> : null}
              </div>
            </div>
          </div>
        );
      })}
      <div style={{ position: "absolute", right: 30 * u, bottom: 30 * u, transform: `rotate(-12deg) scale(${stamp})`, border: `${6 * u}px solid ${C.red}`, color: C.red, borderRadius: 16 * u, padding: `${6 * u}px ${18 * u}px`, fontFamily: FONT_HEAD, fontWeight: 800, fontSize: 34 * u, background: "rgba(255,255,255,0.8)" }}>
        EXAM ALERT
      </div>
      <Title text={v.title} f={f} u={u} bg={C.red} color="#fff" />
    </div>
  );
};

export const Device: React.FC<DeviceProps> = (p) => {
  switch (p.v.kind) {
    case "knolling":
      return <Knolling {...p} />;
    case "exploded":
      return <Exploded {...p} />;
    case "cutaway":
      return <Cutaway {...p} />;
    case "anatomy":
      return <Anatomy {...p} />;
    case "stat":
      return <Stat {...p} />;
    case "timeline":
      return <Timeline {...p} />;
    case "compare":
      return <Compare {...p} />;
    case "steps":
      return <Steps {...p} />;
    case "keyfacts":
      return <KeyFacts {...p} />;
    default:
      return null;
  }
};
