import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import {
  FooterClock,
  formatTimeInTimezone,
  getTimezoneOffsetString,
  TIMEZONE_STORAGE_KEY,
} from "./FooterClock";

describe("FooterClock Component", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("calculates timezone offsets and formats time accurately", () => {
    const fixedDate = new Date("2026-09-04T12:00:00Z");
    const istOffset = getTimezoneOffsetString("Asia/Kolkata", fixedDate);
    expect(istOffset).toBe("UTC+5:30");

    const utcOffset = getTimezoneOffsetString("UTC", fixedDate);
    expect(utcOffset).toBe("UTC");

    const formattedIst = formatTimeInTimezone("Asia/Kolkata", fixedDate);
    expect(formattedIst).toBe("17:30:00");
  });

  it("renders live clock button with default IST offset (UTC+5:30)", () => {
    render(<FooterClock />);

    const button = screen.getByRole("button", { name: /Current clock:/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent(/UTC\+5:30/);
    expect(screen.queryByRole("listbox", { name: "Select timezone" })).not.toBeInTheDocument();
  });

  it("toggles upward timezone dropdown on button click", () => {
    render(<FooterClock />);

    const button = screen.getByRole("button", { name: /Current clock:/i });
    fireEvent.click(button);

    const listbox = screen.getByRole("listbox", { name: "Select timezone" });
    expect(listbox).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Search country, city, or UTC/i)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Exchange \(IST\)/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /^UTC$/i })).toBeInTheDocument();
  });

  it("filters timezone options via search input", () => {
    render(<FooterClock />);

    const button = screen.getByRole("button", { name: /Current clock:/i });
    fireEvent.click(button);

    const searchInput = screen.getByPlaceholderText(/Search country, city, or UTC/i);
    fireEvent.change(searchInput, { target: { value: "New York" } });

    expect(screen.getByRole("option", { name: /New York/i })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Honolulu/i })).not.toBeInTheDocument();
  });

  it("selects a timezone, updates offset, stores in localStorage, and closes popover", () => {
    render(<FooterClock />);

    const button = screen.getByRole("button", { name: /Current clock:/i });
    fireEvent.click(button);

    // Search for London
    const searchInput = screen.getByPlaceholderText(/Search country, city, or UTC/i);
    fireEvent.change(searchInput, { target: { value: "London" } });

    const londonOption = screen.getByRole("option", { name: /London/i });
    fireEvent.click(londonOption);

    // Dropdown closed
    expect(screen.queryByRole("listbox", { name: "Select timezone" })).not.toBeInTheDocument();

    // Persisted to localStorage
    expect(localStorage.getItem(TIMEZONE_STORAGE_KEY)).toBe("Europe/London");
  });

  it("closes popover when pressing Escape", () => {
    render(<FooterClock />);

    const button = screen.getByRole("button", { name: /Current clock:/i });
    fireEvent.click(button);

    expect(screen.getByRole("listbox", { name: "Select timezone" })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("listbox", { name: "Select timezone" })).not.toBeInTheDocument();
  });

  it("loads stored timezone preference from localStorage on mount", () => {
    localStorage.setItem(TIMEZONE_STORAGE_KEY, "America/New_York");
    render(<FooterClock />);

    const button = screen.getByRole("button", { name: /Current clock:/i });
    expect(button).toHaveTextContent(/UTC-4|UTC-5/); // Depending on DST
  });
});
