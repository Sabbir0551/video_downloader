import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MediaCard } from "../MediaCard";
import { MediaInfoResponse } from "@/types/api";

const mockMedia: MediaInfoResponse = {
  id: "test-video-1",
  title: "Next.js Full Course - Build Modern Web Apps",
  url: "https://www.youtube.com/watch?v=123456",
  thumbnail_url: "https://i.ytimg.com/vi/123456/maxresdefault.jpg",
  duration: 3665, // 1h 1m 5s
  uploader: "Dev Academy",
  extractor: "youtube",
  formats: [
    {
      format_id: "137",
      resolution: "1080p",
      ext: "mp4",
      format_note: "1080p60",
      filesize: 150000000,
      is_audio_only: false,
    },
    {
      format_id: "140",
      resolution: "128k",
      ext: "m4a",
      format_note: "medium",
      filesize: 12000000,
      is_audio_only: true,
    },
  ],
};

describe("MediaCard Component", () => {
  it("renders video title, uploader, and duration correctly", () => {
    const handleStart = vi.fn();
    render(
      <MediaCard
        media={mockMedia}
        lang="en"
        onStartDownload={handleStart}
        isStarting={false}
      />
    );

    expect(
      screen.getByText("Next.js Full Course - Build Modern Web Apps")
    ).toBeInTheDocument();
    expect(screen.getByText(/Dev Academy/i)).toBeInTheDocument();
    expect(screen.getByText(/1h 1m 5s/i)).toBeInTheDocument();
  });

  it("switches tabs between Video & Audio and Audio Only", () => {
    const handleStart = vi.fn();
    render(
      <MediaCard
        media={mockMedia}
        lang="en"
        onStartDownload={handleStart}
        isStarting={false}
      />
    );

    // Default Video Tab has Best Available option
    expect(screen.getAllByText("Best Available").length).toBeGreaterThanOrEqual(1);

    // Click Audio Tab
    const audioTabBtn = screen.getByRole("button", { name: /Audio Only/i });
    fireEvent.click(audioTabBtn);

    // Audio options should now appear
    expect(screen.getByText("MP3 Audio")).toBeInTheDocument();
    expect(screen.getByText("M4A Audio")).toBeInTheDocument();
  });

  it("calls onStartDownload when clicking Download button", () => {
    const handleStart = vi.fn();
    render(
      <MediaCard
        media={mockMedia}
        lang="en"
        onStartDownload={handleStart}
        isStarting={false}
      />
    );

    const downloadBtn = screen.getByRole("button", { name: /Download/i });
    fireEvent.click(downloadBtn);

    expect(handleStart).toHaveBeenCalledWith("best", false, "Best Available");
  });
});
