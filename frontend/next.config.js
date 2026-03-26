/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.supabase.co" },
      { protocol: "https", hostname: "**.openstreetmap.org" },
      { protocol: "https", hostname: "**.cartocdn.com" },
      { protocol: "https", hostname: "cdnjs.cloudflare.com" },
    ],
  },
  webpack: (config) => {
    // Required for Babylon.js
    config.externals = [...(config.externals || []), { canvas: "canvas" }];
    return config;
  },
};

module.exports = nextConfig;
