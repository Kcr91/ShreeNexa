import React, { useEffect, useMemo, useRef, useState } from "react";

export interface TimezoneOption {
  id: string; // e.g. "Asia/Kolkata" or "UTC"
  label: string; // e.g. "(UTC+5:30) Kolkata" or "UTC" or "Exchange"
  timeZone: string;
  isExchange?: boolean;
}

export const TIMEZONE_STORAGE_KEY = "shreenexa_terminal_timezone";
export const DEFAULT_TIMEZONE = "Asia/Kolkata";

export const WORLD_TIMEZONES: TimezoneOption[] = [
  { id: "UTC", label: "UTC", timeZone: "UTC" },
  { id: "Exchange", label: "Exchange (IST)", timeZone: "Asia/Kolkata", isExchange: true },
  { id: "Pacific/Honolulu", label: "(UTC-10) Honolulu", timeZone: "Pacific/Honolulu" },
  { id: "America/Anchorage", label: "(UTC-9) Anchorage", timeZone: "America/Anchorage" },
  { id: "America/Juneau", label: "(UTC-8) Juneau", timeZone: "America/Juneau" },
  { id: "America/Vancouver", label: "(UTC-8) Vancouver", timeZone: "America/Vancouver" },
  { id: "America/Los_Angeles", label: "(UTC-7) Los Angeles", timeZone: "America/Los_Angeles" },
  { id: "America/Phoenix", label: "(UTC-7) Phoenix", timeZone: "America/Phoenix" },
  { id: "America/Denver", label: "(UTC-6) Denver", timeZone: "America/Denver" },
  { id: "America/Mexico_City", label: "(UTC-6) Mexico City", timeZone: "America/Mexico_City" },
  { id: "America/El_Salvador", label: "(UTC-6) San Salvador", timeZone: "America/El_Salvador" },
  { id: "America/Bogota", label: "(UTC-5) Bogota", timeZone: "America/Bogota" },
  { id: "America/Chicago", label: "(UTC-5) Chicago", timeZone: "America/Chicago" },
  { id: "America/Lima", label: "(UTC-5) Lima", timeZone: "America/Lima" },
  { id: "America/Caracas", label: "(UTC-4) Caracas", timeZone: "America/Caracas" },
  { id: "America/New_York", label: "(UTC-4) New York", timeZone: "America/New_York" },
  { id: "America/Santiago", label: "(UTC-4) Santiago", timeZone: "America/Santiago" },
  { id: "America/Toronto", label: "(UTC-4) Toronto", timeZone: "America/Toronto" },
  { id: "America/Argentina/Buenos_Aires", label: "(UTC-3) Buenos Aires", timeZone: "America/Argentina/Buenos_Aires" },
  { id: "America/Sao_Paulo", label: "(UTC-3) Sao Paulo", timeZone: "America/Sao_Paulo" },
  { id: "Atlantic/Azores", label: "(UTC-1) Azores", timeZone: "Atlantic/Azores" },
  { id: "Europe/London", label: "(UTC+0) London / Dublin / Lisbon", timeZone: "Europe/London" },
  { id: "Atlantic/Reykjavik", label: "(UTC+0) Reykjavik", timeZone: "Atlantic/Reykjavik" },
  { id: "Europe/Berlin", label: "(UTC+1) Berlin / Paris / Rome / Madrid", timeZone: "Europe/Berlin" },
  { id: "Europe/Zurich", label: "(UTC+1) Zurich / Geneva", timeZone: "Europe/Zurich" },
  { id: "Africa/Lagos", label: "(UTC+1) Lagos", timeZone: "Africa/Lagos" },
  { id: "Europe/Athens", label: "(UTC+2) Athens / Bucharest", timeZone: "Europe/Athens" },
  { id: "Africa/Cairo", label: "(UTC+2) Cairo", timeZone: "Africa/Cairo" },
  { id: "Europe/Helsinki", label: "(UTC+2) Helsinki", timeZone: "Europe/Helsinki" },
  { id: "Asia/Jerusalem", label: "(UTC+2) Jerusalem", timeZone: "Asia/Jerusalem" },
  { id: "Africa/Johannesburg", label: "(UTC+2) Johannesburg", timeZone: "Africa/Johannesburg" },
  { id: "Europe/Istanbul", label: "(UTC+3) Istanbul", timeZone: "Europe/Istanbul" },
  { id: "Asia/Riyadh", label: "(UTC+3) Kuwait / Riyadh", timeZone: "Asia/Riyadh" },
  { id: "Europe/Moscow", label: "(UTC+3) Moscow", timeZone: "Europe/Moscow" },
  { id: "Africa/Nairobi", label: "(UTC+3) Nairobi", timeZone: "Africa/Nairobi" },
  { id: "Asia/Tehran", label: "(UTC+3:30) Tehran", timeZone: "Asia/Tehran" },
  { id: "Asia/Dubai", label: "(UTC+4) Dubai / Abu Dhabi", timeZone: "Asia/Dubai" },
  { id: "Asia/Baku", label: "(UTC+4) Baku", timeZone: "Asia/Baku" },
  { id: "Asia/Kabul", label: "(UTC+4:30) Kabul", timeZone: "Asia/Kabul" },
  { id: "Asia/Karachi", label: "(UTC+5) Karachi / Tashkent", timeZone: "Asia/Karachi" },
  { id: "Asia/Kolkata", label: "(UTC+5:30) Kolkata / Mumbai / New Delhi", timeZone: "Asia/Kolkata" },
  { id: "Asia/Kathmandu", label: "(UTC+5:45) Kathmandu", timeZone: "Asia/Kathmandu" },
  { id: "Asia/Dhaka", label: "(UTC+6) Almaty / Dhaka", timeZone: "Asia/Dhaka" },
  { id: "Asia/Yangon", label: "(UTC+6:30) Yangon", timeZone: "Asia/Yangon" },
  { id: "Asia/Bangkok", label: "(UTC+7) Bangkok / Jakarta / Hanoi", timeZone: "Asia/Bangkok" },
  { id: "Asia/Shanghai", label: "(UTC+8) Shanghai / Beijing / Hong Kong", timeZone: "Asia/Shanghai" },
  { id: "Australia/Perth", label: "(UTC+8) Perth", timeZone: "Australia/Perth" },
  { id: "Asia/Singapore", label: "(UTC+8) Singapore", timeZone: "Asia/Singapore" },
  { id: "Asia/Taipei", label: "(UTC+8) Taipei", timeZone: "Asia/Taipei" },
  { id: "Asia/Seoul", label: "(UTC+9) Seoul", timeZone: "Asia/Seoul" },
  { id: "Asia/Tokyo", label: "(UTC+9) Tokyo", timeZone: "Asia/Tokyo" },
  { id: "Australia/Adelaide", label: "(UTC+9:30) Adelaide / Darwin", timeZone: "Australia/Adelaide" },
  { id: "Australia/Brisbane", label: "(UTC+10) Brisbane", timeZone: "Australia/Brisbane" },
  { id: "Australia/Sydney", label: "(UTC+10) Sydney / Melbourne", timeZone: "Australia/Sydney" },
  { id: "Pacific/Guadalcanal", label: "(UTC+11) Magadan / Solomon Is.", timeZone: "Pacific/Guadalcanal" },
  { id: "Pacific/Auckland", label: "(UTC+12) Auckland / Wellington", timeZone: "Pacific/Auckland" },
  { id: "Pacific/Fiji", label: "(UTC+12) Fiji", timeZone: "Pacific/Fiji" },
  { id: "Pacific/Tongatapu", label: "(UTC+13) Tongatapu", timeZone: "Pacific/Tongatapu" },
];

export function getTimezoneOffsetString(timeZone: string, date: Date = new Date()): string {
  try {
    if (timeZone === "UTC") return "UTC";
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone,
      timeZoneName: "shortOffset",
      hour12: false,
    }).formatToParts(date);
    const tzPart = parts.find((p) => p.type === "timeZoneName");
    if (!tzPart || !tzPart.value) return "UTC";
    const val = tzPart.value.replace(/^GMT/, "UTC");
    return val === "UTC+0" || val === "UTC-0" ? "UTC" : val;
  } catch {
    return "UTC";
  }
}

export function formatTimeInTimezone(timeZone: string, date: Date = new Date()): string {
  try {
    return new Intl.DateTimeFormat("en-US", {
      timeZone,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(date);
  } catch {
    return date.toISOString().slice(11, 19);
  }
}

export const FooterClock: React.FC = () => {
  const [selectedZone, setSelectedZone] = useState<string>(() => {
    try {
      return localStorage.getItem(TIMEZONE_STORAGE_KEY) || DEFAULT_TIMEZONE;
    } catch {
      return DEFAULT_TIMEZONE;
    }
  });

  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentTime, setCurrentTime] = useState<Date>(new Date());
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Live timer
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Close popover when clicking outside or pressing Escape
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const handleSelectZone = (zone: TimezoneOption) => {
    setSelectedZone(zone.timeZone);
    try {
      localStorage.setItem(TIMEZONE_STORAGE_KEY, zone.timeZone);
    } catch {
      // Ignore storage errors in restricted iframe
    }
    setIsOpen(false);
  };

  const formattedTime = formatTimeInTimezone(selectedZone, currentTime);
  const offsetString = getTimezoneOffsetString(selectedZone, currentTime);

  const filteredTimezones = useMemo(() => {
    if (!searchQuery.trim()) return WORLD_TIMEZONES;
    const q = searchQuery.toLowerCase().trim();
    return WORLD_TIMEZONES.filter(
      (tz) =>
        tz.label.toLowerCase().includes(q) ||
        tz.timeZone.toLowerCase().includes(q) ||
        tz.id.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  return (
    <div
      ref={containerRef}
      style={{
        position: "relative",
        display: "inline-flex",
        alignItems: "center",
      }}
    >
      {/* Clock trigger button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label={`Current clock: ${formattedTime} ${offsetString}. Click to change timezone.`}
        title="Click to change timezone"
        style={{
          background: "transparent",
          border: "none",
          padding: "2px 6px",
          borderRadius: "var(--radius-sm, 4px)",
          color: "var(--text-secondary, #94a3b8)",
          fontFamily: "var(--font-family-mono, monospace)",
          fontSize: "var(--font-size-xs, 12px)",
          cursor: "pointer",
          display: "inline-flex",
          alignItems: "center",
          gap: "4px",
          transition: "color 0.15s ease, background-color 0.15s ease",
          userSelect: "none",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.color = "var(--text-primary, #f8fafc)";
          e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.05)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = "var(--text-secondary, #94a3b8)";
          e.currentTarget.style.backgroundColor = "transparent";
        }}
      >
        <span>
          ({formattedTime} {offsetString})
        </span>
      </button>

      {/* TradingView-Style Upward Popover Dropdown */}
      {isOpen && (
        <div
          role="listbox"
          aria-label="Select timezone"
          style={{
            position: "absolute",
            bottom: "calc(100% + 6px)",
            right: 0,
            width: "300px",
            maxHeight: "380px",
            backgroundColor: "var(--bg-surface, #1e222d)",
            border: "1px solid var(--border-default, #2a2e39)",
            borderRadius: "var(--radius-md, 6px)",
            boxShadow: "0 10px 25px rgba(0, 0, 0, 0.5)",
            display: "flex",
            flexDirection: "column",
            zIndex: 1000,
            overflow: "hidden",
          }}
        >
          {/* Header & Search */}
          <div
            style={{
              padding: "8px",
              borderBottom: "1px solid var(--border-subtle, #2a2e39)",
              backgroundColor: "var(--bg-secondary, #131722)",
            }}
          >
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search country, city, or UTC..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search timezone"
              style={{
                width: "100%",
                padding: "6px 8px",
                fontSize: "12px",
                backgroundColor: "var(--bg-surface, #1e222d)",
                color: "var(--text-primary, #d1d4dc)",
                border: "1px solid var(--border-default, #2a2e39)",
                borderRadius: "4px",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Timezone Options List */}
          <div
            style={{
              overflowY: "auto",
              maxHeight: "320px",
              padding: "4px 0",
            }}
          >
            {filteredTimezones.length === 0 ? (
              <div
                style={{
                  padding: "12px",
                  textAlign: "center",
                  color: "var(--text-muted, #787b86)",
                  fontSize: "12px",
                }}
              >
                No timezones found
              </div>
            ) : (
              filteredTimezones.map((tz) => {
                const isSelected =
                  tz.timeZone === selectedZone || (tz.isExchange && selectedZone === "Asia/Kolkata");

                return (
                  <button
                    key={`${tz.id}-${tz.timeZone}`}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => handleSelectZone(tz)}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      padding: "7px 12px",
                      fontSize: "12px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      background: isSelected ? "rgba(41, 98, 255, 0.15)" : "transparent",
                      color: isSelected
                        ? "var(--color-primary, #2962ff)"
                        : "var(--text-primary, #d1d4dc)",
                      fontWeight: isSelected ? 600 : 400,
                      border: "none",
                      cursor: "pointer",
                      transition: "background-color 0.1s ease",
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.05)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.backgroundColor = "transparent";
                      }
                    }}
                  >
                    <span>{tz.label}</span>
                    {isSelected && (
                      <span style={{ color: "var(--color-primary, #2962ff)", fontSize: "12px" }}>
                        ✓
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
