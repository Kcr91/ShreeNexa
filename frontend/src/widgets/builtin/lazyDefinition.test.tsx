import { Suspense } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { WidgetComponentProps, WidgetDefinition } from "../types";
import { createLazyWidgetDefinition } from "./lazyDefinition";

describe("createLazyWidgetDefinition", () => {
  it("loads implementation code only when rendered and applies module defaults", async () => {
    const loadedDefinition: WidgetDefinition = {
      id: "lazy-fixture",
      title: "Lazy Fixture",
      description: "Verifies deferred widget loading.",
      category: "custom",
      icon: "🧪",
      defaultWidth: 200,
      defaultHeight: 120,
      schema: {
        fields: [
          {
            name: "message",
            label: "Message",
            type: "string",
            default: "loaded lazily",
          },
        ],
      },
      component: ({ settings }: WidgetComponentProps<Record<string, unknown>>) => (
        <div>{String(settings.message)}</div>
      ),
    };
    const load = vi.fn(async () => loadedDefinition);
    const definition = createLazyWidgetDefinition({
      id: loadedDefinition.id,
      title: loadedDefinition.title,
      description: loadedDefinition.description,
      category: loadedDefinition.category,
      icon: loadedDefinition.icon,
      defaultWidth: loadedDefinition.defaultWidth,
      defaultHeight: loadedDefinition.defaultHeight,
      load,
    });

    expect(load).not.toHaveBeenCalled();

    const Component = definition.component;
    render(
      <Suspense fallback={<div>loading</div>}>
        <Component instanceId="lazy-1" settings={{}} />
      </Suspense>,
    );

    expect(await screen.findByText("loaded lazily")).toBeInTheDocument();
    expect(load).toHaveBeenCalledOnce();
    expect(definition.schema).toBe(loadedDefinition.schema);
  });
});
