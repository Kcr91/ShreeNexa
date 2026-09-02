import { describe, expect, it } from "vitest";
import { playAlertChime } from "./audio";

describe("Web Audio Synthesizer Engine", () => {
  it("handles playAlertChime safely across alert categories", () => {
    // In headless JSDOM environment, AudioContext is either mocked or safely handled
    const fillResult = playAlertChime("ORDER_FILL", 0.5);
    expect(typeof fillResult).toBe("boolean");

    const rejectResult = playAlertChime("ORDER_REJECT", 0.5);
    expect(typeof rejectResult).toBe("boolean");

    const riskResult = playAlertChime("RISK_BREACH", 0.8);
    expect(typeof riskResult).toBe("boolean");

    const marginResult = playAlertChime("MARGIN_CALL", 0.4);
    expect(typeof marginResult).toBe("boolean");
  });
});
