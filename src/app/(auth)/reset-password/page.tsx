"use client";
import React, { useState, useMemo, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import TradingLoader from "@/components/ui/TradingLoader";
import FullPageTradingLoader from "@/components/ui/FullPageTradingLoader";
import { resetPassword, verifyOtp } from "@/lib/actions/auth.actions";
import { toast } from "sonner";

const ResetPasswordContent = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const email = searchParams.get("email") || "";
  const token = searchParams.get("token") || "";

  const [formData, setFormData] = useState({
    password: "",
    confirmPassword: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isValidating, setIsValidating] = useState(true);

  useEffect(() => {
    const validateToken = async () => {
      if (!email || !token) {
        toast.error("Invalid reset link. Please try again.");
        router.push("/forgot-password");
        return;
      }
      
      // Verify the OTP token is still valid
      const result = await verifyOtp({ email, otp: token });
      if (!result.success) {
        toast.error("Reset link has expired. Please request a new one.");
        router.push("/forgot-password");
        return;
      }
      
      setIsValidating(false);
    };
    
    validateToken();
  }, [email, token, router]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // Password strength calculation
  const passwordStrength = useMemo(() => {
    const password = formData.password;
    if (!password) return { strength: 0, text: "", class: "" };
    
    let strength = 0;
    if (password.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    
    if (strength <= 1) return { strength: 1, text: "Weak", class: "weak" };
    if (strength === 2) return { strength: 2, text: "Medium", class: "medium" };
    if (strength === 3) return { strength: 3, text: "Strong", class: "medium" };
    return { strength: 4, text: "Very Strong", class: "strong" };
  }, [formData.password]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    if (formData.password.length < 8) {
      toast.error("Password must be at least 8 characters long");
      return;
    }

    setIsLoading(true);
    try {
      const result = await resetPassword({
        email,
        newPassword: formData.password,
        token
      });

      if (result.success) {
        toast.success("Password reset successfully! Please sign in with your new password.");
        router.push("/sign-in");
      } else {
        toast.error(result.error || "Failed to reset password");
      }
    } catch {
      toast.error("An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isValidating) {
    return (
      <>
        <FullPageTradingLoader show={true} label="Validating reset link..." />
        <div className="auth-form" style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "400px" }} />
      </>
    );
  }

  return (
    <>
      <FullPageTradingLoader show={isLoading} label="Resetting password..." />
      <form onSubmit={handleSubmit} className="auth-form">
      <div className="form-header">
        <div className="form-loader">
          <TradingLoader size={70} />
        </div>
        <h1>Reset Password</h1>
        <p>Create a new password for your account</p>
      </div>

      {/* Email Display */}
      <div style={{
        background: "rgba(212, 175, 55, 0.05)",
        border: "1px solid rgba(212, 175, 55, 0.2)",
        borderRadius: "12px",
        padding: "14px 16px",
        marginBottom: "24px",
        display: "flex",
        alignItems: "center",
        gap: "12px"
      }}>
        <svg viewBox="0 0 24 24" fill="none" stroke="#D4AF37" strokeWidth="2" style={{ width: "20px", height: "20px", flexShrink: 0 }}>
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
        <span style={{ color: "#e5e7eb", fontSize: "0.95rem" }}>{email}</span>
      </div>

      {/* New Password Field */}
      <div className="input-group">
        <div className="input-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0110 0v4" />
          </svg>
        </div>
        <input
          type={showPassword ? "text" : "password"}
          name="password"
          placeholder="New Password"
          value={formData.password}
          onChange={handleChange}
          required
          minLength={8}
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setShowPassword(!showPassword)}
        >
          {showPassword ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
        <div className="input-highlight"></div>
      </div>

      {/* Password Strength Indicator */}
      {formData.password && (
        <div className="password-strength">
          <div className="strength-bars">
            {[1, 2, 3, 4].map((level) => (
              <div
                key={level}
                className={`strength-bar ${level <= passwordStrength.strength ? `active ${passwordStrength.class}` : ""}`}
              />
            ))}
          </div>
          <span className={`strength-text ${passwordStrength.class}`}>
            {passwordStrength.text}
          </span>
        </div>
      )}

      {/* Confirm Password Field */}
      <div className="input-group">
        <div className="input-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        </div>
        <input
          type={showConfirmPassword ? "text" : "password"}
          name="confirmPassword"
          placeholder="Confirm New Password"
          value={formData.confirmPassword}
          onChange={handleChange}
          required
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
        >
          {showConfirmPassword ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
        <div className="input-highlight"></div>
      </div>

      {/* Password Match Indicator */}
      {formData.confirmPassword && (
        <div style={{ 
          display: "flex", 
          alignItems: "center", 
          gap: "8px", 
          marginBottom: "20px",
          color: formData.password === formData.confirmPassword ? "#D4AF37" : "#ef4444",
          fontSize: "0.85rem"
        }}>
          {formData.password === formData.confirmPassword ? (
            <>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: "16px", height: "16px" }}>
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Passwords match
            </>
          ) : (
            <>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: "16px", height: "16px" }}>
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
              Passwords do not match
            </>
          )}
        </div>
      )}

      {/* Submit Button */}
      <button 
        type="submit" 
        className={`submit-btn ${isLoading ? "loading" : ""}`} 
        disabled={isLoading || formData.password !== formData.confirmPassword}
      >
        <>
          <span className="btn-text">Reset Password</span>
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

const ResetPasswordPage = () => {
  return (
    <Suspense fallback={
      <div className="auth-form" style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "400px" }}>
        <TradingLoader size={70} />
      </div>
    }>
      <ResetPasswordContent />
    </Suspense>
  );
};

export default ResetPasswordPage;
