import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallbackMessage?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("ErrorBoundary caught an unhandled error:", error, errorInfo);
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  public override render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          style={{
            padding: "var(--spacing-6)",
            margin: "var(--spacing-4)",
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--color-down)",
            borderRadius: "var(--radius-md)",
            color: "var(--text-primary)",
          }}
        >
          <h2 style={{ color: "var(--color-down)", marginBottom: "var(--spacing-2)" }}>
            Application Error Caught
          </h2>
          <p style={{ color: "var(--text-secondary)", marginBottom: "var(--spacing-4)" }}>
            {this.props.fallbackMessage || this.state.error?.message || "An unexpected error occurred in this view."}
          </p>
          <button
            type="button"
            onClick={this.handleReset}
            style={{
              padding: "var(--spacing-2) var(--spacing-4)",
              backgroundColor: "var(--color-primary)",
              color: "var(--text-inverse)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              fontWeight: "bold",
            }}
          >
            Retry Component
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
