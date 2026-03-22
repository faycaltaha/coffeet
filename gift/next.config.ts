import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Silence "multiple lockfiles" workspace-root warning in WebContainers (StackBlitz).
  turbopack: {
    root: __dirname,
  },
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        path: false,
        os: false,
      };
    }
    return config;
  },
};

export default nextConfig;
