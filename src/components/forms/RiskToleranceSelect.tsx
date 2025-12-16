"use client";
import React from "react";

export interface RiskLevel {
  value: string;
  label: string;
  color: string;
}

export const RISK_LEVELS: RiskLevel[] = [
  { value: "low", label: "Low", color: "#10b981" },
  { value: "medium", label: "Medium", color: "#f59e0b" },
  { value: "high", label: "High", color: "#ef4444" },
  { value: "aggressive", label: "Aggressive", color: "#dc2626" },
];

interface RiskToleranceSelectProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

const RiskToleranceSelect: React.FC<RiskToleranceSelectProps> = ({ value, onChange, className = "" }) => {
  return (
    <div className={`select-group ${className}`}>
      <label className="select-label">Risk Tolerance</label>
      <div className="select-wrapper">
        <div className="select-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        </div>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="auth-select"
        >
          <option value="">Select Risk Level</option>
          {RISK_LEVELS.map((level) => (
            <option key={level.value} value={level.value}>
              {level.label}
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

export default RiskToleranceSelect;
