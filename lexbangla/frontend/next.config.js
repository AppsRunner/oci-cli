/** @type {import('next').NextConfig} */

const DJANGO_API_URL = process.env.DJANGO_API_URL ?? 'http://127.0.0.1:8000';

const nextConfig = {
  // ------------------------------------------------------------------ //
  // Output mode — standalone bundle for Docker / OCI Container Instances
  // ------------------------------------------------------------------ //
  output: 'standalone',

  // ------------------------------------------------------------------ //
  // Compiler
  // ------------------------------------------------------------------ //
  swcMinify: true,
  reactStrictMode: true,
  poweredByHeader: false,

  // ------------------------------------------------------------------ //
  // Images — serve from OCI Object Storage public bucket or media origin
  // ------------------------------------------------------------------ //
  images: {
    domains: [
      'objectstorage.ap-mumbai-1.oraclecloud.com',
      'media.lexbangla.com',
    ],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 86400, // 1 day; CDN adds on top
  },

  // ------------------------------------------------------------------ //
  // Rewrites — proxy /api/* to Django so the browser never has to
  // deal with CORS for same-origin API calls.
  // ------------------------------------------------------------------ //
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${DJANGO_API_URL}/api/:path*`,
      },
      {
        source: '/admin/:path*',
        destination: `${DJANGO_API_URL}/admin/:path*`,
      },
    ];
  },

  // ------------------------------------------------------------------ //
  // Headers — add CDN-friendly Cache-Control for Next.js static assets
  // ------------------------------------------------------------------ //
  async headers() {
    return [
      // Immutable hash-named Next.js bundles
      {
        source: '/_next/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      // Favicon, robots.txt, manifest, etc.
      {
        source: '/(favicon.ico|robots.txt|manifest.json)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=86400, stale-while-revalidate=3600',
          },
        ],
      },
      // Legal document pages — short public TTL; ISR keeps them fresh
      {
        source: '/legal/:path*',
        headers: [
          {
            key: 'Cache-Control',
            // s-maxage: edge TTL (OCI WAA / Cloudflare / Nginx)
            // max-age:  browser TTL (shorter so fresh content loads faster)
            // stale-while-revalidate: serve stale while Next.js ISR runs
            value: 'public, s-maxage=300, max-age=60, stale-while-revalidate=300',
          },
          {
            key: 'Vary',
            value: 'Accept-Language',
          },
        ],
      },
      // Security headers for all pages
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options',        value: 'DENY' },
          { key: 'X-Content-Type-Options',  value: 'nosniff' },
          { key: 'Referrer-Policy',         value: 'strict-origin-when-cross-origin' },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: https://objectstorage.ap-mumbai-1.oraclecloud.com https://media.lexbangla.com",
              "font-src 'self' data:",
              "connect-src 'self' https://api.lexbangla.com",
            ].join('; '),
          },
        ],
      },
    ];
  },

  // ------------------------------------------------------------------ //
  // Webpack — bundle analyser (run: ANALYZE=true next build)
  // ------------------------------------------------------------------ //
  webpack(config, { isServer }) {
    if (process.env.ANALYZE === 'true') {
      const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
      config.plugins.push(
        new BundleAnalyzerPlugin({
          analyzerMode: 'static',
          reportFilename: isServer
            ? '../analyze/server.html'
            : './analyze/client.html',
        })
      );
    }
    return config;
  },
};

module.exports = nextConfig;
