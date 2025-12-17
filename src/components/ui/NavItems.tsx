'use client'
import { NAV_ITEMS, type NavItem } from '@/lib/constants'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

type NavItemsProps = {
    onSearchClick?: () => void
}

const NavItems = ({ onSearchClick }: NavItemsProps) => {
    const pathname = usePathname()

    const isActive = (path: string) => {
        if (path === '/') return pathname === '/'

        return pathname.startsWith(path)
    }

    const getLinkClass = (active: boolean) =>
        `transition-colors ${
            active ? 'text-yellow-500 font-semibold' : 'text-white hover:text-yellow-500'
        }`

    return (
        <ul className="flex flex-col sm:flex-row p-2 gap-3 sm:gap-10 font-medium">
            {NAV_ITEMS.map(({ href, label, variant }: NavItem) => {
                const linkClass = getLinkClass(variant !== 'command' && isActive(href))

                return (
                    <li key={href}>
                        {variant === 'command' ? (
                            <button
                                type="button"
                                className={`${linkClass} cursor-pointer`}
                                onClick={(event) => {
                                    event.preventDefault()
                                    onSearchClick?.()
                                }}
                            >
                                {label}
                            </button>
                        ) : (
                            <Link href={href} className={linkClass}>
                                {label}
                            </Link>
                        )}
                    </li>
                )
            })}
        </ul>
    )
}

export default NavItems