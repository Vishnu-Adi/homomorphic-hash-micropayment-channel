## Privacy-Preserving Micropayment Channel

This project implements a two-party micropayment channel prototype that keeps per-update payment amounts private using additively homomorphic commitments. It combines a Python FastAPI backend for the cryptographic protocol with a Next.js 14 web frontend for interactive demos and visualizations.

### Repository Layout
- `backend/` – FastAPI application, cryptographic primitives, protocol logic, tests, and benchmarking utilities.
- `frontend/` – Next.js 14 (TypeScript) web application for configuring channels, executing private micropayments, viewing history, and inspecting benchmark results.
- `report/` – Final report sources and Word reference template.
- `figures/` – Diagrams and plots referenced by the report and frontend.
- `hom.plan.md` – Development plan that guided the implementation.

### Getting Started (Planned)
1. Create and activate a Python 3.11 virtual environment.
2. Install backend dependencies from `backend/requirements.txt` and run `uvicorn src.api.main:app --reload`.
3. Install frontend dependencies with `npm install` inside `frontend/` and run `npm run dev`.
4. Visit `http://localhost:3000` to explore the web UI; the frontend uses the backend REST API to manage the channel.

### Status
The repository scaffolding is in progress. Additional instructions will follow as components are implemented.

