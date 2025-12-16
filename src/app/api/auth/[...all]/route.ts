import { getAuth } from "@/lib/better-auth/auth";
import { toNextJsHandler } from "better-auth/next-js";
import { NextRequest } from "next/server";

export const GET = async (request: NextRequest) => {
    const auth = await getAuth();
    const { GET } = toNextJsHandler(auth);
    return GET(request);
}

export const POST = async (request: NextRequest) => {
    const auth = await getAuth();
    const { POST } = toNextJsHandler(auth);
    return POST(request);
}
