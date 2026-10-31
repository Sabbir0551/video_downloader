import { describe, it, expect } from "vitest";
import { getErrorMessage, translations } from "../i18n";

describe("Error Mapping & Localization", () => {
  const errorCodes = [
    "SSRF_DESTINATION_FORBIDDEN",
    "MEDIA_DRM_PROTECTED",
    "UPSTREAM_EXTRACTOR_DEPRECATED",
    "RATE_LIMIT_EXCEEDED",
    "GLOBAL_CONCURRENCY_CAP_EXCEEDED",
    "ACCESS_DENIED",
    "CAPTCHA_VERIFICATION_FAILED",
    "STORAGE_CAPACITY_FULL",
    "MEDIA_PRIVATE_OR_UNAVAILABLE",
    "MEDIA_LIVESTREAM_UNSUPPORTED",
    "MEDIA_DURATION_EXCEEDED",
    "UNSUPPORTED_URL_OR_PLATFORM",
    "MEDIA_LIMIT_EXCEEDED",
    "LEGAL_TAKEDOWN_BLOCK",
    "REQUEST_VALIDATION_ERROR",
    "JOB_NOT_FOUND",
    "DOWNLOAD_TOKEN_INVALID",
  ];

  it("maps every backend error code to distinct English messages", () => {
    errorCodes.forEach((code) => {
      const msg = getErrorMessage(code, "en");
      expect(msg).toBeDefined();
      expect(msg).not.toEqual(translations.en.errors.DEFAULT);
      expect(msg.length).toBeGreaterThan(10);
    });
  });

  it("maps every backend error code to distinct Bengali messages", () => {
    errorCodes.forEach((code) => {
      const msg = getErrorMessage(code, "bn");
      expect(msg).toBeDefined();
      expect(msg).not.toEqual(translations.bn.errors.DEFAULT);
      expect(msg.length).toBeGreaterThan(10);
    });
  });

  it("returns fallback default message when error code is null, undefined, or unrecognized", () => {
    expect(getErrorMessage(null, "en")).toBe(translations.en.errors.DEFAULT);
    expect(getErrorMessage(undefined, "en")).toBe(translations.en.errors.DEFAULT);
    expect(getErrorMessage("RANDOM_UNKNOWN_CODE", "en")).toBe(
      translations.en.errors.DEFAULT
    );

    expect(getErrorMessage(null, "bn")).toBe(translations.bn.errors.DEFAULT);
    expect(getErrorMessage(undefined, "bn")).toBe(translations.bn.errors.DEFAULT);
    expect(getErrorMessage("RANDOM_UNKNOWN_CODE", "bn")).toBe(
      translations.bn.errors.DEFAULT
    );
  });
});

