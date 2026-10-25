import React from "react";

// Flat illustrated backgrounds. Drawn on a 1920x1080 canvas; for vertical
// Shorts the centre of the scene is kept (slice), so key details sit centrally.

type P = { width: number; height: number; frame: number };

const Svg: React.FC<{ width: number; height: number; children: React.ReactNode }> = ({ width, height, children }) => (
  <svg
    viewBox="0 0 1920 1080"
    width={width}
    height={height}
    preserveAspectRatio="xMidYMax slice"
    style={{ position: "absolute", inset: 0 }}
  >
    {children}
  </svg>
);

const Floor: React.FC<{ color: string; line: string }> = ({ color, line }) => (
  <g>
    <rect x={0} y={820} width={1920} height={260} fill={color} />
    {Array.from({ length: 12 }).map((_, i) => (
      <line key={i} x1={i * 180 - 60} y1={820} x2={i * 180 - 260} y2={1080} stroke={line} strokeWidth={4} />
    ))}
    <rect x={0} y={812} width={1920} height={14} fill={line} />
  </g>
);

const Plant: React.FC<{ x: number; y: number; s?: number }> = ({ x, y, s = 1 }) => (
  <g transform={`translate(${x} ${y}) scale(${s})`}>
    <path d="M-40 0 L40 0 L30 90 L-30 90 Z" fill="#c8553d" />
    {[-50, -20, 10, 40].map((a, i) => (
      <ellipse key={i} cx={a * 0.8} cy={-60 - (i % 2) * 30} rx={26} ry={70} fill={i % 2 ? "#2a9d8f" : "#52b788"} transform={`rotate(${a} 0 0)`} />
    ))}
  </g>
);

const Window: React.FC<{ x: number; y: number; w: number; h: number; sky?: string }> = ({ x, y, w, h, sky = "#bde0fe" }) => (
  <g>
    <rect x={x - 14} y={y - 14} width={w + 28} height={h + 28} rx={10} fill="#e9d8a6" />
    <rect x={x} y={y} width={w} height={h} fill={sky} />
    <circle cx={x + w * 0.75} cy={y + h * 0.3} r={Math.min(w, h) * 0.12} fill="#ffe066" />
    <path d={`M${x} ${y + h * 0.75} Q${x + w * 0.3} ${y + h * 0.55} ${x + w * 0.6} ${y + h * 0.72} T${x + w} ${y + h * 0.68} L${x + w} ${y + h} L${x} ${y + h} Z`} fill="#95d5b2" />
    <line x1={x + w / 2} y1={y} x2={x + w / 2} y2={y + h} stroke="#e9d8a6" strokeWidth={12} />
    <line x1={x} y1={y + h / 2} x2={x + w} y2={y + h / 2} stroke="#e9d8a6" strokeWidth={12} />
  </g>
);

const Classroom: React.FC<P> = ({ width, height }) => (
  <Svg width={width} height={height}>
    <rect width={1920} height={1080} fill="#e7f2ef" />
    <rect y={600} width={1920} height={220} fill="#cfe5df" />
    <rect x={520} y={150} width={880} height={430} rx={18} fill="#6b4f3a" />
    <rect x={545} y={175} width={830} height={380} rx={8} fill="#2f5d50" />
    <g stroke="rgba(255,255,255,0.55)" strokeWidth={8} strokeLinecap="round" fill="none">
      <path d="M610 250 L900 250" />
      <path d="M610 320 L1080 320" />
      <path d="M610 390 L980 390" />
      <path d="M1180 260 l40 40 l60 -80" />
      <circle cx={1220} cy={430} r={50} />
    </g>
    <rect x={560} y={560} width={800} height={18} fill="#8d6e53" />
    <Window x={1540} y={170} w={260} h={320} />
    <g>
      <rect x={140} y={200} width={220} height={290} rx={10} fill="#ffd166" />
      <rect x={170} y={235} width={160} height={24} rx={6} fill="#fff" />
      <rect x={170} y={280} width={120} height={18} rx={6} fill="#fff8" />
      <rect x={170} y={320} width={140} height={18} rx={6} fill="#fff8" />
      <circle cx={250} cy={420} r={40} fill="#ef476f" />
    </g>
    <Floor color="#d9b38c" line="#c49a72" />
    <Plant x={1760} y={730} s={1.2} />
  </Svg>
);

const Bank: React.FC<P> = ({ width, height }) => (
  <Svg width={width} height={height}>
    <rect width={1920} height={1080} fill="#e8f1fb" />
    {Array.from({ length: 7 }).map((_, i) => (
      <rect key={i} x={120 + i * 260} y={0} width={40} height={820} fill="#d6e6f7" />
    ))}
    <rect x={660} y={110} width={600} height={120} rx={20} fill="#073b4c" />
    <text x={960} y={196} textAnchor="middle" fontSize={78} fontWeight={800} fill="#ffd23f" fontFamily="'Baloo 2', sans-serif">
      बैंक  ·  BANK
    </text>
    <circle cx={1500} cy={170} r={60} fill="#fff" stroke="#073b4c" strokeWidth={10} />
    <line x1={1500} y1={170} x2={1500} y2={130} stroke="#073b4c" strokeWidth={8} strokeLinecap="round" />
    <line x1={1500} y1={170} x2={1530} y2={185} stroke="#073b4c" strokeWidth={8} strokeLinecap="round" />
    <rect x={0} y={520} width={1920} height={300} fill="#118ab2" />
    <rect x={0} y={500} width={1920} height={30} fill="#0b6e8f" />
    {Array.from({ length: 5 }).map((_, i) => (
      <g key={i}>
        <rect x={150 + i * 360} y={300} width={300} height={210} fill="rgba(255,255,255,0.55)" stroke="#9cc5e0" strokeWidth={6} />
        <rect x={250 + i * 360} y={470} width={100} height={30} rx={6} fill="#ffd23f" />
        <text x={300 + i * 360} y={493} textAnchor="middle" fontSize={22} fontWeight={700} fill="#073b4c" fontFamily="sans-serif">
          {i + 1}
        </text>
      </g>
    ))}
    <Floor color="#c9d6df" line="#b5c4cf" />
    <Plant x={90} y={730} />
  </Svg>
);

const Village: React.FC<P> = ({ width, height, frame }) => (
  <Svg width={width} height={height}>
    <defs>
      <linearGradient id="vsky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#8ecae6" />
        <stop offset="1" stopColor="#e0f4ff" />
      </linearGradient>
    </defs>
    <rect width={1920} height={1080} fill="url(#vsky)" />
    <circle cx={1560} cy={190} r={90} fill="#ffd166" />
    {[0, 1, 2].map((i) => (
      <g key={i} transform={`translate(${((frame * 0.4 + i * 700) % 2300) - 300} ${120 + i * 50})`}>
        <ellipse cx={0} cy={0} rx={90} ry={34} fill="#fff" />
        <ellipse cx={60} cy={-16} rx={60} ry={30} fill="#fff" />
      </g>
    ))}
    <path d="M0 560 Q300 420 640 540 T1300 520 T1920 540 L1920 820 L0 820 Z" fill="#74c69d" />
    <path d="M0 640 Q500 560 960 640 T1920 620 L1920 820 L0 820 Z" fill="#52b788" />
    {Array.from({ length: 9 }).map((_, i) => (
      <path key={i} d={`M${-200 + i * 260} 820 L${100 + i * 220} 660`} stroke="#40916c" strokeWidth={10} />
    ))}
    <g transform="translate(1250 430)">
      <rect x={0} y={90} width={300} height={200} fill="#e9c46a" />
      <path d="M-40 100 L150 -20 L340 100 Z" fill="#bc6c25" />
      <rect x={115} y={170} width={70} height={120} fill="#6f4518" />
      <rect x={30} y={140} width={60} height={50} fill="#8ecae6" />
    </g>
    <g transform="translate(320 360)">
      <rect x={-18} y={120} width={36} height={340} fill="#7f5539" />
      <circle cx={0} cy={80} r={130} fill="#2d6a4f" />
      <circle cx={-90} cy={140} r={90} fill="#40916c" />
      <circle cx={100} cy={140} r={90} fill="#40916c" />
    </g>
    <rect x={0} y={820} width={1920} height={260} fill="#d4a373" />
    <rect x={0} y={812} width={1920} height={14} fill="#bc8a5f" />
  </Svg>
);

const Shop: React.FC<P> = ({ width, height }) => (
  <Svg width={width} height={height}>
    <rect width={1920} height={1080} fill="#fff1e6" />
    <g>
      {Array.from({ length: 12 }).map((_, i) => (
        <rect key={i} x={i * 160} y={0} width={160} height={120} fill={i % 2 ? "#ef476f" : "#fff"} />
      ))}
      <path d={`M0 120 ${Array.from({ length: 13 }).map((_, i) => `Q${i * 160 + 80} 170 ${(i + 1) * 160} 120`).join(" ")}`} fill="#ef476f" />
    </g>
    {[0, 1, 2].map((r) => (
      <g key={r}>
        <rect x={180} y={260 + r * 170} width={1560} height={20} fill="#9c6644" />
        {Array.from({ length: 14 }).map((_, i) => {
          const colors = ["#ffd166", "#06d6a0", "#118ab2", "#ef476f", "#f4a261", "#8338ec"];
          const h = 70 + ((i * 37 + r * 11) % 50);
          return (
            <rect key={i} x={200 + i * 108} y={260 + r * 170 - h} width={80} height={h} rx={10} fill={colors[(i + r) % colors.length]} />
          );
        })}
      </g>
    ))}
    <rect x={0} y={640} width={1920} height={180} fill="#b08968" />
    <rect x={0} y={630} width={1920} height={20} fill="#7f5539" />
    <Floor color="#e6ccb2" line="#d5b394" />
  </Svg>
);

const HomeRoom: React.FC<P> = ({ width, height }) => (
  <Svg width={width} height={height}>
    <rect width={1920} height={1080} fill="#ffe8d6" />
    <Window x={760} y={160} w={400} h={330} />
    <path d="M720 140 L700 560 L800 560 L780 140 Z" fill="#e76f51" />
    <path d="M1200 140 L1220 560 L1120 560 L1140 140 Z" fill="#e76f51" />
    <rect x={700} y={130} width={520} height={20} rx={10} fill="#9c6644" />
    <g>
      <rect x={210} y={200} width={170} height={210} rx={8} fill="#fff" stroke="#ddd" strokeWidth={4} />
      <rect x={210} y={200} width={170} height={50} rx={8} fill="#ef476f" />
      {Array.from({ length: 12 }).map((_, i) => (
        <rect key={i} x={225 + (i % 4) * 38} y={270 + Math.floor(i / 4) * 40} width={26} height={26} rx={4} fill="#eee" />
      ))}
    </g>
    <rect x={1380} y={520} width={420} height={160} rx={40} fill="#457b9d" />
    <rect x={1360} y={460} width={460} height={110} rx={50} fill="#5a8fb5" />
    <Floor color="#ddb892" line="#cfa77e" />
    <Plant x={1840} y={730} />
  </Svg>
);

const Office: React.FC<P> = ({ width, height }) => (
  <Svg width={width} height={height}>
    <rect width={1920} height={1080} fill="#edf2f4" />
    <rect x={240} y={150} width={640} height={380} rx={16} fill="#fff" stroke="#8d99ae" strokeWidth={8} />
    <polyline points="300,470 420,400 520,430 640,300 760,330 840,220" fill="none" stroke="#06d6a0" strokeWidth={14} strokeLinecap="round" />
    {[0, 1, 2, 3].map((i) => (
      <rect key={i} x={320 + i * 140} y={470 - (i + 1) * 50} width={70} height={(i + 1) * 50} fill="#8ecae6" opacity={0.6} />
    ))}
    <Window x={1250} y={170} w={460} h={330} sky="#cde7ff" />
    <rect x={1100} y={600} width={700} height={40} rx={10} fill="#8d6e63" />
    <rect x={1300} y={470} width={260} height={150} rx={12} fill="#2b2d42" />
    <rect x={1315} y={485} width={230} height={115} rx={6} fill="#8ecae6" />
    <Floor color="#cdd5db" line="#b8c2ca" />
    <Plant x={120} y={730} s={1.1} />
  </Svg>
);

const Studio: React.FC<P & { a?: string; b?: string }> = ({ width, height, frame, a = "#fff7e6", b = "#ffe3b3" }) => (
  <Svg width={width} height={height}>
    <defs>
      <radialGradient id="stg" cx="0.5" cy="0.45" r="0.8">
        <stop offset="0" stopColor={a} />
        <stop offset="1" stopColor={b} />
      </radialGradient>
    </defs>
    <rect width={1920} height={1080} fill="url(#stg)" />
    {Array.from({ length: 40 }).map((_, i) => (
      <circle
        key={i}
        cx={(i * 211) % 1920}
        cy={((i * 97) % 1080 + frame * 0.3 * ((i % 3) + 1)) % 1080}
        r={4 + (i % 4) * 3}
        fill="rgba(255,140,66,0.10)"
      />
    ))}
  </Svg>
);

export const SETTINGS: Record<string, React.FC<P>> = {
  classroom: Classroom,
  bank: Bank,
  village: Village,
  shop: Shop,
  home: HomeRoom,
  office: Office,
  studio: Studio,
};

export const Setting: React.FC<P & { name?: string }> = ({ name = "studio", ...p }) => {
  const Comp = SETTINGS[name] || Studio;
  return <Comp {...p} />;
};
