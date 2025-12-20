'use server';

import {getAuth} from "@/lib/better-auth/auth";
import {inngest} from "@/lib/inngest/client";
import {headers} from "next/headers";
import Otp from "@/database/models/otp.model";
import { connectToDatabase } from "@/database/mongoose";
import { sendWelcomeEmail } from "@/lib/nodemailer";
import { hashPassword } from "better-auth/crypto";

interface SignUpFormData {
    email: string;
    password: string;
    fullName: string;
    country: string;
    investmentGoals: string;
    riskTolerance: string;
    preferredIndustry: string;
    otp: string;
}

interface SignInFormData {
    email: string;
    password: string;
}

const normalizeEmail = (email: string) => email.trim().toLowerCase();

const getExistingCollection = async (
    db: NonNullable<Awaited<ReturnType<typeof connectToDatabase>>["connection"]["db"]>,
    candidates: string[],
) => {
    const collections = await db.listCollections({}, { nameOnly: true }).toArray();
    const existingNames = new Set(collections.map((c) => c.name));
    const chosen = candidates.find((name) => existingNames.has(name)) ?? candidates[0];
    return db.collection(chosen);
};

export const sendOtp = async ({ email, name }: { email: string; name: string }) => {
    try {
        const mongoose = await connectToDatabase();
        const db = mongoose.connection.db;
        if (!db) {
            return { success: false, error: "Database connection failed" };
        }

        const normalizedEmail = normalizeEmail(email);

        // Prevent duplicate sign-ups
        const userCollection = await getExistingCollection(db, ["user", "users"]);
        const existingUser =
            (await userCollection.findOne({ email: normalizedEmail })) ??
            (await userCollection.findOne({ email: { $regex: `^${normalizedEmail.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")}$`, $options: "i" } }));
        if (existingUser) {
            return { success: false, error: "An account with this email already exists. Please sign in." };
        }
        
        // Generate 6-digit OTP
        const otp = Math.floor(100000 + Math.random() * 900000).toString();
        
        // Delete any existing OTP for this email
        await Otp.deleteMany({ email: normalizedEmail });
        
        // Create new OTP
        await Otp.create({ email: normalizedEmail, otp });
        
        // Send email
        await sendWelcomeEmail({
            email: normalizedEmail,
            name: name || "User",
            intro: "Please verify your email address to complete your registration.",
            otp
        });
        
        return { success: true };
    } catch (error: unknown) {
        console.error("Error sending OTP:", error);
        const message = error instanceof Error ? error.message : undefined;
        return { success: false, error: message || "Failed to send verification code" };
    }
};

export const sendPasswordResetOtp = async ({ email }: { email: string }) => {
    try {
        const mongoose = await connectToDatabase();
        const db = mongoose.connection.db;
        if (!db) {
            return { success: false, error: "Database connection failed" };
        }

        const normalizedEmail = normalizeEmail(email);

        // Only send reset OTP to existing users
        const userCollection = await getExistingCollection(db, ["user", "users"]);
        const user =
            (await userCollection.findOne({ email: normalizedEmail })) ??
            (await userCollection.findOne({ email: { $regex: `^${normalizedEmail.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")}$`, $options: "i" } }));

        if (!user) {
            return { success: false, error: "No account found with that email" };
        }
        
        // Generate 6-digit OTP
        const otp = Math.floor(100000 + Math.random() * 900000).toString();
        
        // Delete any existing OTP for this email
        await Otp.deleteMany({ email: normalizedEmail });
        
        // Create new OTP
        await Otp.create({ email: normalizedEmail, otp });
        
        // Send email
        await sendWelcomeEmail({
            email: normalizedEmail,
            name: "User",
            intro: "You requested to reset your password. Use the verification code below to continue.",
            otp
        });
        
        return { success: true };
    } catch (error) {
        console.error("Error sending password reset OTP:", error);
        return { success: false, error: "Failed to send verification code" };
    }
};

export const verifyOtp = async ({ email, otp }: { email: string; otp: string }) => {
    try {
        await connectToDatabase();

        const normalizedEmail = normalizeEmail(email);
        
        const otpRecord = await Otp.findOne({ email: normalizedEmail, otp });
        
        if (!otpRecord) {
            return { success: false, error: "Invalid or expired verification code" };
        }
        
        return { success: true };
    } catch (error) {
        console.error("Error verifying OTP:", error);
        return { success: false, error: "Failed to verify code" };
    }
};

export const resetPassword = async ({ email, newPassword, token }: { email: string; newPassword: string; token: string }) => {
    try {
        const mongoose = await connectToDatabase();
        const db = mongoose.connection.db;
        
        if (!db) {
            return { success: false, error: "Database connection failed" };
        }

        const normalizedEmail = normalizeEmail(email);

        // Verify token (OTP) server-side as well
        const otpRecord = await Otp.findOne({ email: normalizedEmail, otp: token });
        if (!otpRecord) {
            return { success: false, error: "Invalid or expired reset link. Please request a new one." };
        }
        
        const hashedPassword = await hashPassword(newPassword);
        
        // First, find the user by email in the users collection
        const userCollection = await getExistingCollection(db, ["user", "users"]);
        const accountCollection = await getExistingCollection(db, ["account", "accounts"]);

        const user =
            (await userCollection.findOne({ email: normalizedEmail })) ??
            (await userCollection.findOne({ email: { $regex: `^${normalizedEmail.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")}$`, $options: "i" } }));
        
        if (!user) {
            return { success: false, error: "User not found" };
        }
        
        // Update the password in the accounts collection using the user's ID
        const result = await accountCollection.updateOne(
            { userId: user._id, providerId: "credential" },
            { $set: { password: hashedPassword } }
        );
        
        if (result.matchedCount === 0) {
            // Some DBs store userId as string
            const stringUserIdResult = await accountCollection.updateOne(
                { userId: user._id.toString(), providerId: "credential" },
                { $set: { password: hashedPassword } }
            );

            if (stringUserIdResult.matchedCount > 0) {
                await Otp.deleteMany({ email: normalizedEmail });
                return { success: true };
            }

            // Try with the email as accountId (fallback for older accounts)
            const fallbackResult = await accountCollection.updateOne(
                { providerId: "credential", accountId: normalizedEmail },
                { $set: { password: hashedPassword } }
            );
            
            if (fallbackResult.matchedCount === 0) {
                return { success: false, error: "Account not found. Please ensure you signed up with email." };
            }
        }
        
        // Delete the OTP after successful password reset
        await Otp.deleteMany({ email: normalizedEmail });
        
        return { success: true };
    } catch (error) {
        console.error("Error resetting password:", error);
        return { success: false, error: "Failed to reset password" };
    }
};

export const signUpWithEmail = async ({ email, password, fullName, country, investmentGoals, riskTolerance, preferredIndustry, otp }: SignUpFormData) => {
    try {
        const mongoose = await connectToDatabase();
        const db = mongoose.connection.db;
        if (!db) {
            return { success: false, error: "Database connection failed" };
        }

        const normalizedEmail = normalizeEmail(email);

        // Prevent duplicate sign-ups
        const userCollection = await getExistingCollection(db, ["user", "users"]);
        const existingUser =
            (await userCollection.findOne({ email: normalizedEmail })) ??
            (await userCollection.findOne({ email: { $regex: `^${normalizedEmail.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")}$`, $options: "i" } }));
        if (existingUser) {
            return { success: false, error: "Account already exists. Please sign in instead." };
        }
        
        // Verify OTP
        const otpRecord = await Otp.findOne({ email: normalizedEmail, otp });
        
        if (!otpRecord) {
            return { success: false, error: "Invalid or expired verification code" };
        }
        
        const auth = await getAuth();
        const response = await auth.api.signUpEmail({ body: { email: normalizedEmail, password, name: fullName } })

        if(response) {
            // Delete OTP after successful signup
            await Otp.deleteOne({ _id: otpRecord._id });
            
            await inngest.send({
                name: 'app/user.created',
                data: { email: normalizedEmail, name: fullName, country, investmentGoals, riskTolerance, preferredIndustry }
            })
        }

        return { success: true, data: response }
    } catch (e) {
        console.log('Sign up failed', e)
        const message = e instanceof Error ? e.message : undefined;
        return { success: false, error: message || 'Sign up failed' }
    }
}

export const signInWithEmail = async ({ email, password }: SignInFormData) => {
    try {
        const auth = await getAuth();
        const response = await auth.api.signInEmail({ body: { email: normalizeEmail(email), password } })

        return { success: true, data: response }
    } catch (e) {
        console.log('Sign in failed', e)
        return { success: false, error: 'Sign in failed' }
    }
}

export const signOut = async () => {
    try {
        const auth = await getAuth();
        await auth.api.signOut({ headers: await headers() });
    } catch (e) {
        console.log('Sign out failed', e)
        return { success: false, error: 'Sign out failed' }
    }
}