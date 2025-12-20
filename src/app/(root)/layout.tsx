import React from 'react'
import Header from '@/components/ui/Header'
import { WatchlistProvider } from '@/context/WatchlistContext'
import RequireAuthClient from '@/components/auth/RequireAuthClient'

const layout = ({ children }: { children: React.ReactNode }) => {
  return (
    <WatchlistProvider>
      <RequireAuthClient>
        <main className="min-h-screen text-gray-400">
          <Header></Header>
          <div className="container py-10">
            {children}
          </div>
        </main>
      </RequireAuthClient>
    </WatchlistProvider>
  )
}

export default layout