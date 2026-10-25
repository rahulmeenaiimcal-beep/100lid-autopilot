import React from "react";
import { Composition, Still } from "remotion";
import { Episode } from "./Episode";
import { Thumbnail } from "./Thumbnail";
import { EpisodeProps, ThumbProps } from "./types";

// The robot passes real data with --props=... ; these defaults only make the
// project open in Remotion Studio.
const emptyEpisode: EpisodeProps = {
  format: "long",
  fps: 30,
  width: 1920,
  height: 1080,
  durationInFrames: 90,
  brand: { name: "100LID", handle: "@100LIDEDUCATION", accent: "#ffd23f", accent2: "#073b4c" },
  series: "",
  title: "",
  cast: {},
  talk: [],
  amp: "",
  shots: [],
  captions: [],
  chapters: [],
};

const emptyThumb: ThumbProps = {
  width: 1280,
  height: 720,
  brand: emptyEpisode.brand,
  series: "",
  textTop: "",
  textBig: "",
  emotion: "shocked",
  character: {
    name: "",
    skin: "#c68642",
    hair: "#222",
    hairStyle: "short",
    beard: "none",
    mustache: false,
    glasses: false,
    top: "#118ab2",
    topStyle: "shirt",
    accent: "#ffd23f",
    accessory: "none",
    bindi: false,
    height: 1,
  },
  icon: "bank",
  palette: 0,
  layout: 0,
};

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Episode"
      component={Episode as any}
      defaultProps={emptyEpisode}
      fps={30}
      width={1920}
      height={1080}
      durationInFrames={90}
      calculateMetadata={({ props }) => {
        const p = props as EpisodeProps;
        return { durationInFrames: Math.max(1, p.durationInFrames), fps: p.fps || 30, width: p.width, height: p.height };
      }}
    />
    <Still
      id="Thumbnail"
      component={Thumbnail as any}
      defaultProps={emptyThumb}
      width={1280}
      height={720}
      calculateMetadata={({ props }) => {
        const p = props as ThumbProps;
        return { width: p.width || 1280, height: p.height || 720 };
      }}
    />
  </>
);
