"use client";
import React from "react";

export interface Country {
  code: string;
  name: string;
  flag: string;
}

export const COUNTRIES: Country[] = [
  { code: "US", name: "United States", flag: "🇺🇸" },
  { code: "GB", name: "United Kingdom", flag: "🇬🇧" },
  { code: "CA", name: "Canada", flag: "🇨🇦" },
  { code: "AU", name: "Australia", flag: "🇦🇺" },
  { code: "DE", name: "Germany", flag: "🇩🇪" },
  { code: "FR", name: "France", flag: "🇫🇷" },
  { code: "JP", name: "Japan", flag: "🇯🇵" },
  { code: "IN", name: "India", flag: "🇮🇳" },
  { code: "SG", name: "Singapore", flag: "🇸🇬" },
  { code: "AE", name: "United Arab Emirates", flag: "🇦🇪" },
  { code: "CH", name: "Switzerland", flag: "🇨🇭" },
  { code: "NL", name: "Netherlands", flag: "🇳🇱" },
  { code: "HK", name: "Hong Kong", flag: "🇭🇰" },
  { code: "BR", name: "Brazil", flag: "🇧🇷" },
  { code: "MX", name: "Mexico", flag: "🇲🇽" },
  { code: "KR", name: "South Korea", flag: "🇰🇷" },
  { code: "ES", name: "Spain", flag: "🇪🇸" },
  { code: "IT", name: "Italy", flag: "🇮🇹" },
  { code: "SE", name: "Sweden", flag: "🇸🇪" },
  { code: "NZ", name: "New Zealand", flag: "🇳🇿" },
];

interface CountrySelectProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

const CountrySelect: React.FC<CountrySelectProps> = ({ value, onChange, className = "" }) => {
  const selectedCountry = COUNTRIES.find((c) => c.code === value);

  return (
    <div className={`select-group ${className}`}>
      <label className="select-label">Country</label>
      <div className="select-wrapper">
        <div className="select-icon">
          {selectedCountry ? (
            <span className="country-flag">{selectedCountry.flag}</span>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
          )}
        </div>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="auth-select"
        >
          <option value="">Select Country</option>
          {COUNTRIES.map((country) => (
            <option key={country.code} value={country.code}>
              {country.flag} {country.name}
            </option>
          ))}
        </select>
        <div className="select-arrow">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </div>
      <p className="select-hint">Helps us show market data and news relevant to you.</p>
    </div>
  );
};

export default CountrySelect;
