"use client";
import React, { useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import TradingLoader from "@/components/ui/TradingLoader";
import FullPageTradingLoader from "@/components/ui/FullPageTradingLoader";
import CountrySelect from "@/components/forms/CountrySelect";
import InvestmentGoalsSelect from "@/components/forms/InvestmentGoalsSelect";
import RiskToleranceSelect from "@/components/forms/RiskToleranceSelect";
import PreferredIndustrySelect from "@/components/forms/PreferredIndustrySelect";
import { sendOtp } from "@/lib/actions/auth.actions";
import { toast } from "sonner";

const SignUpPage = () => {
  const router = useRouter();
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    password: "",
    confirmPassword: "",
    country: "",
    investmentGoal: "",
    riskTolerance: "",
    preferredIndustry: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [agreeToTerms, setAgreeToTerms] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSelectChange = (field: string) => (value: string) => {
    setFormData({ ...formData, [field]: value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agreeToTerms) {
      toast.error("Please agree to the Terms of Service and Privacy Policy");
      return;
    }
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
      // Send OTP and redirect to verify-otp page
      const result = await sendOtp({ email: formData.email, name: formData.fullName });
      
      if (result.success) {
        toast.success("Verification code sent to your email");
        // Build query string with all form data
        const params = new URLSearchParams({
          email: formData.email,
          name: formData.fullName,
          password: formData.password,
          country: formData.country,
          investmentGoals: formData.investmentGoal,
          riskTolerance: formData.riskTolerance,
          preferredIndustry: formData.preferredIndustry,
          type: "signup"
        });
        router.push(`/verify-otp?${params.toString()}`);
      } else {
        toast.error(result.error || "Failed to send verification code");
      }
    } catch {
      toast.error("An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
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

  return (
  <>
    {/* Full Screen Loader overlay (if needed) */}
    <FullPageTradingLoader show={isLoading} label="Creating your account..." />

    <form onSubmit={handleSubmit} className="auth-form">
      <div className="form-header">
        {/* Trading Loader Animation - Positioned at top */}
        <div className="form-loader">
          {/* Ensure your TradingLoader component accepts width/height or uses styles */}
          <TradingLoader size={70} /> 
        </div>
        <h1>Create Account</h1>
        <p>Start your trading journey today</p>
      </div>

      <div className="divider">
        <span>Register details</span>
      </div>

      {/* Full Name Field */}
      <div className="input-group">
        <div className="input-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </div>
        <input
          type="text"
          name="fullName"
          placeholder="Full Name"
          value={formData.fullName}
          onChange={handleChange}
          required
        />
        <div className="input-highlight"></div>
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
          placeholder="Confirm Password"
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

      {/* Investment Profile Section */}
      <div className="investment-profile-section">
        <div className="section-divider">
          <span>Investment Profile</span>
        </div>
        
        <CountrySelect
          value={formData.country}
          onChange={handleSelectChange("country")}
        />

        <InvestmentGoalsSelect
          value={formData.investmentGoal}
          onChange={handleSelectChange("investmentGoal")}
        />

        <RiskToleranceSelect
          value={formData.riskTolerance}
          onChange={handleSelectChange("riskTolerance")}
        />

        <PreferredIndustrySelect
          value={formData.preferredIndustry}
          onChange={handleSelectChange("preferredIndustry")}
        />
      </div>

      {/* Terms Agreement */}
      <div className="terms-agreement">
        <label>
          <input
            type="checkbox"
            checked={agreeToTerms}
            onChange={(e) => setAgreeToTerms(e.target.checked)}
          />
          <span>
            I agree to the <Link href="/terms">Terms of Service</Link> and{" "}
            <Link href="/privacy">Privacy Policy</Link>
          </span>
        </label>
      </div>

      {/* Submit Button */}
      <button type="submit" className={`submit-btn ${isLoading ? "loading" : ""}`} disabled={isLoading}>
        {isLoading ? (
           <span className="btn-text">Processing...</span>
        ) : (
           <>
             <span className="btn-text">Create Account</span>
             <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
               <path d="M5 12h14M12 5l7 7-7 7" />
             </svg>
           </>
        )}
      </button>

      {/* Mobile Toggle */}
      <div className="mobile-toggle">
        <p>Already have an account?</p>
        <Link href="/sign-in">Sign In</Link>
      </div>
    </form>
  </>
  );
};

export default SignUpPage;
