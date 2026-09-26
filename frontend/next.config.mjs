/** @type {import('next').NextConfig} */
const nextConfig = {
  /* config options here */
  reactStrictMode: true,
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  // Proxy /api/* to the backend so the browser sees the API as same-origin.
  // This makes the auth cookies first-party (httpOnly, SameSite=Lax) instead of
  // cross-site (which modern browsers block). Set BACKEND_ORIGIN in the
  // environment (e.g. https://backend-production-901a.up.railway.app); defaults
  // to the local dev backend.
  async rewrites() {
    const backend = process.env.BACKEND_ORIGIN || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backend}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
