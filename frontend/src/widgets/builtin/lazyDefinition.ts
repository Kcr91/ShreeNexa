import React from "react";

import type {
  WidgetComponentProps,
  WidgetDefinition,
  WidgetSettingsSchema,
} from "../types";

type WidgetMetadata = Omit<WidgetDefinition, "component">;

export interface LazyWidgetManifest extends WidgetMetadata {
  load: () => Promise<WidgetDefinition>;
}

const metadataKeys: (keyof WidgetMetadata)[] = [
  "id",
  "title",
  "description",
  "category",
  "icon",
  "defaultWidth",
  "defaultHeight",
  "minWidth",
  "minHeight",
  "schema",
];

function defaultsFrom(schema: WidgetSettingsSchema): Record<string, unknown> {
  return Object.fromEntries(schema.fields.map((field) => [field.name, field.default]));
}

/**
 * Registers widget metadata immediately while deferring the implementation
 * module until React first renders that widget.
 */
export function createLazyWidgetDefinition(
  manifest: LazyWidgetManifest,
): WidgetDefinition {
  const { load, ...metadata } = manifest;
  let definition: WidgetDefinition;

  const component = React.lazy(async () => {
    const loaded = await load();

    for (const key of metadataKeys) {
      const matches =
        key === "schema"
          ? JSON.stringify(loaded.schema) === JSON.stringify(metadata.schema)
          : loaded[key] === metadata[key];
      if (!matches) {
        throw new Error(
          `Lazy widget metadata mismatch for '${metadata.id}' at '${key}'.`,
        );
      }
    }

    const LoadedComponent = loaded.component as React.ComponentType<
      WidgetComponentProps<Record<string, unknown>>
    >;

    const LazyWidget: React.FC<WidgetComponentProps<Record<string, unknown>>> = (
      props,
    ) =>
      React.createElement(LoadedComponent, {
        ...props,
        settings: {
          ...defaultsFrom(loaded.schema),
          ...props.settings,
        },
      });

    return { default: LazyWidget };
  });

  definition = {
    ...metadata,
    component,
  };
  return definition;
}
