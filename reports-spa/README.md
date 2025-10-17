# Reports SPA

Modern Vite + React + TypeScript SPA for SDM-Tools reports.

## Features

- **4 Interactive Dashboards**:
  - Team Sprint Dashboard (landing page)
  - Team KPI Dashboard
  - Developer Activity Dashboard
  - Developer Comparison Dashboard

- **Navigation**: Collapsible sidebar menu
- **Self-Contained**: Data embedded at build time
- **Offline**: No external dependencies required
- **Professional**: TELUS branding and design system

## Development

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

Output: `../dist/reports/`

## Tech Stack

- React 18
- TypeScript
- Vite
- React Router
- Chart.js
- TailwindCSS

## Project Structure

```
src/
├── components/
│   ├── Layout/          # Sidebar and main layout
│   ├── charts/          # Chart components (Radar, Bar, Pie)
│   └── shared/          # Reusable UI components
├── pages/               # Dashboard pages
├── data/                # TypeScript types and embedded data
├── styles/              # Custom CSS
├── App.tsx              # Router configuration
└── main.tsx             # Entry point
```

## Data Embedding

Data is embedded directly into the built HTML at build time, making the bundle fully self-contained with no need for external API calls or data fetching.

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
