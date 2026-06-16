/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: false,
  images: {
    unoptimized: true,
  },
  async redirects() {
    return [
      {
        // El dashboard cliente aprobado es el HTML estático servido desde /public/docs.
        source: "/client/meeting-validation",
        destination: "/docs/meeting-validation-interactive-flow.html",
        permanent: false,
      },
    ]
  },
}

export default nextConfig
