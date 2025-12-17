import nodemailer from 'nodemailer';
import { NEWS_SUMMARY_EMAIL_TEMPLATE, WELCOME_EMAIL_TEMPLATE } from "@/lib/nodemailer/templates";

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

export const sendNewsSummaryEmail = async (
    { email, date, newsContent }: { email: string; date: string; newsContent: string }
): Promise<void> => {
    if (!process.env.NODEMAILER_EMAIL || !process.env.NODEMAILER_PASSWORD) {
        throw new Error("Email credentials are not configured");
    }

    const htmlTemplate = NEWS_SUMMARY_EMAIL_TEMPLATE
        .replace('{{date}}', date)
        .replace('{{newsContent}}', newsContent);

    const mailOptions = {
        from: `"Market Pulse News" <signalist@jsmastery.pro>`,
        to: email,
        subject: `📈 Market News Summary Today - ${date}`,
        text: `Today's market news summary from Market Pulse`,
        html: htmlTemplate,
    };

    await transporter.sendMail(mailOptions);
};