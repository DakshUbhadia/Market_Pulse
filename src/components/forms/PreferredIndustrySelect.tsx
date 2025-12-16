"use client";
import React from "react";

export interface Industry {
  value: string;
  label: string;
  icon: string;
}

export const INDUSTRIES: Industry[] = [
  { value: "technology", label: "Technology", icon: "" },
  { value: "healthcare", label: "Healthcare", icon: "" },
  { value: "finance", label: "Finance", icon: "" },
  { value: "energy", label: "Energy", icon: "" },
  { value: "consumer", label: "Consumer Goods", icon: "" },
  { value: "real-estate", label: "Real Estate", icon: "" },
  { value: "industrials", label: "Industrials", icon: "" },
  { value: "materials", label: "Materials", icon: "" },
  { value: "utilities", label: "Utilities", icon: "" },
  { value: "telecom", label: "Telecommunications", icon: "" },
  { value: "crypto", label: "Cryptocurrency", icon: "" },
  { value: "all", label: "All Industries", icon: "" },
];

interface PreferredIndustrySelectProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

const PreferredIndustrySelect: React.FC<PreferredIndustrySelectProps> = ({ value, onChange, className = "" }) => {
  return (
    <div className={`select-group ${className}`}>
      <label className="select-label">Preferred Industry</label>
      <div className="select-wrapper">
        <div className="select-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M2 20h20M5 20V10h4v10M10 20V4h4v16M15 20v-6h4v6" />
          </svg>
        </div>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="auth-select"
        >
          <option value="">Select Industry</option>
          {INDUSTRIES.map((industry) => (
            <option key={industry.value} value={industry.value}>
              {industry.icon} {industry.label}
            </option>
          ))}
        </select>
        <div className="select-arrow">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </div>
    </div>
  );
};

export default PreferredIndustrySelect;
