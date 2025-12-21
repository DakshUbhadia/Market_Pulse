'use client'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useRouter } from "next/navigation"
import React from 'react'
import { Button } from '../ui/button'
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { LogOut, Settings } from "lucide-react"
import { authClient } from "@/lib/auth-client"
import NavItems from "./NavItems"
import { getMyEmailPreferences, updateMyEmailPreferences, type EmailPreferencesDTO } from "@/lib/actions/email-preferences.actions"
import { Switch } from "@/components/ui/switch"

const UserDropdown = () => {
  const router = useRouter();
  const { data: session, isPending, isRefetching, refetch } = authClient.useSession();

  const [open, setOpen] = React.useState(false);
  const [mobileSettingsOpen, setMobileSettingsOpen] = React.useState(false);

  const [emailPrefs, setEmailPrefs] = React.useState<EmailPreferencesDTO | null>(null);
  const [isSavingPrefs, setIsSavingPrefs] = React.useState(false);

  React.useEffect(() => {
    // After sign-in/sign-up we often arrive here via a client-side navigation.
    // Force a session refresh so we don't show the fallback user.
    refetch().catch(() => null);
  }, [refetch]);

  React.useEffect(() => {
    if (!session?.user) {
      setEmailPrefs(null);
      return;
    }

    getMyEmailPreferences()
      .then((prefs) => setEmailPrefs(prefs))
      .catch(() => setEmailPrefs({ receiveDailyNewsSummary: true, receiveAlerts: true }));
  }, [session?.user]);

  const togglePref = async (key: keyof EmailPreferencesDTO, next: boolean) => {
    if (!session?.user) return;

    const prev = emailPrefs;
    setEmailPrefs((p) => ({
      receiveDailyNewsSummary: p?.receiveDailyNewsSummary ?? true,
      receiveAlerts: p?.receiveAlerts ?? true,
      [key]: next,
    } as EmailPreferencesDTO));

    setIsSavingPrefs(true);
    try {
      const res = await updateMyEmailPreferences({ [key]: next } as Partial<EmailPreferencesDTO>);
      if (res.success && res.preferences) {
        setEmailPrefs(res.preferences);
      } else {
        setEmailPrefs(prev ?? { receiveDailyNewsSummary: true, receiveAlerts: true });
      }
    } catch {
      setEmailPrefs(prev ?? { receiveDailyNewsSummary: true, receiveAlerts: true });
    } finally {
      setIsSavingPrefs(false);
    }
  };

    const handleLogout = async () => {
        await authClient.signOut();
        router.push('/sign-in');
    }

    const showLoading = !session?.user && (isPending || isRefetching);

    if (!session?.user) {
      return (
        <Button
          variant="ghost"
          className="flex items-center gap-3 text-gray-400 hover:text-yellow-500"
          onClick={() => router.push('/sign-in')}
          disabled={showLoading}
        >
          {showLoading ? "Loading…" : "Sign in"}
        </Button>
      );
    }

    const viewUser: { name: string; email: string; image?: string | null } = {
      name: session.user.name,
      email: session.user.email,
      image: session.user.image ?? null,
    };

    const userInitials = viewUser.name ? viewUser.name[0].toUpperCase() : "U";

  return (
  <DropdownMenu open={open} onOpenChange={setOpen}>
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
  <DropdownMenuContent
    align="end"
    side="bottom"
    sideOffset={8}
    collisionPadding={8}
    className="text-gray-500 w-[min(22rem,calc(100vw-1rem))] max-w-[calc(100vw-1rem)]"
  >
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
          <span className="text-xs text-gray-400 truncate max-w-[calc(100vw-8rem)]">{viewUser.email}</span>
        </div>
      </div>
    </DropdownMenuLabel>
    <DropdownMenuSeparator />

    {/* Desktop: keep Settings as submenu */}
    <div className="hidden sm:block">
      <DropdownMenuSub>
        <DropdownMenuSubTrigger className="cursor-pointer">
          <Settings className="mr-2 h-4 w-4" />
          <span>Settings</span>
        </DropdownMenuSubTrigger>
        <DropdownMenuSubContent className="text-gray-500 w-[min(22rem,calc(100vw-1rem))] max-w-[calc(100vw-1rem)]">
          <DropdownMenuItem onSelect={(e) => e.preventDefault()} className="cursor-default">
            <div className="flex w-full flex-col gap-2">
              <div className="flex w-full items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-gray-300">Daily news summary</span>
                </div>
                <Switch
                  checked={emailPrefs?.receiveDailyNewsSummary ?? true}
                  disabled={!session?.user || isSavingPrefs}
                  onCheckedChange={(checked) => togglePref("receiveDailyNewsSummary", Boolean(checked))}
                  className="shrink-0 data-[state=checked]:bg-yellow-500 data-[state=unchecked]:bg-gray-700"
                />
              </div>
              <span className="text-xs text-gray-500">Turn on/off daily emails</span>
            </div>
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={(e) => e.preventDefault()} className="cursor-default">
            <div className="flex w-full flex-col gap-2">
              <div className="flex w-full items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-gray-300">Alerts</span>
                </div>
                <Switch
                  checked={emailPrefs?.receiveAlerts ?? true}
                  disabled={!session?.user || isSavingPrefs}
                  onCheckedChange={(checked) => togglePref("receiveAlerts", Boolean(checked))}
                  className="shrink-0 data-[state=checked]:bg-yellow-500 data-[state=unchecked]:bg-gray-700"
                />
              </div>
              <span className="text-xs text-gray-500">Turn on/off alert emails</span>
            </div>
          </DropdownMenuItem>
        </DropdownMenuSubContent>
      </DropdownMenuSub>
    </div>

    {/* Mobile: expand inline under Settings */}
    <div className="sm:hidden">
      <DropdownMenuItem
        onSelect={(e) => {
          e.preventDefault()
          setMobileSettingsOpen((v) => !v)
        }}
        className="cursor-pointer"
      >
        <Settings className="mr-2 h-4 w-4" />
        <span>Settings</span>
      </DropdownMenuItem>

      {mobileSettingsOpen ? (
        <>
          <DropdownMenuItem onSelect={(e) => e.preventDefault()} className="cursor-default">
            <div className="flex w-full flex-col gap-2">
              <div className="flex w-full items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-gray-300">Daily news summary</span>
                </div>
                <Switch
                  checked={emailPrefs?.receiveDailyNewsSummary ?? true}
                  disabled={!session?.user || isSavingPrefs}
                  onCheckedChange={(checked) => togglePref("receiveDailyNewsSummary", Boolean(checked))}
                  className="shrink-0 data-[state=checked]:bg-yellow-500 data-[state=unchecked]:bg-gray-700"
                />
              </div>
              <span className="text-xs text-gray-500">Turn on/off daily emails</span>
            </div>
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={(e) => e.preventDefault()} className="cursor-default">
            <div className="flex w-full flex-col gap-2">
              <div className="flex w-full items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-gray-300">Alerts</span>
                </div>
                <Switch
                  checked={emailPrefs?.receiveAlerts ?? true}
                  disabled={!session?.user || isSavingPrefs}
                  onCheckedChange={(checked) => togglePref("receiveAlerts", Boolean(checked))}
                  className="shrink-0 data-[state=checked]:bg-yellow-500 data-[state=unchecked]:bg-gray-700"
                />
              </div>
              <span className="text-xs text-gray-500">Turn on/off alert emails</span>
            </div>
          </DropdownMenuItem>
        </>
      ) : null}
    </div>

    <DropdownMenuItem className="cursor-pointer group text-red-500 focus:text-red-500" onClick={handleLogout}>
      <LogOut className="mr-2 h-4 w-4 group-hover:text-red-600" />
      <span>Log out</span>
    </DropdownMenuItem>
    <DropdownMenuSeparator className="hidden sm:block bg-gray-600"/>
      <nav
        className="sm:hidden"
        onClick={() => setOpen(false)}
      >
        <NavItems
          onSearchClick={() => {
            if (typeof window !== "undefined") {
              window.dispatchEvent(new Event("marketpulse:open-search"))
            }
            setOpen(false)
          }}
        />
      </nav>
  </DropdownMenuContent>
  </DropdownMenu>
  )
}

export default UserDropdown