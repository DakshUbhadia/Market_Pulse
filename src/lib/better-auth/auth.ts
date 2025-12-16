import { betterAuth } from "better-auth";
import{ mongodbAdapter } from "better-auth/adapters/mongodb";
import {nextCookies} from "better-auth/next-js";
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

    authInstance = betterAuth({
        database: mongodbAdapter(db),

        secret: process.env.BETTER_AUTH_SECRET,
        baseURL: process.env.BETTER_AUTH_URL,

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