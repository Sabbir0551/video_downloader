import { describe, it, expect, vi, beforeEach } from "vitest";
import { AnyStreamApiClient } from "../api-client";

describe("AnyStreamApiClient", () => {
  let client: AnyStreamApiClient;

  beforeEach(() => {
    client = new AnyStreamApiClient("http://localhost:8000");
    vi.restoreAllMocks();
  });

  it("resolves download URLs with and without access tokens", () => {
    expect(client.resolveDownloadUrl("/api/v1/downloads/123/file")).toBe(
      "http://localhost:8000/api/v1/downloads/123/file"
    );

    expect(
      client.resolveDownloadUrl("/api/v1/downloads/123/file", "jat_mock_secret")
    ).toBe("http://localhost:8000/api/v1/downloads/123/file?token=jat_mock_secret");

    expect(
      client.resolveDownloadUrl("https://r2.storage.example/file.mp4?existing=1", "jat_mock_secret")
    ).toBe("https://r2.storage.example/file.mp4?existing=1&token=jat_mock_secret");
  });

  it("passes X-Job-Token header and token query param on getJobStatus", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        job_id: "test-job-uuid",
        status: "PROCESSING",
        progress: 45,
        created_at: "2026-11-01T00:00:00Z",
        expires_at: "2026-11-01T00:30:00Z",
        job_access_token: "jat_secret",
      }),
    });
    global.fetch = fetchMock;

    const res = await client.getJobStatus("test-job-uuid", "jat_secret");
    expect(res.status).toBe("PROCESSING");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/downloads/test-job-uuid?token=jat_secret",
      expect.objectContaining({
        method: "GET",
        headers: expect.any(Headers),
      })
    );
  });

  it("passes X-Job-Token header on cancelJob", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        job_id: "test-job-uuid",
        status: "CANCELLED",
        progress: 45,
        created_at: "2026-11-01T00:00:00Z",
        expires_at: "2026-11-01T00:30:00Z",
      }),
    });
    global.fetch = fetchMock;

    const res = await client.cancelJob("test-job-uuid", "jat_secret");
    expect(res.status).toBe("CANCELLED");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/downloads/test-job-uuid?token=jat_secret",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.any(Headers),
      })
    );
  });
});
