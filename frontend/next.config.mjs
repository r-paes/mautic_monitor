/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [],
  },
  async rewrites() {
    // Em produção (EasyPanel), o backend é acessível pelo hostname interno Docker
    // Em desenvolvimento, usa localhost:8000
    const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL
      ?? process.env.INTERNAL_API_URL
      ?? "http://localhost:8000";

    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
      {
        source: "/webhooks/:path*",
        destination: `${apiUrl}/webhooks/:path*`,
      },
      {
        source: "/health",
        destination: `${apiUrl}/health`,
      },
    ];
  },
};

export default nextConfig;
