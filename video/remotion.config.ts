import { Config } from "@remotion/cli/config";

// Plain H.264 MP4. Quality is set by CRF (lower = better); 20 is a good balance for YouTube.
Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(85);
Config.setCodec("h264");
Config.setCrf(20);
Config.setX264Preset("veryfast"); // much faster encoding, same quality level
Config.setPixelFormat("yuv420p");
// GitHub's public machines have 4 processors and 16 GB memory: one browser tab per processor.
Config.setConcurrency(4);
Config.setChromiumOpenGlRenderer("swangle");
