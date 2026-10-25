import { Config } from "@remotion/cli/config";

// Plain H.264 MP4. Quality is set by CRF (lower = better); 20 is a good balance for YouTube.
Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(92);
Config.setCodec("h264");
Config.setCrf(20);
Config.setPixelFormat("yuv420p");
// GitHub's public machines have 4 processors and 16 GB memory. 3 parallel browser
// tabs keeps memory use safe while still rendering quickly.
Config.setConcurrency(3);
Config.setChromiumOpenGlRenderer("swangle");
