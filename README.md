# p6 Project Structure

A full-stack application with a Flask backend and a React (Rsbuild) frontend.

## Conceptual Overview

-   **Backend (`src/main.py`)**: A Flask-based API server that also runs background worker threads. It handles business logic, data processing (e.g., using `torch`), and serves JSON endpoints.
-   **Frontend (`webdash/`)**: A modern React application built with Rsbuild. It communicates with the backend via a development proxy for seamless API integration.

## Getting Started

### Prerequisites
-   **Python 3.13+** (managed with `uv`)
-   **Node.js** (managed with `yarn`)

### Running the App
1.  **Backend**: `uv run python src/main.py` (Starts on port 5000)
2.  **Frontend**: `cd webdash && yarn dev` (Starts on port 3000)

## Project Layout

-   `src/`: Backend Python source code.
-   `webdash/`: Frontend React application source and configuration.
-   `AGENTS.md`: Detailed instructions for AI-assisted development and commands.
-   `pyproject.toml`: Python dependencies and project metadata.
-   `webdash/package.json`: Frontend dependencies and build scripts.
