"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import TradingLoader from "@/components/ui/TradingLoader";
import { signInWithEmail } from "@/lib/actions/auth.actions";

const SignInPage = () => {
  const router = useRouter();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const result = await signInWithEmail({
        email: formData.email,
        password: formData.password,
      });

      if (result.success) {
        toast.success("Signed in successfully");
        router.push("/dashboard");
      } else {
        toast.error(result.error || "Failed to sign in");
      }
    } catch {
      toast.error("An unexpected error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <div className="form-header">
        {/* Trading Loader Animation */}
        <div className="form-loader">
          <TradingLoader size={70} />
        </div>
        <h1>Welcome Back</h1>
        <p>Sign in to access your trading dashboard</p>
      </div>

      <div className="divider">
        <span>Continue with email</span>
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
          value={formData.email}
          onChange={handleChange}
          required
        />
        <div className="input-highlight"></div>
      </div>

      {/* Password Field */}
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
          placeholder="Password"
          value={formData.password}
          onChange={handleChange}
          required
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

      {/* Form Options */}
      <div className="form-options">
        <label className="remember-me">
          <input type="checkbox" />
          <span>Remember me</span>
        </label>
        <Link href="/forgot-password" className="forgot-password">
          Forgot Password?
        </Link>
      </div>

      {/* Submit Button */}
      <button type="submit" className={`submit-btn ${isLoading ? "loading" : ""}`} disabled={isLoading}>
        {isLoading ? (
          <div className="btn-loader">
            <TradingLoader size={40} />
          </div>
        ) : (
          <>
            <span className="btn-text">Sign In</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </>
        )}
      </button>

      {/* Mobile Toggle */}
      <div className="mobile-toggle">
        <p>Don&apos;t have an account?</p>
        <Link href="/sign-up">Create Account</Link>
      </div>
    </form>
  );
};

export default SignInPage;
