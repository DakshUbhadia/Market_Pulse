"use client";
import React from "react";
import Link from "next/link";
import Image from "next/image";

const LandingHeader = () => {
  return (
    <header
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        padding: "16px 20px",
        background: "rgba(10, 10, 10, 0.9)",
        backdropFilter: "blur(10px)",
        borderBottom: "1px solid rgba(212, 175, 55, 0.1)",
      }}
    >
      <div
        style={{
          maxWidth: "1200px",
          margin: "0 auto",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        {/* Logo */}
        <Link
          href="/landing"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            textDecoration: "none",
          }}
        >
          <Image
            src="/assets/images/Logo.png"
            alt="Market Pulse Logo"
            width={36}
            height={36}
            style={{
              borderRadius: "8px",
            }}
          />
          <span
            style={{
              color: "#fff",
              fontWeight: 700,
              fontSize: "1.2rem",
            }}
          >
            Market<span style={{ color: "#D4AF37" }}>Pulse</span>
          </span>
        </Link>

        {/* Navigation */}
        <nav
          style={{
            display: "flex",
            alignItems: "center",
            gap: "32px",
          }}
        >
          <Link
            href="/sign-in"
            style={{
              color: "#D4AF37",
              textDecoration: "none",
              fontSize: "0.9rem",
              fontWeight: 500,
            }}
          >
            Sign In
          </Link>
          <Link
            href="/sign-up"
            className="btn-gold"
            style={{
              padding: "10px 20px",
              fontSize: "0.9rem",
            }}
          >
            Get Started
          </Link>
        </nav>
      </div>
    </header>
  );
};

export default LandingHeader;
