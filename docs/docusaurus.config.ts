import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";

// Documentation site for the Databricks Policy Agent. Guide pages are hand-written under
// ``docs/``; the API reference under ``docs/api`` is generated from source docstrings by
// pydoc-markdown (see pydoc-markdown.yml) and must not be edited by hand.
const config: Config = {
  title: "Databricks Policy Agent",
  tagline: "Policy compliance for Databricks workspace objects",
  favicon: "img/favicon.ico",
  url: "https://example.com",
  baseUrl: "/databricks-policy-agent",
  onBrokenLinks: "throw",
  i18n: { defaultLocale: "en", locales: ["en"] },
  // Parse ``.md`` as CommonMark (not MDX) so literal braces in policy examples and the
  // generated API reference are not mistaken for JSX expressions.
  markdown: { format: "detect", hooks: { onBrokenMarkdownLinks: "warn" } },
  presets: [
    [
      "classic",
      {
        docs: { routeBasePath: "/", sidebarPath: "./sidebars.ts" },
        blog: false,
        theme: {},
      } satisfies Preset.Options,
    ],
  ],
  themeConfig: {
    navbar: {
      title: "Policy Agent",
      items: [{ type: "docSidebar", sidebarId: "docs", position: "left", label: "Docs" }],
    },
    footer: { style: "dark", links: [] },
  } satisfies Preset.ThemeConfig,
};

export default config;
