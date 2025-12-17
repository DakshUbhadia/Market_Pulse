'use client'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useRouter } from "next/navigation"
import React from 'react'
import { Button } from '../ui/button'
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { LogOut } from "lucide-react"
import { authClient } from "@/lib/auth-client"
import NavItems from "./NavItems"

const UserDropdown = () => {
  const router = useRouter();
  const { data: session, isPending, isRefetching, refetch } = authClient.useSession();

  React.useEffect(() => {
    // After sign-in/sign-up we often arrive here via a client-side navigation.
    // Force a session refresh so we don't show the fallback user.
    refetch().catch(() => null);
  }, [refetch]);

    const handleLogout = async () => {
        await authClient.signOut();
        router.push('/sign-in');
    }

    const showLoading = !session?.user && (isPending || isRefetching);

    const viewUser: { name: string; email: string; image?: string | null } = session?.user
      ? { name: session.user.name, email: session.user.email, image: session.user.image ?? null }
      : showLoading
        ? { name: "Loading…", email: "", image: null }
        : { name: "Guest", email: "", image: null };
    const userInitials = viewUser.name ? viewUser.name[0].toUpperCase() : "G";

  return (
  <DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="ghost" className="flex items-center gap-3 text-gray-400 hover:text-yellow-500">
        <Avatar className="h-8 w-8">
        <AvatarImage src={viewUser.image || "https://github.com/shadcn.png"} />
        <AvatarFallback className="bg-yellow-500 text-yellow-900 text-sm font-bold">
            {userInitials}
        </AvatarFallback>
        </Avatar>
        <div className="hidden sm:flex flex-col items-start">
          <span className="text-sm font-medium ">{viewUser.name}</span>
        </div>
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent className="text-gray-500">
    <DropdownMenuLabel>
      <div className="flex relative items-center gap-3 py-2">
        <Avatar className="h-8 w-8">
          <AvatarImage src={viewUser.image || "https://github.com/shadcn.png"} />
          <AvatarFallback className="bg-yellow-500 text-yellow-900 text-sm font-bold">
              {userInitials}
          </AvatarFallback>
        </Avatar>
        <div className="flex flex-col">
          <span className="text-base font-medium">{viewUser.name}</span>
          <span className="text-xs text-gray-400">{viewUser.email}</span>
        </div>
      </div>
    </DropdownMenuLabel>
    <DropdownMenuSeparator />
    <DropdownMenuItem className="cursor-pointer group text-red-500 focus:text-red-500" onClick={handleLogout}>
      <LogOut className="mr-2 h-4 w-4 group-hover:text-red-600" />
      <span>Log out</span>
    </DropdownMenuItem>
    <DropdownMenuSeparator className="hidden sm:block bg-gray-600"/>
      <nav className="sm:hidden">
        <NavItems />
      </nav>
  </DropdownMenuContent>
  </DropdownMenu>
  )
}

export default UserDropdown