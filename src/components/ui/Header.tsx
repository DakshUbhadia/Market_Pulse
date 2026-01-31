'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import NavItems from './NavItems'
import SearchCommand from './SearchCommand'
import UserDropdown from './UserDropdown'
import { Menu, X } from 'lucide-react'

const Header = () => {
  const [searchOpen, setSearchOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <>
      <header className="sticky top-0 header z-50">
        <div className="container flex items-center justify-between h-16 px-4 sm:px-6">
          <Link
            href="/dashboard"
            className="flex items-center gap-3 hover:opacity-90 transition-opacity"
          >
            <Image
              src="/assets/icons/logo.svg"
              alt="Market Pulse Logo"
              width={48}
              height={48}
              className="w-10 h-10 sm:w-12 sm:h-12"
            />
            <span className="font-bold text-lg sm:text-xl hidden xs:inline bg-linear-to-r from-yellow-500 to-yellow-600 bg-clip-text text-transparent">
              Market Pulse
            </span>
          </Link>
          
          {/* Desktop Navigation */}
          <nav className="hidden md:block">
            <NavItems onSearchClick={() => setSearchOpen(true)} />
          </nav>
          
          {/* Desktop User Dropdown */}
          <div className="hidden md:block">
            <UserDropdown />
          </div>
          
          {/* Mobile Menu Button */}
          <button
            type="button"
            className="md:hidden p-2 text-white hover:text-yellow-500 transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
        
        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-border/30 bg-background/95 backdrop-blur-sm">
            <div className="container px-4 py-4">
              <NavItems onSearchClick={() => {
                setMobileMenuOpen(false)
                setSearchOpen(true)
              }} onNavClick={() => setMobileMenuOpen(false)} />
              <div className="mt-4 pt-4 border-t border-border/30">
                <UserDropdown />
              </div>
            </div>
          </div>
        )}
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