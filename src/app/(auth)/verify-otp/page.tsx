"use client";
import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import TradingLoader from "@/components/ui/TradingLoader";
import FullPageTradingLoader from "@/components/ui/FullPageTradingLoader";
import { sendOtp, signUpWithEmail, verifyOtp } from "@/lib/actions/auth.actions";
import { authClient } from "@/lib/auth-client";
import { toast } from "sonner";

const VerifyOtpContent = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const email = searchParams.get("email") || "";
  const name = searchParams.get("name") || "";
  const password = searchParams.get("password") || "";
  const country = searchParams.get("country") || "";
  const investmentGoals = searchParams.get("investmentGoals") || "";
  const riskTolerance = searchParams.get("riskTolerance") || "";
  const preferredIndustry = searchParams.get("preferredIndustry") || "";
  const type = searchParams.get("type") || "signup"; // signup or forgot-password

  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [timer, setTimer] = useState(20);
  const [isLoading, setIsLoading] = useState(false);
  const [canResend, setCanResend] = useState(false);

  useEffect(() => {
    if (!email) {
      router.push("/sign-up");
      return;
    }
  }, [email, router]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (timer > 0) {
      interval = setInterval(() => {
        setTimer((prev) => {
          if (prev <= 1) {
            setCanResend(true);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [timer]);

  const handleOtpChange = (index: number, value: string) => {
    if (value.length > 1) return;
    if (!/^\d*$/.test(value)) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // Auto-focus next input
    if (value && index < 5) {
      const nextInput = document.getElementById(`otp-${index + 1}`);
      nextInput?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      const prevInput = document.getElementById(`otp-${index - 1}`);
      prevInput?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").slice(0, 6);
    if (!/^\d+$/.test(pastedData)) return;
    
    const newOtp = [...otp];
    for (let i = 0; i < pastedData.length; i++) {
      newOtp[i] = pastedData[i];
    }
    setOtp(newOtp);
  };

  const handleResendOtp = async () => {
    if (!canResend) return;
    
    setIsLoading(true);
    try {
      const result = await sendOtp({ email, name });
      if (result.success) {
        toast.success("New verification code sent to your email");
        setTimer(20);
        setCanResend(false);
        setOtp(["", "", "", "", "", ""]);
      } else {
        toast.error(result.error || "Failed to resend verification code");
      }
    } catch {
      toast.error("An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const otpString = otp.join("");
    
    if (otpString.length !== 6) {
      toast.error("Please enter the complete verification code");
      return;
    }

    setIsLoading(true);
    try {
      if (type === "signup") {
        const result = await signUpWithEmail({
          email,
          password,
          fullName: name,
          country,
          investmentGoals,
          riskTolerance,
          preferredIndustry,
          otp: otpString
        });

        if (result.success) {
          toast.success("Account created successfully!");
          // Ensure a browser-side sign-in so the session cookie is set on Vercel.
          const { data, error } = await authClient.signIn.email({
            email: email.trim().toLowerCase(),
            password,
          });

          if (data?.user && !error) {
            router.replace("/dashboard");
          } else {
            toast.error("Account created, but auto sign-in failed. Please sign in.");
            router.replace("/sign-in");
          }
        } else {
          toast.error(result.error || "Invalid verification code");
        }
      } else if (type === "forgot-password") {
        const result = await verifyOtp({ email, otp: otpString });
        if (result.success) {
          toast.success("Email verified! Now set your new password.");
          router.push(`/reset-password?email=${encodeURIComponent(email)}&token=${encodeURIComponent(otpString)}`);
        } else {
          toast.error(result.error || "Invalid verification code");
        }
      }
    } catch {
      toast.error("An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <FullPageTradingLoader show={isLoading} label={type === "signup" ? "Creating account..." : "Verifying code..."} />
      <form onSubmit={handleSubmit} className="auth-form">
      <div className="form-header">
        <div className="form-loader">
          <TradingLoader size={70} />
        </div>
        <h1>Verify Your Email</h1>
        <p>
          Enter the 6-digit code sent to<br />
          <strong style={{ color: "#D4AF37" }}>{email}</strong>
        </p>
      </div>

      {/* OTP Input Fields */}
      <div className="otp-inputs" style={{ 
        display: "flex", 
        gap: "10px", 
        justifyContent: "center", 
        margin: "30px 0" 
      }}>
        {otp.map((digit, index) => (
          <input
            key={index}
            id={`otp-${index}`}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={digit}
            onChange={(e) => handleOtpChange(index, e.target.value)}
            onKeyDown={(e) => handleKeyDown(index, e)}
            onPaste={handlePaste}
            style={{
              width: "50px",
              height: "60px",
              textAlign: "center",
              fontSize: "1.5rem",
              fontWeight: "bold",
              background: "transparent",
              border: digit ? "2px solid #D4AF37" : "1px solid rgba(212, 175, 55, 0.3)",
              borderRadius: "12px",
              color: "#F1D27B",
              outline: "none",
              transition: "all 0.3s ease"
            }}
          />
        ))}
      </div>

      {/* Timer and Resend */}
      <div style={{ textAlign: "center", marginBottom: "30px" }}>
        {!canResend ? (
          <p style={{ color: "#6b7280", fontSize: "0.9rem" }}>
            Resend code in <span style={{ color: "#D4AF37", fontWeight: "600" }}>{timer}s</span>
          </p>
        ) : (
          <button
            type="button"
            onClick={handleResendOtp}
            disabled={isLoading}
            style={{
              background: "none",
              border: "none",
              color: "#D4AF37",
              cursor: "pointer",
              fontSize: "0.95rem",
              textDecoration: "underline",
              fontWeight: "500"
            }}
          >
            Resend Verification Code
          </button>
        )}
      </div>

      {/* Submit Button */}
      <button 
        type="submit" 
        className={`submit-btn ${isLoading ? "loading" : ""}`} 
        disabled={isLoading || otp.join("").length !== 6}
      >
        <>
          <span className="btn-text">
            {type === "signup" ? "Verify & Create Account" : "Verify Email"}
          </span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </>
      </button>

      {/* Back Link */}
      <div className="mobile-toggle">
        <p>Wrong email?</p>
        <Link href={type === "signup" ? "/sign-up" : "/forgot-password"}>Go Back</Link>
      </div>
      </form>
    </>
  );
};

const VerifyOtpPage = () => {
  return (
    <Suspense fallback={
      <div className="auth-form" style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "400px" }}>
        <TradingLoader size={70} />
      </div>
    }>
      <VerifyOtpContent />
    </Suspense>
  );
};

export default VerifyOtpPage;
