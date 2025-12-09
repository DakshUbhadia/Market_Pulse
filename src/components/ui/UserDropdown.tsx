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
const UserDropdown = () => {
    const router = useRouter();

    const handleLogout = async () => {
        router.push('/login');
    }

    const user = { name: "Daksh", email: "ubhadiadaksh@gmail.com" };

  return (
    <DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="ghost" className="flex items-center gap-3 text-gray-400 hover:text-yellow-500">
        <Avatar className="h-8 w-8">
        <AvatarImage src="https://github.com/shadcn.png" />
        <AvatarFallback className="bg-yellow-500 text-yellow-900 text-sm font-bold">
            {user.name[0]}
        </AvatarFallback>
        </Avatar>
        <div className="hidden sm:flex flex-col items-start">
            <span className="text-sm font-medium">{user.name}</span>
            <span className="text-xs text-gray-500">{user.email}</span>
        </div>
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent>
    <DropdownMenuLabel>My Account</DropdownMenuLabel>
    <DropdownMenuSeparator />
    <DropdownMenuItem>Profile</DropdownMenuItem>
    <DropdownMenuItem>Billing</DropdownMenuItem>
    <DropdownMenuItem>Team</DropdownMenuItem>
    <DropdownMenuItem>Subscription</DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem onClick={handleLogout}>Logout</DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
  )
}

export default UserDropdown