import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';

export const baseOptions: BaseLayoutProps = {
  nav: {
    title: (
      <span className="font-semibold tracking-tight">Policy Agent</span>
    ),
  },
  links: [
    {
      text: 'Documentation',
      url: '/docs',
      active: 'nested-url',
    },
    {
      text: 'GitHub',
      url: 'https://github.com/ghanse/databricks-policy-agent',
      external: true,
    },
  ],
  githubUrl: 'https://github.com/ghanse/databricks-policy-agent',
};
