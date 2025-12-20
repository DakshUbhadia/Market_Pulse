import { NextRequest, NextResponse } from "next/server";
import { getSessionCookie } from "better-auth/cookies";

export async function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Public routes
    const isPublicRoute =
        pathname === "/" ||
        pathname.startsWith("/landing") ||
        pathname.startsWith("/sign-in") ||
        pathname.startsWith("/sign-up") ||
        pathname.startsWith("/forgot-password") ||
        pathname.startsWith("/verify-otp") ||
        pathname.startsWith("/reset-password");

    if (isPublicRoute) {
        return NextResponse.next();
    }

    const sessionCookie = getSessionCookie(request);

    if (!sessionCookie) {
        return NextResponse.redirect(new URL("/sign-in", request.url));
    }

    return NextResponse.next();
}

export const config = {
    matcher: [
        // Protect everything except Next.js internals + static assets.
        "/((?!api|_next/static|_next/image|favicon.ico|assets).*)",
    ],
};