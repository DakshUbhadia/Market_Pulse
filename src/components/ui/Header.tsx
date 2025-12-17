'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import NavItems from './NavItems'
import SearchCommand from './SearchCommand'
import UserDropdown from './UserDropdown'

const Header = () => {
  const [searchOpen, setSearchOpen] = useState(false)

  return (
    <>
      <header className="sticky top-0 header">
        <div className="container flex items-center justify-between h-16">
          <Link
            href="/"
            className="flex items-center gap-3 hover:opacity-90 transition-opacity"
          >
            <Image
              src="/assets/icons/logo.svg"
              alt="Market Pulse Logo"
              width={48}
              height={48}
              className="w-12 h-12"
            />
            <span className="font-bold text-xl hidden sm:inline bg-linear-to-r from-yellow-500 to-yellow-600 bg-clip-text text-transparent">
              Market Pulse
            </span>
          </Link>
          <nav className="hidden sm:block">
            <NavItems onSearchClick={() => setSearchOpen(true)} />
          </nav>
          <UserDropdown />
        </div>
      </header>
      <SearchCommand
        open={searchOpen}
        onOpenChange={setSearchOpen}
        showTrigger={false}
      />
    </>
  )
}

export default Header