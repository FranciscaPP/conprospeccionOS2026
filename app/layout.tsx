import { Analytics } from '@vercel/analytics/next'
import type { Metadata } from 'next'
import { Inter, Geist, Saira, Saira_Condensed } from 'next/font/google'
import './globals.css'
import { AppProvider } from '@/lib/app-context'

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin']
})

const geist = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
})

const saira = Saira_Condensed({
  variable: '--font-saira',
  subsets: ['latin'],
  weight: ['500', '600', '700'],
})

const sairaBody = Saira({
  variable: '--font-saira-body',
  subsets: ['latin'],
  weight: ['400', '500', '600'],
})

export const metadata: Metadata = {
  title: 'Conprospección OS',
  description: 'B2B Sales Prospecting Operating System',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${geist.variable} ${saira.variable} ${sairaBody.variable} bg-background`}>
      <body className="font-sans antialiased">
        <AppProvider>
          {children}
        </AppProvider>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}

