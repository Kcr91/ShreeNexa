import React from "react";
import { LayoutProvider, LayoutManager } from "../layout";

export const DashboardView: React.FC = () => {
  return (
    <div style={{ height: "100%", width: "100%", display: "flex", flexDirection: "column" }}>
      <LayoutProvider>
        <LayoutManager />
      </LayoutProvider>
    </div>
  );
};
