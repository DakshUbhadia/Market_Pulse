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
import NavItems from "./NavItems"
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
            <span className="text-sm font-medium ">{user.name}</span>
        </div>
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent className="text-gray-500">
    <DropdownMenuLabel>
      <div className="flex relative items-center gap-3 py-2">
        <Avatar className="h-8 w-8">
          <AvatarImage src="https://github.com/shadcn.png" />
          <AvatarFallback className="bg-yellow-500 text-yellow-900 text-sm font-bold">
              {user.name[0]}
          </AvatarFallback>
        </Avatar>
        <div className="flex flex-col">
          <span className="text-base font-medium">{user.name}</span>
          <span className="text-sm text-gray-500">{user.email}</span>
        </div>
      </div>
    </DropdownMenuLabel>
    <DropdownMenuSeparator className="bg bg-gray-600" />
    <DropdownMenuItem onClick={handleLogout} className="text-gray-100 text-md font-medium focus:text-yellow-500 transition-colors cursor-pointer">
      <LogOut className="size-4 mr-2" />
      Logout
    </DropdownMenuItem>
    <DropdownMenuSeparator className="hidden sm:block bg-gray-600" />
    <div className="sm:hidden">
        <NavItems />
    </div>
  </DropdownMenuContent>
</DropdownMenu>
  )
}

export default UserDropdown