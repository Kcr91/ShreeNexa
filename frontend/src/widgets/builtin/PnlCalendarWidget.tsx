import React, { useState, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import { DailyPnlRecord, PnlCalendarWidgetSettings } from "../../pnlcalendar/types";
import { generateMonthlyPnlSummary } from "../../pnlcalendar/calendar";

export const PnlCalendarWidget: React.FC<
  WidgetComponentProps<PnlCalendarWidgetSettings>
> = ({ settings }) => {
  const [currentYear, setCurrentYear] = useState(2026);
  const [currentMonth, setCurrentMonth] = useState(8); // August
  const [selectedDay, setSelectedDay] = useState<DailyPnlRecord | null>(null);

  const monthlySummary = useMemo(() => {
    return generateMonthlyPnlSummary(currentYear, currentMonth);
  }, [currentYear, currentMonth]);

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];

  const handlePrevMonth = () => {
    if (currentMonth === 1) {
      setCurrentMonth(12);
      setCurrentYear((y) => y - 1);
    } else {
      setCurrentMonth((m) => m - 1);
    }
    setSelectedDay(null);
  };

  const handleNextMonth = () => {
    if (currentMonth === 12) {
      setCurrentMonth(1);
      setCurrentYear((y) => y + 1);
    } else {
      setCurrentMonth((m) => m + 1);
    }
    setSelectedDay(null);
  };

  // Compute leading blank days for Monday-start calendar
  const firstDayOfMonth = new Date(currentYear, currentMonth - 1, 1).getDay();
  // In JS: 0 = Sun, 1 = Mon ... 6 = Sat -> For Mon=0 start: (day + 6) % 7
  const leadingBlankDays = (firstDayOfMonth + 6) % 7;
  const daysInMonth = new Date(currentYear, currentMonth, 0).getDate();

  const calendarDays = useMemo(() => {
    const days = [];
    for (let i = 0; i < leadingBlankDays; i++) {
      days.push(null);
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const monthStr = currentMonth < 10 ? `0${currentMonth}` : `${currentMonth}`;
      const dayStr = d < 10 ? `0${d}` : `${d}`;
      const dateKey = `${currentYear}-${monthStr}-${dayStr}`;
      days.push(monthlySummary.dailyRecords[dateKey] || null);
    }
    return days;
  }, [leadingBlankDays, daysInMonth, currentYear, currentMonth, monthlySummary.dailyRecords]);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "var(--spacing-2)", gap: "var(--spacing-2)" }}>
      {/* Navigation and Monthly Scorecard Banner */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: "var(--bg-surface)",
          padding: "var(--spacing-2) var(--spacing-3)",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-subtle)",
          fontSize: "var(--font-size-xs)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
          <button
            type="button"
            onClick={handlePrevMonth}
            style={{
              padding: "2px 8px",
              backgroundColor: "transparent",
              color: "var(--text-primary)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
            }}
          >
            ‹ Prev
          </button>
          <strong style={{ fontSize: "var(--font-size-sm)", minWidth: "120px", textAlign: "center" }}>
            {monthNames[currentMonth - 1]} {currentYear}
          </strong>
          <span
            style={{
              padding: "1px 6px",
              borderRadius: "var(--radius-sm)",
              fontSize: "10px",
              fontWeight: "var(--font-weight-semibold)",
              backgroundColor: settings?.sourceKind === "paper" ? "rgba(16, 185, 129, 0.15)" : "rgba(59, 130, 246, 0.15)",
              color: settings?.sourceKind === "paper" ? "var(--color-success)" : "var(--color-info)",
              border: `1px solid ${settings?.sourceKind === "paper" ? "var(--color-success)" : "var(--color-info)"}`,
              textTransform: "uppercase",
            }}
          >
            {settings?.sourceKind === "paper" ? "Paper" : "Backtest"}
          </span>
          <button
            type="button"
            onClick={handleNextMonth}
            style={{
              padding: "2px 8px",
              backgroundColor: "transparent",
              color: "var(--text-primary)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
            }}
          >
            Next ›
          </button>
        </div>

        {/* Monthly Scorecard Strip */}
        <div style={{ display: "flex", gap: "var(--spacing-3)", alignItems: "center" }}>
          <div>
            <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>Net P&L: </span>
            <strong
              data-testid="month-net-pnl"
              style={{
                color: monthlySummary.netPnl >= 0 ? "var(--color-up)" : "var(--color-down)",
                fontSize: "var(--font-size-sm)",
              }}
            >
              {monthlySummary.netPnl >= 0 ? "+" : ""}₹{monthlySummary.netPnl.toLocaleString("en-IN")}
            </strong>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>Win Rate: </span>
            <strong style={{ color: "var(--color-primary)" }}>{monthlySummary.winRatePct}%</strong>{" "}
            <span style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>
              ({monthlySummary.greenDays}W / {monthlySummary.redDays}L)
            </span>
          </div>
          {settings?.showCharges !== false && (
            <div>
              <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>Charges: </span>
              <strong>₹{monthlySummary.totalCharges.toLocaleString("en-IN")}</strong>
            </div>
          )}
        </div>
      </div>

      {/* Main Grid & Drilldown View */}
      <div style={{ flex: 1, display: "flex", gap: "var(--spacing-2)", overflow: "hidden" }}>
        {/* Calendar Grid */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", overflow: "hidden" }}>
          {/* Day of Week Headers */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", backgroundColor: "var(--bg-surface)", borderBottom: "1px solid var(--border-subtle)", textAlign: "center", padding: "4px 0", fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)" }}>
            <div>Mon</div>
            <div>Tue</div>
            <div>Wed</div>
            <div>Thu</div>
            <div>Fri</div>
            <div>Sat</div>
            <div>Sun</div>
          </div>

          {/* Day Tiles */}
          <div style={{ flex: 1, display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gridAutoRows: "1fr", gap: "1px", backgroundColor: "var(--border-subtle)", overflowY: "auto" }}>
            {calendarDays.map((dayRecord, idx) => {
              if (!dayRecord) {
                return <div key={`blank-${idx}`} style={{ backgroundColor: "var(--bg-base)" }} />;
              }

              const dayNum = parseInt(dayRecord.date.split("-")[2], 10);
              const isSelected = selectedDay?.date === dayRecord.date;

              if (dayRecord.dayType === "WEEKEND") {
                return (
                  <div
                    key={dayRecord.date}
                    style={{
                      backgroundColor: "var(--bg-base)",
                      opacity: 0.5,
                      padding: "4px",
                      fontSize: "0.6875rem",
                      color: "var(--text-muted)",
                    }}
                  >
                    <span>{dayNum}</span>
                  </div>
                );
              }

              if (dayRecord.dayType === "HOLIDAY") {
                return (
                  <div
                    key={dayRecord.date}
                    data-testid={`holiday-tile-${dayRecord.date}`}
                    style={{
                      backgroundColor: "rgba(255, 255, 255, 0.02)",
                      padding: "4px",
                      fontSize: "0.6875rem",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                    }}
                  >
                    <span style={{ color: "var(--text-muted)" }}>{dayNum}</span>
                    <span style={{ fontSize: "0.5625rem", color: "#faad14", lineHeight: "1.1" }}>
                      🏖️ {dayRecord.holidayName}
                    </span>
                  </div>
                );
              }

              // Trading Day
              const isGreen = dayRecord.netPnl >= 0;
              return (
                <div
                  key={dayRecord.date}
                  data-testid={`trading-day-tile-${dayRecord.date}`}
                  onClick={() => setSelectedDay(dayRecord)}
                  style={{
                    backgroundColor: isGreen ? "rgba(38, 166, 154, 0.12)" : "rgba(239, 83, 80, 0.12)",
                    border: isSelected ? "2px solid var(--color-primary)" : "none",
                    padding: "4px",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.6875rem" }}>
                    <span style={{ fontWeight: 600 }}>{dayNum}</span>
                    <span style={{ fontSize: "0.5625rem", color: "var(--text-muted)" }}>{dayRecord.tradesCount}T</span>
                  </div>
                  <strong
                    style={{
                      fontSize: "0.6875rem",
                      color: isGreen ? "var(--color-up)" : "var(--color-down)",
                      textAlign: "right",
                    }}
                  >
                    {isGreen ? "+" : ""}₹{Math.round(dayRecord.netPnl).toLocaleString("en-IN")}
                  </strong>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Day Drilldown Side Panel */}
        {selectedDay && (
          <div
            data-testid="day-drilldown-panel"
            style={{
              width: "280px",
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              padding: "var(--spacing-3)",
              display: "flex",
              flexDirection: "column",
              gap: "var(--spacing-2)",
              fontSize: "var(--font-size-xs)",
              overflowY: "auto",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong>Date: {selectedDay.date}</strong>
              <button
                type="button"
                onClick={() => setSelectedDay(null)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                ✕
              </button>
            </div>

            <div style={{ backgroundColor: "var(--bg-active)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px" }}>
              <div>Gross PnL:</div>
              <div style={{ textAlign: "right", fontWeight: 600 }}>₹{selectedDay.grossPnl.toLocaleString("en-IN")}</div>
              <div>Taxes & Charges:</div>
              <div style={{ textAlign: "right", color: "var(--text-muted)" }}>-₹{selectedDay.charges.toLocaleString("en-IN")}</div>
              <div style={{ fontWeight: 700 }}>Net Realized PnL:</div>
              <div style={{ textAlign: "right", fontWeight: 700, color: selectedDay.netPnl >= 0 ? "var(--color-up)" : "var(--color-down)" }}>
                {selectedDay.netPnl >= 0 ? "+" : ""}₹{selectedDay.netPnl.toLocaleString("en-IN")}
              </div>
            </div>

            <strong style={{ marginTop: "4px" }}>Trade Book Reconciliations</strong>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              {selectedDay.trades.map((t, idx) => (
                <div
                  key={idx}
                  style={{
                    backgroundColor: "var(--bg-active)",
                    padding: "4px 6px",
                    borderRadius: "var(--radius-sm)",
                    fontSize: "0.6875rem",
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600 }}>{t.symbol}</div>
                    <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)" }}>
                      {t.time} • {t.side} {t.quantity} @ ₹{t.price}
                    </div>
                  </div>
                  <strong style={{ color: t.pnl >= 0 ? "var(--color-up)" : "var(--color-down)" }}>
                    {t.pnl >= 0 ? "+" : ""}₹{t.pnl.toLocaleString("en-IN")}
                  </strong>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export const pnlCalendarDefinition: WidgetDefinition<PnlCalendarWidgetSettings> = {
  id: "pnl-calendar",
  title: "P&L Calendar",
  description: "Monthly trading performance grid, holiday schedule indicators, and trade book drill-down.",
  category: "analytics",
  icon: "📅",
  defaultWidth: 640,
  defaultHeight: 420,
  schema: {
    fields: [
      {
        name: "defaultMonth",
        label: "Default Month",
        type: "string",
        default: "2026-08",
      },
      {
        name: "showCharges",
        label: "Show Brokerage & Taxes",
        type: "boolean",
        default: true,
      },
      {
        name: "showWeekends",
        label: "Show Weekends",
        type: "boolean",
        default: true,
      },
      {
        name: "sourceKind",
        label: "Execution Source",
        type: "select",
        default: "backtest",
        options: [
          { label: "Backtest", value: "backtest" },
          { label: "Paper Trading", value: "paper" },
        ],
      },
    ],
  },
  component: PnlCalendarWidget,
};
