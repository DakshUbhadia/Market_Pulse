import nodemailer from 'nodemailer';
import { 
    NEWS_SUMMARY_EMAIL_TEMPLATE, 
    WELCOME_EMAIL_TEMPLATE, 
    STOCK_ALERT_UPPER_EMAIL_TEMPLATE, 
    STOCK_ALERT_LOWER_EMAIL_TEMPLATE 
} from "@/lib/nodemailer/templates";

const getTransporter = () => {
    const user = process.env.NODEMAILER_EMAIL;
    const pass = process.env.NODEMAILER_PASSWORD;

    if (!user || !pass) {
        throw new Error(
            "Email credentials are not configured. Set NODEMAILER_EMAIL and NODEMAILER_PASSWORD in your environment."
        );
    }

    return nodemailer.createTransport({
        service: 'gmail',
        auth: {
            user,
            pass,
        },
    });
};

export interface AlertEmailData {
    email: string;
    alertName: string;
    symbol: string;
    company: string;
    currentPrice: string;
    targetPrice: string;
    alertType: 'PRICE' | 'PERCENTAGE' | 'PE_RATIO';
    condition: 'GREATER_THAN' | 'LESS_THAN' | 'CROSSES_ABOVE' | 'CROSSES_BELOW';
    timestamp: string;
}

interface WelcomeEmailData {
    email: string;
    name: string;
    intro: string;
    otp?: string;
}

export const sendWelcomeEmail = async ({ email, name, intro, otp }: WelcomeEmailData) => {
    const transporter = getTransporter();

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
        from: `"Market Pulse" <${process.env.NODEMAILER_EMAIL}>`,
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
    const transporter = getTransporter();

    const htmlTemplate = NEWS_SUMMARY_EMAIL_TEMPLATE
        .replace('{{date}}', date)
        .replace('{{newsContent}}', newsContent);

    const mailOptions = {
        from: `"Market Pulse News" <${process.env.NODEMAILER_EMAIL}>`,
        to: email,
        subject: `📈 Market News Summary Today - ${date}`,
        text: `Today's market news summary from Market Pulse`,
        html: htmlTemplate,
    };

    await transporter.sendMail(mailOptions);
};

export const sendAlertEmail = async (data: AlertEmailData): Promise<void> => {
    const transporter = getTransporter();

    const isUpperAlert = data.condition === 'GREATER_THAN' || data.condition === 'CROSSES_ABOVE';
    const template = isUpperAlert 
        ? STOCK_ALERT_UPPER_EMAIL_TEMPLATE 
        : STOCK_ALERT_LOWER_EMAIL_TEMPLATE;

    const metricLabel = {
        'PRICE': 'Price',
        'PERCENTAGE': '% Change',
        'PE_RATIO': 'P/E Ratio'
    }[data.alertType];

    const conditionLabel = {
        'GREATER_THAN': 'exceeded',
        'LESS_THAN': 'dropped below',
        'CROSSES_ABOVE': 'crossed above',
        'CROSSES_BELOW': 'crossed below'
    }[data.condition];

    const alertTitle = {
        'GREATER_THAN': `${metricLabel} Above Hit`,
        'LESS_THAN': `${metricLabel} Below Hit`,
        'CROSSES_ABOVE': `${metricLabel} Crossed Above`,
        'CROSSES_BELOW': `${metricLabel} Crossed Below`,
    }[data.condition];

    const triggerText = `${metricLabel} ${conditionLabel} your target of ${data.targetPrice}`;

    const crossoverMeaningRaw =
        data.condition === 'CROSSES_ABOVE'
            ? 'Bullish crossover — often viewed as a buy signal (upward momentum strengthening).'
            : data.condition === 'CROSSES_BELOW'
                ? 'Bearish crossover — often viewed as a sell signal (downward momentum strengthening).'
                : undefined;

    const crossoverMeaning = crossoverMeaningRaw
        ? `<p class="mobile-text dark-text-secondary" style="margin: 0; font-size: 14px; line-height: 1.5; color: #9ca3af;">
                <strong>Meaning:</strong> ${crossoverMeaningRaw}
           </p>`
        : '';

    const emoji = isUpperAlert ? '📈' : '📉';
    const subject = `${emoji} ${data.alertName}: ${data.symbol} ${conditionLabel} ${data.targetPrice}`;

    const htmlTemplate = template
        .replace(/\{\{symbol\}\}/g, data.symbol)
        .replace(/\{\{company\}\}/g, data.company)
        .replace(/\{\{currentPrice\}\}/g, data.currentPrice)
        .replace(/\{\{targetPrice\}\}/g, data.targetPrice)
        .replace(/\{\{timestamp\}\}/g, data.timestamp);

    const htmlWithType = htmlTemplate
        .replace(/\{\{metricLabel\}\}/g, metricLabel)
        .replace(/\{\{alertTitle\}\}/g, alertTitle)
        .replace(/\{\{triggerText\}\}/g, triggerText)
        .replace(/\{\{crossoverMeaning\}\}/g, crossoverMeaning);

    const mailOptions = {
        from: `"Market Pulse Alerts" <${process.env.NODEMAILER_EMAIL}>`,
        to: data.email,
        subject,
        text: `${data.alertName}: ${data.symbol} has ${conditionLabel} your ${metricLabel} target of ${data.targetPrice}. Current value: ${data.currentPrice}`,
        html: htmlWithType,
    };

    await transporter.sendMail(mailOptions);
};