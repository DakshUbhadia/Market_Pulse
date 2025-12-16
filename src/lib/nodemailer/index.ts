import nodemailer from 'nodemailer';
import {WELCOME_EMAIL_TEMPLATE} from "@/lib/nodemailer/templates";

interface WelcomeEmailData {
    email: string;
    name: string;
    intro: string;
    otp?: string;
}

export const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
        user: process.env.NODEMAILER_EMAIL!,
        pass: process.env.NODEMAILER_PASSWORD!,
    }
})

export const sendWelcomeEmail = async ({ email, name, intro, otp }: WelcomeEmailData) => {
    if (!process.env.NODEMAILER_EMAIL || !process.env.NODEMAILER_PASSWORD) {
        throw new Error("Email credentials are not configured");
    }

    let htmlTemplate = WELCOME_EMAIL_TEMPLATE
        .replace('{{name}}', name)
        .replace('{{intro}}', intro);

    if (otp) {
        htmlTemplate = htmlTemplate.replace('{{otp}}', otp);
    } else {
        // Remove the OTP section if no OTP is provided
        // This regex looks for the OTP section div and removes it
        // Note: This is a simple regex and assumes the structure matches exactly what's in the template
        // A more robust way would be to have separate templates, but for now we'll use string replacement
        // to hide the OTP section or replace {{otp}} with an empty string if we can't easily remove the div
        
        // Alternative: Replace the whole OTP section block with empty string
        // We'll use a marker in the template or just replace the content
        
        // Let's try to replace the specific block we added
        const otpSectionStart = '<!-- OTP Section -->';
        const otpSectionEnd = '<!-- Feature List Label -->';
        const startIndex = htmlTemplate.indexOf(otpSectionStart);
        const endIndex = htmlTemplate.indexOf(otpSectionEnd);
        
        if (startIndex !== -1 && endIndex !== -1) {
            htmlTemplate = htmlTemplate.substring(0, startIndex) + htmlTemplate.substring(endIndex);
        }
    }

    const mailOptions = {
        from: `"Market Pulse" <signalist@jsmastery.pro>`,
        to: email,
        subject: otp ? `Verify your email - Market Pulse` : `Welcome to Market Pulse - your stock market toolkit is ready!`,
        text: otp ? `Your verification code is ${otp}` : 'Thanks for joining Market Pulse',
        html: htmlTemplate,
    }

    await transporter.sendMail(mailOptions);
}