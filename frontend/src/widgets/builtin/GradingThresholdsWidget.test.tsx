import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  GradingThresholdsWidget,
  gradingThresholdsDefinition,
} from "./GradingThresholdsWidget";
import { widgetRegistry } from "../registry";
import "./index";

describe("GradingThresholdsWidget Component", () => {
  it("renders grading thresholds editor with horizon selector and live preview", () => {
    render(
      <GradingThresholdsWidget
        instanceId="grading-1"
        settings={{
          defaultHorizon: "POSITIONAL",
        }}
      />
    );

    expect(screen.getByTestId("config-version-tag")).toHaveTextContent("v1.0");
    expect(screen.getByTestId("horizon-tab-positional")).toBeInTheDocument();
    expect(screen.getByTestId("preview-grade")).toBeInTheDocument();
    expect(screen.getByTestId("preview-score")).toBeInTheDocument();
    expect(screen.getByTestId("btn-save-thresholds")).toBeInTheDocument();
    expect(screen.getByTestId("btn-regrade-scorecards")).toBeInTheDocument();
  });

  it("displays validation error when entering an invalid non-monotonic threshold", () => {
    render(
      <GradingThresholdsWidget
        instanceId="grading-1"
        settings={{
          defaultHorizon: "POSITIONAL",
        }}
      />
    );

    // Break Sharpe Excellent by setting it below Good (e.g. 0.2)
    const sharpeExcellentInput = screen.getByLabelText("Sharpe Ratio excellent");
    fireEvent.change(sharpeExcellentInput, { target: { value: "0.2" } });

    expect(screen.getByTestId("validation-error-banner")).toBeInTheDocument();
    expect(screen.getByText(/Invalid threshold order/i)).toBeInTheDocument();
    expect(screen.getByTestId("btn-save-thresholds")).toBeDisabled();
  });

  it("saves valid threshold configuration, marks scorecards STALE, and explicitly re-grades", () => {
    render(
      <GradingThresholdsWidget
        instanceId="grading-1"
        settings={{
          defaultHorizon: "POSITIONAL",
        }}
      />
    );

    // Initial status should be CURRENT
    expect(screen.getByTestId("active-scorecard-status")).toHaveTextContent("CURRENT");

    // Click Save
    const saveBtn = screen.getByTestId("btn-save-thresholds");
    fireEvent.click(saveBtn);

    // Version advances to v1.1
    expect(screen.getByTestId("config-version-tag")).toHaveTextContent("v1.1");
    expect(screen.getByTestId("notification-banner")).toHaveTextContent(/Historical scorecards marked STALE/i);
    expect(screen.getByTestId("active-scorecard-status")).toHaveTextContent("STALE");

    // Click Re-grade
    const regradeBtn = screen.getByTestId("btn-regrade-scorecards");
    fireEvent.click(regradeBtn);

    // Status returns to CURRENT
    expect(screen.getByTestId("active-scorecard-status")).toHaveTextContent("CURRENT");
    expect(screen.getByTestId("notification-banner")).toHaveTextContent(/All scorecards re-graded/i);
  });

  it("is registered in widget registry under analytics category", () => {
    expect(widgetRegistry.get("grading-thresholds")).toBeDefined();
    expect(widgetRegistry.get("grading-thresholds")?.title).toBe(
      "Grading Thresholds"
    );
    expect(gradingThresholdsDefinition.category).toBe("analytics");
  });
});
