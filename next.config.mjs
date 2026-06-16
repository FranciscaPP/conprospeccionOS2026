/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: false,
  images: {
    unoptimized: true,
  },
  async redirects() {
    return [
      {
        source: "/client/meeting-validation",
        destination: "/docs/meeting-validation-interactive-flow.html",
        permanent: false,
      },
    ]
  },
}

export default nextConfig
