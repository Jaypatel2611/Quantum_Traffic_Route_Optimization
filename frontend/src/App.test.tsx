import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, beforeEach } from "vitest";
import App from "./App";

describe("App", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([{ id: "indiranagar_bengaluru", name: "Indiranagar, Bengaluru" }]),
      } as Response)
    );
  });

  it("renders the Setup screen first, with the cached city loaded", async () => {
    render(<App />);
    await waitFor(() => screen.getByText(/city \/ network setup/i));
    await waitFor(() => screen.getByText(/indiranagar, bengaluru/i));
  });
});
