import { betterAuth } from "better-auth";
import { mongodbAdapter } from "better-auth/adapters/mongodb";
import { nextCookies } from "better-auth/next-js";
import { MongoClient, type Db } from "mongodb";

const MONGODB_URI = process.env.MONGODB_URI;
const MONGODB_DB_NAME = process.env.MONGODB_DB_NAME;

let mongoClient: MongoClient | null = null;
let mongoDb: Db | null = null;

const getMongoDb = async () => {
    if (mongoDb) return mongoDb;
    if (!MONGODB_URI) throw new Error("MONGODB_URI must be set within .env");

    if (!mongoClient) {
        mongoClient = new MongoClient(MONGODB_URI);
        await mongoClient.connect();
    }

    mongoDb = mongoClient.db(MONGODB_DB_NAME);
    return mongoDb;
};

let authInstance: ReturnType<typeof betterAuth> | null = null;
export const getAuth = async () => {
    if(authInstance) return authInstance;
    const db = await getMongoDb();

    if(!db) throw new Error("Database connection is not established");

    const baseURL =
        process.env.BETTER_AUTH_URL ||
        (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "http://localhost:3000");

    const trustedOrigins = Array.from(
        new Set(
            [
                "http://localhost:3000",
                // Prefer explicit envs, but fall back to Vercel's runtime URL.
                process.env.NEXT_PUBLIC_BETTER_AUTH_URL,
                process.env.BETTER_AUTH_URL,
                process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : undefined,
                // Allow Vercel preview deployments too (safe as long as your project is private/controlled).
                "https://*.vercel.app",
            ].filter((v): v is string => typeof v === "string" && v.length > 0),
        ),
    );

    authInstance = betterAuth({
        database: mongodbAdapter(db),

        secret: process.env.BETTER_AUTH_SECRET,
        baseURL,
        trustedOrigins,

        emailAndPassword: {
            enabled: true,
            disableSignUp: false,
            requireEmailVerification: false,
            minPasswordLength: 8,
            maxPasswordLength: 128,
            autoSignIn : true,
        },
        plugins: [nextCookies()],
    });

    return authInstance;
}