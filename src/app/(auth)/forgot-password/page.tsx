"use client";
import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import TradingLoader from "@/components/ui/TradingLoader";
import FullPageTradingLoader from "@/components/ui/FullPageTradingLoader";
import { sendPasswordResetOtp } from "@/lib/actions/auth.actions";
import { toast } from "sonner";

const ForgotPasswordPage = () => {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email) {
      toast.error("Please enter your email address");
      return;
    }

    setIsLoading(true);
    try {
      const result = await sendPasswordResetOtp({ email });
      
      if (result.success) {
        toast.success("Verification code sent to your email");
        router.push(`/verify-otp?email=${encodeURIComponent(email)}&type=forgot-password`);
      } else {
        toast.error(result.error || "Failed to send verification code");
      }
    } catch {
      toast.error("An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <FullPageTradingLoader show={isLoading} label="Sending verification code..." />
      <form onSubmit={handleSubmit} className="auth-form">
      <div className="form-header">
        <div className="form-loader">
          <TradingLoader size={70} />
        </div>
        <h1>Forgot Password</h1>
        <p>Enter your email to receive a verification code</p>
      </div>

      {/* Info Box */}
      <div style={{
        background: "rgba(212, 175, 55, 0.1)",
        border: "1px solid rgba(212, 175, 55, 0.2)",
        borderRadius: "12px",
        padding: "16px",
        marginBottom: "24px"
      }}>
        <p style={{ color: "#9ca3af", fontSize: "0.9rem", margin: 0, lineHeight: "1.5" }}>
          <svg 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="#D4AF37" 
            strokeWidth="2" 
            style={{ width: "18px", height: "18px", display: "inline", marginRight: "8px", verticalAlign: "middle" }}
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4M12 8h.01" />
          </svg>
          We&apos;ll send you a 6-digit verification code to confirm your identity before you can reset your password.
        </p>
      </div>

      {/* Email Field */}
      <div className="input-group">
        <div className="input-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
            <polyline points="22,6 12,13 2,6" />
          </svg>
        </div>
        <input
          type="email"
          name="email"
          placeholder="Email Address"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <div className="input-highlight"></div>
      </div>

      {/* Submit Button */}
      <button 
        type="submit" 
        className={`submit-btn ${isLoading ? "loading" : ""}`} 
        disabled={isLoading}
      >
        <>
          <span className="btn-text">Send Verification Code</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </>
      </button>

      {/* Back to Sign In */}
      <div className="mobile-toggle">
        <p>Remember your password?</p>
        <Link href="/sign-in">Sign In</Link>
      </div>
      </form>
    </>
  );
};

export default ForgotPasswordPage;
