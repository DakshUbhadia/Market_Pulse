"use client";
import React from "react";

export interface InvestmentGoal {
  value: string;
  label: string;
  description: string;
}

export const INVESTMENT_GOALS: InvestmentGoal[] = [
  { value: "growth", label: "Growth", description: "Focus on capital appreciation" },
  { value: "income", label: "Income", description: "Generate regular dividends" },
  { value: "preservation", label: "Preservation", description: "Protect existing wealth" },
  { value: "speculation", label: "Speculation", description: "High-risk trading" },
  { value: "balanced", label: "Balanced", description: "Mix of growth and income" },
  { value: "retirement", label: "Retirement", description: "Long-term wealth building" },
];

interface InvestmentGoalsSelectProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

const InvestmentGoalsSelect: React.FC<InvestmentGoalsSelectProps> = ({ value, onChange, className = "" }) => {
  return (
    <div className={`select-group ${className}`}>
      <label className="select-label">Investment Goals</label>
      <div className="select-wrapper">
        <div className="select-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
          </svg>
        </div>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="auth-select"
        >
          <option value="">Select Goal</option>
          {INVESTMENT_GOALS.map((goal) => (
            <option key={goal.value} value={goal.value}>
              {goal.label}
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

export default InvestmentGoalsSelect;
