import React from "react";
import { CharacterLook, Emotion, Gesture } from "../types";
import { rand } from "../lib/anim";

// A friendly flat-style 2D cartoon person drawn entirely in SVG, so every
// character looks exactly the same in every video. viewBox is 400 x 900.

type Props = {
  look: CharacterLook;
  emotion?: Emotion;
  gesture?: Gesture;
  mouth?: number; // 0..1 how open the mouth is (from the voice loudness)
  frame: number;
  seed?: string;
  height: number; // rendered height in px
  facing?: 1 | -1;
  talking?: boolean;
  style?: React.CSSProperties;
};

const deg = (d: number) => (d * Math.PI) / 180;

const ARM_POSES: Record<Gesture, { r: [number, number]; l: [number, number] }> = {
  none: { r: [12, -8], l: [12, -8] },
  point: { r: [105, -15], l: [10, -5] },
  raise: { r: [160, 12], l: [12, -8] },
  think: { r: [22, -168], l: [28, -70] },
  wave: { r: [150, 25], l: [12, -8] },
  explain: { r: [38, -72], l: [38, -72] },
  thumbs: { r: [28, -118], l: [12, -8] },
};

const darken = (hex: string, amt = 0.25) => {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  const r = Math.max(0, Math.round(((n >> 16) & 255) * (1 - amt)));
  const g = Math.max(0, Math.round(((n >> 8) & 255) * (1 - amt)));
  const b = Math.max(0, Math.round((n & 255) * (1 - amt)));
  return `rgb(${r},${g},${b})`;
};

const arm = (sx: number, sy: number, a1: number, a2: number, side: 1 | -1) => {
  const L1 = 118;
  const L2 = 108;
  const ex = sx + side * Math.sin(deg(a1)) * L1;
  const ey = sy + Math.cos(deg(a1)) * L1;
  const hx = ex + side * Math.sin(deg(a1 + a2)) * L2;
  const hy = ey + Math.cos(deg(a1 + a2)) * L2;
  return { ex, ey, hx, hy };
};

export const Character: React.FC<Props> = ({
  look,
  emotion = "neutral",
  gesture = "none",
  mouth = 0,
  frame,
  seed = "x",
  height,
  facing = 1,
  talking = false,
  style,
}) => {
  const s = rand(seed);
  // gentle idle movement
  const bob = Math.sin((frame + s * 100) / 16) * (talking ? 4 : 2.5);
  const sway = Math.sin((frame + s * 50) / 37) * 1.2;
  // blinking: closed for 4 frames roughly every 3-5 seconds
  const period = 110 + Math.floor(s * 50);
  const blink = (frame + Math.floor(s * period)) % period < 4;

  const pose = ARM_POSES[gesture] || ARM_POSES.none;
  let rA = [...pose.r] as [number, number];
  let lA = [...pose.l] as [number, number];
  if (gesture === "wave") rA = [rA[0], rA[1] + Math.sin(frame / 4) * 22];
  if (talking && (gesture === "explain" || gesture === "none")) {
    rA = [rA[0] + Math.sin(frame / 7) * 6, rA[1] + Math.sin(frame / 5) * 8];
    lA = [lA[0] + Math.cos(frame / 8) * 5, lA[1] + Math.cos(frame / 6) * 6];
  }

  const skin = look.skin;
  const skinD = darken(skin, 0.18);
  const top = look.top;
  const topD = darken(top, 0.22);
  const ink = "#2b2118";
  const isSaree = look.topStyle === "saree";
  const isKurta = look.topStyle === "kurta";
  const pants =
    look.topStyle === "tshirt" ? "#3c5a8a" : isKurta ? "#f3ead8" : look.topStyle === "blazer" ? darken(top, 0.1) : "#4a4a55";

  const R = arm(292, 335, rA[0], rA[1], 1);
  const Lr = arm(108, 335, lA[0], lA[1], -1);
  const sleeveFull = !(look.topStyle === "tshirt" || isSaree);

  const widthPx = (height * 400) / 900;
  const ey = 192;
  const eyeRy = blink ? 1.6 : emotion === "shocked" ? 20 : emotion === "excited" ? 18 : 16;

  // ---- eyebrows per emotion
  const brows: Record<string, [string, string]> = {
    neutral: ["M148 160 Q164 153 180 159", "M220 159 Q236 153 252 160"],
    happy: ["M148 155 Q164 146 180 153", "M220 153 Q236 146 252 155"],
    excited: ["M148 148 Q164 136 180 145", "M220 145 Q236 136 252 148"],
    curious: ["M148 160 Q164 154 180 160", "M220 148 Q236 136 252 146"],
    thinking: ["M148 158 L180 162", "M220 146 Q236 138 252 148"],
    worried: ["M148 162 L180 150", "M220 150 L252 162"],
    shocked: ["M146 146 Q164 130 182 142", "M218 142 Q236 130 254 146"],
    proud: ["M148 154 L180 160", "M220 160 L252 154"],
  };
  const [bl, br] = brows[emotion] || brows.neutral;

  // ---- mouth
  const open = Math.max(0, Math.min(1, mouth));
  const showOpen = talking && open > 0.08;
  let mouthEl: React.ReactNode;
  if (showOpen) {
    const ry = 4 + open * 15;
    mouthEl = (
      <g>
        <ellipse cx={200} cy={250} rx={15 + open * 3} ry={ry} fill="#5a1f1f" />
        <ellipse cx={200} cy={250 + ry * 0.45} rx={9} ry={Math.max(2, ry * 0.4)} fill="#e0707a" />
        <rect x={188} y={250 - ry} width={24} height={Math.min(5, ry * 0.5)} rx={2} fill="#fff" />
      </g>
    );
  } else if (emotion === "happy" || emotion === "proud") {
    mouthEl = <path d="M174 242 Q200 270 226 242 Q200 258 174 242 Z" fill="#5a1f1f" />;
  } else if (emotion === "excited") {
    mouthEl = (
      <g>
        <path d="M170 238 Q200 284 230 238 Z" fill="#5a1f1f" />
        <path d="M174 239 L226 239 L222 246 L178 246 Z" fill="#fff" />
      </g>
    );
  } else if (emotion === "shocked") {
    mouthEl = <ellipse cx={200} cy={254} rx={13} ry={17} fill="#5a1f1f" />;
  } else if (emotion === "curious") {
    mouthEl = <ellipse cx={204} cy={250} rx={7} ry={6} fill="#5a1f1f" />;
  } else if (emotion === "worried") {
    mouthEl = <path d="M182 256 Q200 244 218 256" stroke="#5a1f1f" strokeWidth={5} fill="none" strokeLinecap="round" />;
  } else if (emotion === "thinking") {
    mouthEl = <path d="M186 252 L216 246" stroke="#5a1f1f" strokeWidth={5} fill="none" strokeLinecap="round" />;
  } else {
    mouthEl = <path d="M180 247 Q200 258 220 247" stroke="#5a1f1f" strokeWidth={5} fill="none" strokeLinecap="round" />;
  }

  // ---- hair (front) and back-hair
  const hairCol = look.hair;
  let hairFront: React.ReactNode = null;
  let hairBack: React.ReactNode = null;
  switch (look.hairStyle) {
    case "short":
      hairFront = <path d="M106 190 Q100 92 200 84 Q300 92 294 190 Q288 128 200 122 Q112 128 106 190 Z" fill={hairCol} />;
      break;
    case "side_part":
      hairFront = (
        <path d="M106 192 Q98 90 200 82 Q302 90 294 192 Q290 132 232 118 Q190 140 150 128 Q118 140 106 192 Z" fill={hairCol} />
      );
      break;
    case "spiky":
      hairFront = (
        <path
          d="M106 180 L116 112 L144 126 L158 78 L184 112 L204 70 L226 108 L250 78 L262 118 L288 104 L294 180 Q282 130 200 126 Q118 130 106 180 Z"
          fill={hairCol}
        />
      );
      break;
    case "bald_sides":
      hairFront = (
        <g fill={hairCol}>
          <path d="M106 212 Q100 150 126 126 L134 176 Q118 186 112 214 Z" />
          <path d="M294 212 Q300 150 274 126 L266 176 Q282 186 288 214 Z" />
        </g>
      );
      break;
    case "bun":
      hairFront = (
        <g fill={hairCol}>
          <circle cx={200} cy={80} r={36} />
          <path d="M104 200 Q96 88 200 82 Q304 88 296 200 Q290 128 200 120 Q110 128 104 200 Z" />
        </g>
      );
      break;
    case "long_braid":
      hairBack = <path d="M100 200 Q92 300 120 330 L280 330 Q308 300 300 200 Z" fill={hairCol} />;
      hairFront = (
        <g fill={hairCol}>
          <path d="M102 210 Q94 86 200 80 Q306 86 298 210 Q292 132 200 122 Q108 132 102 210 Z" />
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <ellipse key={i} cx={268 + Math.sin(i) * 3} cy={292 + i * 34} rx={17 - i} ry={20} />
          ))}
        </g>
      );
      break;
    case "pagdi":
      hairFront = (
        <g>
          <path d="M98 182 Q90 76 200 64 Q310 76 302 182 Q292 140 200 136 Q108 140 98 182 Z" fill={look.pagdi || "#e85d04"} />
          <path d="M104 160 Q200 96 296 160" stroke={darken(look.pagdi || "#e85d04", 0.25)} strokeWidth={8} fill="none" />
          <path d="M110 132 Q200 76 290 132" stroke={darken(look.pagdi || "#e85d04", 0.25)} strokeWidth={7} fill="none" />
          <ellipse cx={248} cy={84} rx={30} ry={22} fill={look.pagdi || "#e85d04"} />
        </g>
      );
      break;
  }

  // ---- torso shape
  const torsoBottom = isKurta ? 722 : 610;
  const torso = isKurta
    ? "M108 322 Q200 292 292 322 L314 722 Q200 740 86 722 Z"
    : "M108 322 Q200 292 292 322 L302 612 Q200 628 98 612 Z";

  const sleeve = (a: typeof R, sx: number) => (
    <g>
      <path
        d={`M${sx} 335 L${a.ex} ${a.ey}`}
        stroke={sleeveFull || look.topStyle === "tshirt" ? top : isSaree ? top : skin}
        strokeWidth={46}
        strokeLinecap="round"
      />
      <path
        d={`M${a.ex} ${a.ey} L${a.hx} ${a.hy}`}
        stroke={sleeveFull ? top : skin}
        strokeWidth={40}
        strokeLinecap="round"
      />
      <circle cx={a.hx} cy={a.hy} r={23} fill={skin} />
    </g>
  );

  return (
    <svg
      viewBox="0 0 400 900"
      width={widthPx}
      height={height}
      style={{ overflow: "visible", ...style }}
    >
      <g transform={`translate(200 900) scale(${facing} 1) translate(-200 -900)`}>
        <g transform={`translate(0 ${bob}) rotate(${sway} 200 880)`}>
          {/* shadow */}
          <ellipse cx={200} cy={888 - bob} rx={120} ry={14} fill="rgba(0,0,0,0.18)" />
          {hairBack}
          {/* back accessories */}
          {look.accessory === "backpack" && <rect x={86} y={330} width={228} height={250} rx={40} fill={look.accent} />}

          {/* legs / skirt */}
          {isSaree ? (
            <g>
              <path d="M112 470 L288 470 L318 880 L82 880 Z" fill={top} />
              {[0, 1, 2, 3].map((i) => (
                <path key={i} d={`M${170 + i * 14} 600 L${160 + i * 18} 878`} stroke={topD} strokeWidth={4} />
              ))}
              <path d="M82 860 L318 860 L318 880 L82 880 Z" fill={look.accent} />
              <ellipse cx={150} cy={884} rx={34} ry={12} fill="#5b3a29" />
              <ellipse cx={250} cy={884} rx={34} ry={12} fill="#5b3a29" />
            </g>
          ) : (
            <g>
              <rect x={136} y={torsoBottom - 20} width={58} height={860 - torsoBottom + 20} rx={18} fill={pants} />
              <rect x={206} y={torsoBottom - 20} width={58} height={860 - torsoBottom + 20} rx={18} fill={pants} />
              <ellipse cx={160} cy={872} rx={44} ry={18} fill="#2d2a32" />
              <ellipse cx={240} cy={872} rx={44} ry={18} fill="#2d2a32" />
            </g>
          )}

          {/* torso */}
          <path d={torso} fill={top} />
          {isKurta && <path d="M200 312 L200 470" stroke={topD} strokeWidth={5} />}
          {isKurta && [0, 1, 2].map((i) => <circle key={i} cx={200} cy={340 + i * 34} r={5} fill={look.accent} />)}
          {look.topStyle === "shirt" && (
            <g>
              <path d="M170 300 L200 336 L230 300 L222 324 L200 352 L178 324 Z" fill="#fff" />
              <path d="M200 340 L200 600" stroke={topD} strokeWidth={4} />
              {[0, 1, 2, 3].map((i) => <circle key={i} cx={210} cy={380 + i * 52} r={4} fill={topD} />)}
              <rect x={100} y={588} width={204} height={22} fill={darken(pants, 0.2)} />
            </g>
          )}
          {look.topStyle === "blazer" && (
            <g>
              <path d="M168 302 L200 420 L232 302 Z" fill="#fff" />
              <path d="M168 302 L150 400 L200 470 Z" fill={topD} />
              <path d="M232 302 L250 400 L200 470 Z" fill={topD} />
              <circle cx={200} cy={500} r={6} fill={look.accent} />
              <circle cx={200} cy={540} r={6} fill={look.accent} />
            </g>
          )}
          {look.topStyle === "tshirt" && (
            <g>
              <path d="M176 304 Q200 330 224 304" stroke={topD} strokeWidth={8} fill="none" />
              <circle cx={200} cy={440} r={46} fill={look.accent} opacity={0.9} />
              <text x={200} y={458} textAnchor="middle" fontSize={50} fontWeight={800} fill="#fff" fontFamily="sans-serif">
                ?
              </text>
            </g>
          )}
          {isSaree && (
            <g>
              <path d="M108 322 Q200 292 292 322 L300 480 L100 480 Z" fill={top} />
              <path d="M262 312 L300 330 L170 640 L120 610 Z" fill={look.accent} opacity={0.95} />
              <path d="M262 312 L300 330 L170 640" stroke={darken(look.accent, 0.25)} strokeWidth={6} fill="none" />
            </g>
          )}
          {look.accessory === "shawl" && (
            <path d="M104 320 Q200 280 296 320 L310 470 Q290 420 250 410 L200 360 L150 410 Q110 420 90 470 Z" fill={look.accent} />
          )}
          {look.accessory === "gamcha" && (
            <g>
              <path d="M130 312 Q200 360 270 312 L276 336 Q200 386 124 336 Z" fill={look.accent} />
              <rect x={232} y={330} width={30} height={160} rx={8} fill={look.accent} />
              {[0, 1, 2, 3].map((i) => (
                <line key={i} x1={232} x2={262} y1={350 + i * 34} y2={350 + i * 34} stroke="#fff" strokeWidth={4} />
              ))}
            </g>
          )}
          {look.accessory === "apron" && <rect x={130} y={400} width={140} height={210} rx={14} fill={look.accent} />}
          {look.accessory === "dupatta" && (
            <path d="M120 316 Q200 360 280 316 L290 340 Q200 392 110 340 Z" fill={look.accent} />
          )}
          {look.accessory === "backpack" && (
            <g>
              <path d="M128 318 L150 560" stroke={darken(look.accent, 0.2)} strokeWidth={18} strokeLinecap="round" />
              <path d="M272 318 L250 560" stroke={darken(look.accent, 0.2)} strokeWidth={18} strokeLinecap="round" />
            </g>
          )}
          {look.accessory === "id_badge" && (
            <g>
              <path d="M180 302 L200 420 L220 302" stroke="#d62828" strokeWidth={5} fill="none" />
              <rect x={180} y={418} width={42} height={56} rx={6} fill="#fff" stroke="#999" strokeWidth={2} />
              <rect x={188} y={428} width={26} height={18} rx={3} fill="#8ecae6" />
              <rect x={186} y={454} width={30} height={5} fill="#ccc" />
            </g>
          )}

          {/* arms */}
          {sleeve(Lr, 108)}
          {sleeve(R, 292)}
          {gesture === "point" && (
            <path
              d={`M${R.hx} ${R.hy} l${Math.sin(deg(rA[0] + rA[1])) * 40} ${Math.cos(deg(rA[0] + rA[1])) * 40}`}
              stroke={skin}
              strokeWidth={13}
              strokeLinecap="round"
            />
          )}
          {gesture === "thumbs" && (
            <rect x={R.hx - 8} y={R.hy - 48} width={16} height={36} rx={8} fill={skin} />
          )}

          {/* neck + head */}
          <rect x={180} y={262} width={40} height={52} rx={12} fill={skinD} />
          <ellipse cx={112} cy={200} rx={17} ry={22} fill={skinD} />
          <ellipse cx={288} cy={200} rx={17} ry={22} fill={skinD} />
          <ellipse cx={200} cy={186} rx={90} ry={100} fill={skin} />
          {hairFront}

          {/* face */}
          {(emotion === "happy" || emotion === "excited" || emotion === "proud") && (
            <g fill="#ff8fa3" opacity={0.45}>
              <circle cx={150} cy={226} r={15} />
              <circle cx={250} cy={226} r={15} />
            </g>
          )}
          <g>
            <ellipse cx={165} cy={ey} rx={15} ry={eyeRy} fill="#fff" />
            <ellipse cx={235} cy={ey} rx={15} ry={eyeRy} fill="#fff" />
            {!blink && (
              <g fill={ink}>
                <circle cx={168} cy={ey + 2} r={emotion === "shocked" ? 6 : 8} />
                <circle cx={238} cy={ey + 2} r={emotion === "shocked" ? 6 : 8} />
                <circle cx={171} cy={ey - 1} r={2.5} fill="#fff" />
                <circle cx={241} cy={ey - 1} r={2.5} fill="#fff" />
              </g>
            )}
          </g>
          <path d={bl} stroke={darken(hairCol === "#f2f2f2" ? "#9a9a9a" : hairCol, 0)} strokeWidth={7} fill="none" strokeLinecap="round" />
          <path d={br} stroke={darken(hairCol === "#f2f2f2" ? "#9a9a9a" : hairCol, 0)} strokeWidth={7} fill="none" strokeLinecap="round" />
          <path d="M198 206 Q192 222 202 226" stroke={skinD} strokeWidth={5} fill="none" strokeLinecap="round" />
          {look.beard !== "none" && (
            <path
              d={
                look.beard === "stubble"
                  ? "M126 230 Q200 330 274 230 Q264 290 200 296 Q136 290 126 230 Z"
                  : "M118 214 Q120 330 200 340 Q280 330 282 214 Q270 300 200 300 Q130 300 118 214 Z"
              }
              fill={look.beard === "white_full" ? "#eeeeee" : look.beard === "stubble" ? darken(skin, 0.35) : look.hair}
              opacity={look.beard === "stubble" ? 0.45 : 1}
            />
          )}
          {mouthEl}
          {look.mustache && (
            <path
              d="M168 236 Q184 224 200 234 Q216 224 232 236 Q216 244 200 238 Q184 244 168 236 Z"
              fill={look.beard === "white_full" ? "#e6e6e6" : look.hair === "#f2f2f2" ? "#d9d9d9" : "#2a1f1a"}
            />
          )}
          {look.bindi && <circle cx={200} cy={150} r={6} fill="#d62828" />}
          {look.glasses && (
            <g stroke="#2b2b2b" strokeWidth={5} fill="rgba(255,255,255,0.12)">
              <rect x={142} y={170} width={46} height={40} rx={14} />
              <rect x={212} y={170} width={46} height={40} rx={14} />
              <path d="M188 188 Q200 182 212 188" fill="none" />
            </g>
          )}
        </g>
      </g>
    </svg>
  );
};
