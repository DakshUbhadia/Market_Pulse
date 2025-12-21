import type { NextConfig } from "next";

type NextConfigForDeploy = NextConfig & {
  typescript?: {
    ignoreBuildErrors?: boolean;
  };
  // Newer/experimental config keys can exist even when the shipped types lag behind.
  turbopack?: Record<string, unknown>;
};

const nextConfig: NextConfigForDeploy = {
  typescript: {
    ignoreBuildErrors: true,
  },
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
