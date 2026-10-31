import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Footer } from "../Footer";

describe("Footer Component", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("renders OpenAPI Swagger link in development environment", () => {
    vi.stubEnv("NODE_ENV", "development");
    render(<Footer lang="en" />);

    expect(screen.getByText("OpenAPI Swagger")).toBeInTheDocument();
    expect(screen.getByText("Terms of Service")).toBeInTheDocument();
    expect(screen.getByText("Privacy Policy")).toBeInTheDocument();
    expect(screen.getByText("DMCA Takedown")).toBeInTheDocument();
  });

  it("hides OpenAPI Swagger link when NODE_ENV is production", () => {
    vi.stubEnv("NODE_ENV", "production");
    render(<Footer lang="en" />);

    expect(screen.queryByText("OpenAPI Swagger")).not.toBeInTheDocument();
    expect(screen.getByText("Terms of Service")).toBeInTheDocument();
    expect(screen.getByText("Privacy Policy")).toBeInTheDocument();
    expect(screen.getByText("DMCA Takedown")).toBeInTheDocument();
  });

  it("renders Bengali legal notices and links when lang is bn", () => {
    vi.stubEnv("NODE_ENV", "production");
    render(<Footer lang="bn" />);

    expect(screen.queryByText("OpenAPI Swagger")).not.toBeInTheDocument();
    expect(screen.getByText("ব্যবহারের নিয়মাবলী")).toBeInTheDocument();
    expect(screen.getByText("গোপনীয়তা নীতি")).toBeInTheDocument();
    expect(screen.getByText("DMCA কপিরাইট নোটিশ")).toBeInTheDocument();
    expect(screen.getByText(/আইনি সতর্কতা:/i)).toBeInTheDocument();
  });
});

