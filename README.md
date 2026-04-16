# p6 Project Structure

A hybrid Rust + Python project using `uv` and `maturin`.

## Conceptual Overview

-   **Backend (`python/p6/main.py`)**: A Flask-based API server.
-   **Native Extension (`src/lib.rs`)**: High-performance Rust implementations (e.g., LTTB algorithm).
-   **Frontend (`webdash/`)**: A modern React application built with Rsbuild.

## Development Setup

### Prerequisites
-   **Python 3.13+** (managed with `uv`)
-   **Rust** (managed with `rustup`)
-   **Zig** (for cross-compilation)
-   **Node.js** (managed with `yarn`)

### Running the App
1.  **Backend (with Rust extension)**: 
    ```bash
    uv run python python/p6/main.py
    ```
    (Starts on port 5000. `maturin` handles the compilation of the Rust part automatically when using `uv`).

2.  **Frontend**: 
    ```bash
    cd webdash && yarn dev
    ```
    (Starts on port 3000)

## Project Layout

-   `src/`: Rust source code.
-   `python/p6/`: Backend Python package.
-   `webdash/`: Frontend React application.
-   `Cargo.toml`: Rust package configuration.
-   `pyproject.toml`: Python project configuration and `maturin` settings.

## Cross-Compilation with Zig

To cross-compile for different targets using Zig:

1.  Install `cargo-zigbuild`:
    ```bash
    cargo install cargo-zigbuild
    ```
2.  Install Zig on your system.
3.  Build with maturin:
    ```bash
    uvx maturin build --zig --target <target-triple>
    ```
