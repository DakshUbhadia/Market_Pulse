<div align="center">
<img src="https://drive.google.com/uc?export=view&id=18VTtRD7qG4a0Cvj7UpisRHbh60gMZ-TM" alt="Banner" width="100%" />
  <br />

  <h1>📈 Market Pulse</h1>
  <p>
    <b>Real-time market dashboards, watchlists, alerts, and AI-generated email digests.</b>
    <br />
    <i>Built with Next.js 16 App Router, Tailwind v4, and MongoDB.</i>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Next.js-16.0-black?logo=next.js&logoColor=white&style=flat-square" alt="Next.js">
    <img src="https://img.shields.io/badge/TypeScript-5.0-3178C6?logo=typescript&logoColor=white&style=flat-square" alt="TypeScript">
    <img src="https://img.shields.io/badge/Maintained-Yes-success?style=flat-square" alt="Maintained">
  </p>

  <p>
    <a href="#-overview">Overview</a> •
    <a href="#-key-features">Key Features</a> •
    <a href="#-tech-stack">Tech Stack</a> •
    <a href="#-getting-started">Getting Started</a> •
    <a href="#-environment-variables">Env Variables</a> •
    <a href="#-deployment">Deployment</a>
  </p>
</div>

---

## 📋 Overview

**Market Pulse** is a high-performance financial dashboard designed to eliminate the noise of stock monitoring. Built for speed and clarity, it leverages the **Next.js App Router** and **Server-Sent Events (SSE)** to deliver real-time data without the bloat.

Users can create custom watchlists, set price alerts, and receive **AI-curated email summaries** (powered by Gemini) to stay ahead of the market. The application features a "zero-flash" user experience, using a blurred loader overlay to ensure smooth transitions between data-heavy views.

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| 🔐 **Secure Auth** | Robust Email/Password authentication using **Better Auth** with secure session cookies. |
| 🛡️ **Protected Shell** | Middleware-protected routes ensure unauthorized users cannot access the dashboard. |
| ⚡ **Real-Time Stream** | Custom **SSE (Server-Sent Events)** endpoint streams batched price updates instantly. |
| 📉 **Interactive Charts** | Embedded **TradingView** widgets for Heatmaps, Tickers, and Technical Analysis. |
| 🤖 **AI Workflows** | **Gemini AI** generates personalized daily news digests and welcome emails via **Inngest**. |
| 🔔 **Smart Alerts** | Configure price thresholds to receive instant email notifications via **Nodemailer**. |
| 💨 **Optimized UX** | Full-page blurred loader overlay prevents layout shifts during hydration. |

---

## 🛠 Tech Stack

### Framework & UI
![Next.js](https://img.shields.io/badge/Next.js_16-black?style=for-the-badge&logo=next.js&logoColor=white)
![React](https://img.shields.io/badge/React_19-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS_v4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![shadcn/ui](https://img.shields.io/badge/shadcn/ui-111827?style=for-the-badge&logo=radix-ui&logoColor=white)

### Backend & Database
![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white)
![Better Auth](https://img.shields.io/badge/Better_Auth-FF5722?style=for-the-badge&logo=auth0&logoColor=white)
![Inngest](https://img.shields.io/badge/Inngest-0A0A0A?style=for-the-badge&logo=inngest&logoColor=white)

### AI & Tools
![Gemini AI](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=googlebard&logoColor=white)
![Finnhub](https://img.shields.io/badge/Finnhub_API-1db954?style=for-the-badge&logo=finnhub&logoColor=white)
![Nodemailer](https://img.shields.io/badge/Nodemailer-007ACC?style=for-the-badge&logo=gmail&logoColor=white)

### Technology Details

* **Next.js:** A powerful React framework for building full-stack web applications with server-side rendering and API routes.
* **TypeScript:** A statically typed superset of JavaScript that improves code quality, tooling, and error detection.
* **Better Auth:** A framework-agnostic authentication library providing built-in support for email/password and social sign-on.
* **Inngest:** A platform for event-driven workflows and background jobs (used here for AI workflows and alerts).
* **MongoDB:** A flexible, high-performance NoSQL database for storing user data and watchlists.
* **Finnhub:** A real-time financial data API providing stock market data, economic indicators, and news.
* **Gemini AI:** Google's AI model used to generate smart email digests and summaries.
* **CodeRabbit:** An AI-powered code review assistant that integrates with GitHub to enforce best practices.
* **Nodemailer:** A Node.js library for handling transactional emails and notifications.
* **TailwindCSS & Shadcn:** Utility-first CSS framework and accessible component library for rapid UI development.

---

## 📂 Project Structure

```text
market-pulse/
├── public/
│   └── assets/              # Images, icons, branding
│
├── scripts/                 # Setup & DB test scripts
│
├── src/
│   ├── app/                 # Next.js App Router
│   │   ├── (auth)/          # Authentication pages
│   │   ├── (root)/          # Protected pages (Dashboard, Watchlist, Stock)
│   │   ├── api/             # Auth, SSE, Inngest APIs
│   │   └── landing/         # Marketing / landing page
│   │
│   ├── components/          # UI & feature components
│   │   ├── ui/              # Reusable UI (shadcn-based)
│   │   ├── watchlist/       # Watchlist & alerts UI
│   │   └── landing/         # Landing page sections
│   │
│   ├── database/            # Mongoose models & connection
│   ├── lib/                 # Auth, AI, email, utilities
│   ├── context/             # Global state (Watchlist)
│   └── middleware/          # Route protection
│
├── .env                     # Environment variables
├── next.config.ts
├── package.json
└── README.md

```

### Key API Routes

* `/api/quotes/stream`: Handles SSE streaming for real-time batched price updates.
* `/api/inngest`: Handles background jobs (AI email generation, Cron schedules) without affecting user experience.
* `/api/auth/*`: Better Auth handler.

---

## 🚀 Getting Started

Follow these steps to run Market Pulse on your local machine.

### 1. Install Dependencies

Clone the repository and install packages.

```bash
git clone [https://github.com/your-username/market-pulse.git](https://github.com/your-username/market-pulse.git)
cd market-pulse
npm install

```

*Note: A postinstall script will run automatically to patch specific TS configurations.*

### 2. Configure Environment

Create a `.env` file in the root directory and fill in the required variables (see below).

### 3. Run Development Server

```bash
npm run dev

```

Open [http://localhost:3000](https://www.google.com/search?q=http://localhost:3000) with your browser.

### 4. (Optional) Run Inngest

To test AI workflows and background jobs locally:

```bash
npx inngest-cli@latest dev

```

### 5. (Optional) Test Database Connectivity

```bash
node scripts/test-db.js

```

---

## 🔑 Environment Variables

Create a `.env` file in the root directory:

| Variable | Description |
| --- | --- |
| `MONGODB_URI` | Connection string for MongoDB Atlas. |
| `MONGODB_DB_NAME` | Database name (e.g., `market-pulse`). |
| `BETTER_AUTH_SECRET` | A secure random string used to sign session tokens. |
| `NEXT_PUBLIC_FINNHUB_API_KEY` | API Key from Finnhub (for market data/news). |
| `GEMINI_API_KEY` | Google Gemini API Key (for AI email summaries). |
| `NODEMAILER_EMAIL` | Gmail address used to send alerts. |
| `NODEMAILER_PASSWORD` | Gmail App Password (recommended). |
| `BETTER_AUTH_URL` | (Optional) Server-side base URL. |

---

## 🚢 Deployment

This project is optimized for **Vercel**.

1. **Push to GitHub:** Commit your changes to your `main` branch.
2. **Import to Vercel:** Connect your repository in the Vercel Dashboard.
3. **Add Environment Variables:** Copy your `.env` values into Vercel's "Environment Variables" settings.
4. **Deploy:** Click deploy.

---

## 📄 Scripts

* `npm run dev`: Start Next.js in development mode.
* `npm run build`: Build the application for production.
* `npm run start`: Start the production server.
* `npm run lint`: Run ESLint checks.

---

## 🙏 Acknowledgments

* [TradingView](https://www.tradingview.com/) for the powerful charting widgets.
* [Finnhub](https://finnhub.io/) for the reliable financial data API.
* [Better Auth](https://www.better-auth.com/) for the seamless authentication experience.
* [Inngest](https://www.inngest.com/) for making serverless queues and AI workflows easy.
