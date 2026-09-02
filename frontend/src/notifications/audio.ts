import { AlertCategory } from "./types";

export function playAlertChime(category: AlertCategory, volume: number = 0.5): boolean {
  if (typeof window === "undefined") return false;

  const AudioCtxClass =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

  if (!AudioCtxClass) return false;

  try {
    const ctx = new AudioCtxClass();
    const now = ctx.currentTime;
    const vol = Math.max(0.01, Math.min(1.0, volume));

    const playTone = (freq: number, startOffset: number, duration: number, type: OscillatorType = "sine") => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = type;
      osc.frequency.setValueAtTime(freq, now + startOffset);

      gain.gain.setValueAtTime(vol * 0.3, now + startOffset);
      gain.gain.exponentialRampToValueAtTime(0.001, now + startOffset + duration);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now + startOffset);
      osc.stop(now + startOffset + duration);
    };

    switch (category) {
      case "ORDER_FILL":
        // Ascending major chord (C5, E5, G5)
        playTone(523.25, 0.0, 0.12);
        playTone(659.25, 0.08, 0.12);
        playTone(783.99, 0.16, 0.25);
        break;

      case "ORDER_REJECT":
        // Low double buzzer (220Hz, 174Hz)
        playTone(220.0, 0.0, 0.15, "triangle");
        playTone(174.61, 0.12, 0.2, "triangle");
        break;

      case "MARGIN_CALL":
        // Triple warning pulse (440Hz)
        playTone(440.0, 0.0, 0.08, "square");
        playTone(440.0, 0.12, 0.08, "square");
        playTone(440.0, 0.24, 0.15, "square");
        break;

      case "RISK_BREACH":
        // High/low siren (880Hz -> 440Hz -> 880Hz)
        playTone(880.0, 0.0, 0.1, "sawtooth");
        playTone(440.0, 0.1, 0.1, "sawtooth");
        playTone(880.0, 0.2, 0.15, "sawtooth");
        break;

      case "PRICE_ALERT":
      case "SYSTEM":
      default:
        // Single gentle chime (587Hz)
        playTone(587.33, 0.0, 0.2);
        break;
    }

    return true;
  } catch {
    return false;
  }
}
