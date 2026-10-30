import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DownloadProgress } from "../DownloadProgress";
import { apiClient } from "@/lib/api-client";
import { JobStatus } from "@/types/api";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    getJobStatus: vi.fn(),
    cancelJob: vi.fn(),
    resolveDownloadUrl: vi.fn((url) => `http://localhost:8000${url}`),
  },
}));

describe("DownloadProgress Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders progress, speed, and eta during active download", async () => {
    vi.mocked(apiClient.getJobStatus).mockResolvedValueOnce({
      job_id: "test-job-uuid",
      status: JobStatus.PROCESSING,
      progress: 45.0,
      speed: "3.2 MB/s",
      eta: 18,
      file_size: null,
      download_url: null,
      created_at: new Date().toISOString(),
      expires_at: new Date().toISOString(),
    });

    render(
      <DownloadProgress
        jobId="test-job-uuid"
        videoTitle="Amazing Nature 4K"
        lang="en"
        onCancel={vi.fn()}
        onRetry={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("45%")).toBeInTheDocument();
      expect(screen.getByText(/3.2 MB\/s/i)).toBeInTheDocument();
      expect(screen.getByText(/18s/i)).toBeInTheDocument();
    });
  });

  it("renders Save Media File button when job completes", async () => {
    vi.mocked(apiClient.getJobStatus).mockResolvedValueOnce({
      job_id: "completed-job-uuid",
      status: JobStatus.COMPLETED,
      progress: 100.0,
      speed: null,
      eta: null,
      file_size: 52428800, // 50 MB
      download_url: "/api/v1/downloads/completed-job-uuid/file?token=abc",
      created_at: new Date().toISOString(),
      expires_at: new Date().toISOString(),
    });

    render(
      <DownloadProgress
        jobId="completed-job-uuid"
        videoTitle="Amazing Nature 4K"
        lang="en"
        onCancel={vi.fn()}
        onRetry={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Download Ready!/i)).toBeInTheDocument();
      const saveBtn = screen.getByRole("link", { name: /Save Media File/i });
      expect(saveBtn).toBeInTheDocument();
      expect(saveBtn).toHaveAttribute(
        "href",
        "http://localhost:8000/api/v1/downloads/completed-job-uuid/file?token=abc"
      );
    });
  });

  it("calls cancelJob when clicking the Cancel button", async () => {
    const handleCancel = vi.fn();
    vi.mocked(apiClient.getJobStatus).mockResolvedValueOnce({
      job_id: "cancel-job-uuid",
      status: JobStatus.PROCESSING,
      progress: 20.0,
      speed: "1.0 MB/s",
      eta: 40,
      file_size: null,
      download_url: null,
      created_at: new Date().toISOString(),
      expires_at: new Date().toISOString(),
    });
    vi.mocked(apiClient.cancelJob).mockResolvedValueOnce({
      job_id: "cancel-job-uuid",
      status: JobStatus.CANCELLED,
      progress: 20.0,
      created_at: new Date().toISOString(),
      expires_at: new Date().toISOString(),
    });

    render(
      <DownloadProgress
        jobId="cancel-job-uuid"
        videoTitle="Amazing Nature 4K"
        lang="en"
        onCancel={handleCancel}
        onRetry={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("20%")).toBeInTheDocument();
    });

    const cancelBtn = screen.getByRole("button", { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(apiClient.cancelJob).toHaveBeenCalledWith("cancel-job-uuid");
      expect(handleCancel).toHaveBeenCalled();
    });
  });

  it("renders failure state and retry button on job failure", async () => {
    const handleRetry = vi.fn();
    vi.mocked(apiClient.getJobStatus).mockResolvedValueOnce({
      job_id: "failed-job-uuid",
      status: JobStatus.FAILED,
      progress: 0.0,
      error_code: "MEDIA_DRM_PROTECTED",
      error_message: null,
      created_at: new Date().toISOString(),
      expires_at: new Date().toISOString(),
    });

    render(
      <DownloadProgress
        jobId="failed-job-uuid"
        videoTitle="DRM Video"
        lang="en"
        onCancel={vi.fn()}
        onRetry={handleRetry}
      />
    );

    await waitFor(() => {
      expect(
        screen.getByText(/This media stream is encrypted by DRM/i)
      ).toBeInTheDocument();
      const retryBtn = screen.getByRole("button", { name: /Try Again/i });
      expect(retryBtn).toBeInTheDocument();
      fireEvent.click(retryBtn);
      expect(handleRetry).toHaveBeenCalled();
    });
  });

  it("renders Bengali progress metrics when lang is bn", async () => {
    vi.mocked(apiClient.getJobStatus).mockResolvedValueOnce({
      job_id: "bn-job-uuid",
      status: JobStatus.PROCESSING,
      progress: 60.0,
      speed: "2.5 MB/s",
      eta: 10,
      created_at: new Date().toISOString(),
      expires_at: new Date().toISOString(),
    });

    render(
      <DownloadProgress
        jobId="bn-job-uuid"
        videoTitle="বাংলা নাটক"
        lang="bn"
        onCancel={vi.fn()}
        onRetry={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("60%")).toBeInTheDocument();
      expect(screen.getByText(/স্পিড: 2.5 MB\/s/i)).toBeInTheDocument();
      expect(screen.getByText(/বাকি সময়: 10সেকেন্ড/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /বাতিল করুন/i })).toBeInTheDocument();
    });
  });
});
