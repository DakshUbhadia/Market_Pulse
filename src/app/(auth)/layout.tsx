import React from "react";
import "./auth.css";
import AuthShell from "./AuthShell";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <AuthShell>{children}</AuthShell>;
}
