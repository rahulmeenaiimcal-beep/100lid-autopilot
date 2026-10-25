import React, { useEffect, useState } from "react";
import { continueRender, delayRender } from "remotion";
// Fonts are installed from npm (Fontsource, SIL Open Font License) so no download is needed at render time.
import "@fontsource/baloo-2/700.css";
import "@fontsource/baloo-2/800.css";
import "@fontsource/hind/500.css";
import "@fontsource/hind/600.css";
import "@fontsource/hind/700.css";

// Waits until the Hindi fonts are really loaded before any frame is captured,
// so no frame is ever rendered with a fallback font.
export const FontGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [handle] = useState(() => delayRender("Loading fonts"));
  useEffect(() => {
    const loads = [
      "700 40px 'Baloo 2'",
      "800 40px 'Baloo 2'",
      "500 40px 'Hind'",
      "600 40px 'Hind'",
      "700 40px 'Hind'",
    ].map((f) => document.fonts.load(f, "अआ नमस्ते Aa"));
    Promise.all(loads)
      .then(() => document.fonts.ready)
      .catch(() => undefined)
      .then(() => continueRender(handle));
  }, [handle]);
  return <>{children}</>;
};
