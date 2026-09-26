import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, beforeEach } from "vitest";
import App from "./App";

describe("App", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: "ok" }),
      } as Response)
    );
  });

  it("renders the backend health status after fetching it", async () => {
    render(<App />);
    await waitFor(() => screen.getByText(/backend status: ok/i));
  });
});
