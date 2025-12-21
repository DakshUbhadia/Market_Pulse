"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import TradingLoader from "@/components/ui/TradingLoader";
import FullPageTradingLoader from "@/components/ui/FullPageTradingLoader";
import { authClient } from "@/lib/auth-client";

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
      const { data, error } = await authClient.signIn.email({
        email: formData.email.trim().toLowerCase(),
        password: formData.password,
      });

      if (data?.user && !error) {
        toast.success("Signed in successfully");
        router.replace("/dashboard");
      } else {
        toast.error((error as { message?: string } | null)?.message || "Failed to sign in");
      }
    } catch {
      toast.error("An unexpected error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
  <>
    {/* Full Screen Loader overlay */}
    <FullPageTradingLoader show={isLoading} label="Signing you in..." />

    {/* 'centered' class keeps this form vertically centered */}
    <form onSubmit={handleSubmit} className="auth-form centered">
      <div className="form-header">
        <div className="form-loader">
          <TradingLoader size={60} />
        </div>
        <h1>Welcome Back</h1>
        <p>Continue your trading journey</p>
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

      {/*Forgot Password */}
      <div className="form-options">
        <a href="/forgot-password" className="forgot-password">Forgot Password?</a>
      </div>

      {/* Submit Button */}
      <button type="submit" className={`submit-btn ${isLoading ? "loading" : ""}`} disabled={isLoading}>
        {isLoading ? (
           <span className="btn-text">Signing In...</span>
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
      <div className="mobile-toggle" style={{marginTop: '20px'}}>
        <p style={{color: '#9ca3af', fontSize: '0.9rem', marginBottom: '5px'}}>Don&apos;t have an account?</p>
        <Link href="/sign-up" style={{color: '#D4AF37', textDecoration: 'none', fontWeight: '500'}}>Create Account</Link>
      </div>
    </form>
  </>
  );
};

export default SignInPage;
