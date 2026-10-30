import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { UrlInput } from "../UrlInput";

describe("UrlInput Component", () => {
  it("renders input field and inspect button correctly", () => {
    const handleSearch = vi.fn();
    render(<UrlInput lang="en" onSearch={handleSearch} isLoading={false} />);

    expect(
      screen.getByPlaceholderText(/Paste video link here/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Inspect Link/i })).toBeInTheDocument();
  });

  it("shows validation error on empty submission", () => {
    const handleSearch = vi.fn();
    render(<UrlInput lang="en" onSearch={handleSearch} isLoading={false} />);

    const submitBtn = screen.getByRole("button", { name: /Inspect Link/i });
    fireEvent.click(submitBtn);

    expect(
      screen.getByText(/Please enter a valid video link/i)
    ).toBeInTheDocument();
    expect(handleSearch).not.toHaveBeenCalled();
  });

  it("shows validation error for non-http schemas", () => {
    const handleSearch = vi.fn();
    render(<UrlInput lang="en" onSearch={handleSearch} isLoading={false} />);

    const input = screen.getByPlaceholderText(/Paste video link here/i);
    fireEvent.change(input, { target: { value: "ftp://example.com/video.mp4" } });

    const submitBtn = screen.getByRole("button", { name: /Inspect Link/i });
    fireEvent.click(submitBtn);

    expect(
      screen.getByText(/Please provide a valid HTTP or HTTPS URL/i)
    ).toBeInTheDocument();
    expect(handleSearch).not.toHaveBeenCalled();
  });

  it("calls onSearch with trimmed URL when valid", () => {
    const handleSearch = vi.fn();
    render(<UrlInput lang="en" onSearch={handleSearch} isLoading={false} />);

    const input = screen.getByPlaceholderText(/Paste video link here/i);
    fireEvent.change(input, {
      target: { value: "  https://www.youtube.com/watch?v=dQw4w9WgXcQ  " },
    });

    const submitBtn = screen.getByRole("button", { name: /Inspect Link/i });
    fireEvent.click(submitBtn);

    expect(handleSearch).toHaveBeenCalledWith(
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    );
  });

  it("disables input and shows loading spinner when isLoading is true", () => {
    const handleSearch = vi.fn();
    render(<UrlInput lang="en" onSearch={handleSearch} isLoading={true} />);

    const input = screen.getByPlaceholderText(/Paste video link here/i);
    expect(input).toBeDisabled();
    expect(screen.getByText(/Analyzing.../i)).toBeInTheDocument();
  });
});

