'use server';

import {getAuth} from "@/lib/better-auth/auth";
import {inngest} from "@/lib/inngest/client";
import {headers} from "next/headers";
import Otp from "@/database/models/otp.model";
import { connectToDatabase } from "@/database/mongoose";
import { sendWelcomeEmail } from "@/lib/nodemailer";

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

export const sendOtp = async ({ email, name }: { email: string; name: string }) => {
    try {
        await connectToDatabase();
        
        // Generate 6-digit OTP
        const otp = Math.floor(100000 + Math.random() * 900000).toString();
        
        // Delete any existing OTP for this email
        await Otp.deleteMany({ email });
        
        // Create new OTP
        await Otp.create({ email, otp });
        
        // Send email
        await sendWelcomeEmail({
            email,
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
        await connectToDatabase();
        
        // Generate 6-digit OTP
        const otp = Math.floor(100000 + Math.random() * 900000).toString();
        
        // Delete any existing OTP for this email
        await Otp.deleteMany({ email });
        
        // Create new OTP
        await Otp.create({ email, otp });
        
        // Send email
        await sendWelcomeEmail({
            email,
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
        
        const otpRecord = await Otp.findOne({ email, otp });
        
        if (!otpRecord) {
            return { success: false, error: "Invalid or expired verification code" };
        }
        
        return { success: true };
    } catch (error) {
        console.error("Error verifying OTP:", error);
        return { success: false, error: "Failed to verify code" };
    }
};

export const resetPassword = async ({ email, newPassword }: { email: string; newPassword: string }) => {
    try {
        const mongoose = await connectToDatabase();
        const db = mongoose.connection.db;
        
        if (!db) {
            return { success: false, error: "Database connection failed" };
        }
        
        // Hash the new password using Node.js crypto scrypt (same algorithm as better-auth)
        const crypto = await import("crypto");
        const { promisify } = await import("util");
        const scryptAsync = promisify(crypto.scrypt);
        
        const salt = crypto.randomBytes(16).toString("hex");
        const derivedKey = await scryptAsync(newPassword, salt, 64) as Buffer;
        const hashedPassword = `${salt}:${derivedKey.toString("hex")}`;
        
        // Update the password in the accounts collection (better-auth stores passwords in accounts)
        const result = await db.collection("accounts").updateOne(
            { providerId: "credential", accountId: email },
            { $set: { password: hashedPassword } }
        );
        
        if (result.matchedCount === 0) {
            return { success: false, error: "User not found" };
        }
        
        return { success: true };
    } catch (error) {
        console.error("Error resetting password:", error);
        return { success: false, error: "Failed to reset password" };
    }
};

export const signUpWithEmail = async ({ email, password, fullName, country, investmentGoals, riskTolerance, preferredIndustry, otp }: SignUpFormData) => {
    try {
        await connectToDatabase();
        
        // Verify OTP
        const otpRecord = await Otp.findOne({ email, otp });
        
        if (!otpRecord) {
            return { success: false, error: "Invalid or expired verification code" };
        }
        
        const auth = await getAuth();
        const response = await auth.api.signUpEmail({ body: { email, password, name: fullName } })

        if(response) {
            // Delete OTP after successful signup
            await Otp.deleteOne({ _id: otpRecord._id });
            
            await inngest.send({
                name: 'app/user.created',
                data: { email, name: fullName, country, investmentGoals, riskTolerance, preferredIndustry }
            })
        }

        return { success: true, data: response }
    } catch (e) {
        console.log('Sign up failed', e)
        return { success: false, error: 'Sign up failed' }
    }
}

export const signInWithEmail = async ({ email, password }: SignInFormData) => {
    try {
        const auth = await getAuth();
        const response = await auth.api.signInEmail({ body: { email, password } })

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