# AGENTS.md

You are an expert in JavaScript, Rsbuild, React, and Flask. You write maintainable, performant, and accessible full-stack code.

## Development Workflow

To run the full application, you need two terminal sessions:

1.  **Backend (Root Directory)**:
    ```bash
    uv run python src/main.py
    ```
    -   Runs on `http://127.0.0.1:5000`
    -   Provides API endpoints at `/api/*`

2.  **Frontend (webdash/ Directory)**:
    ```bash
    cd webdash
    yarn run dev
    ```
    -   Runs on `http://localhost:3000`
    -   Proxies API requests to the backend

## Frontend Commands

- `yarn run dev` - Start the dev server
- `yarn run build` - Build the app for production
- `yarn run preview` - Preview the production build locally
- `yarn run check` - Run Biome check (lint + format)
- `yarn run format` - Run Biome format
- `yarn run test` - Run Rstest tests

## Docs

- Rsbuild: https://rsbuild.rs/llms.txt
- Rspack: https://rspack.rs/llms.txt
- Rstest: https://rstest.rs/llms.txt

## Tools

### Biome

- Run `yarn run check` to lint and check formatting
- Run `yarn run format` to format your code

### Rstest

- Run `yarn run test` to run tests
- Run `yarn run test:watch` to run tests in watch mode
