# Task Board

A minimal, self-contained full-stack demo app used to bootstrap and validate the
Cloud Agent development environment for this repository.

- **Backend:** Node.js + TypeScript + Express, exposing a small REST API.
- **Frontend:** static HTML/CSS/JS served by Express (no build step, no framework).
- **Storage:** in-memory with optional JSON-file persistence (no external services).

## Requirements

- Node.js >= 20 (the repo is developed against Node 22)

## Getting started

```bash
npm ci          # install dependencies from the lockfile
npm run dev     # start the dev server at http://localhost:3000
```

Then open http://localhost:3000 and add, complete, and delete tasks.

## Scripts

| Command            | Description                                        |
| ------------------ | -------------------------------------------------- |
| `npm run dev`      | Start the server with hot reload (tsx watch).      |
| `npm run build`    | Type-check and emit compiled output to `dist/`.    |
| `npm start`        | Run the compiled server from `dist/`.              |
| `npm run typecheck`| Type-check the project without emitting.           |
| `npm run lint`     | Lint the TypeScript sources with ESLint.           |
| `npm test`         | Run the API test suite with Vitest.                |

## API

| Method   | Path              | Description              |
| -------- | ----------------- | ------------------------ |
| `GET`    | `/api/health`     | Health check.            |
| `GET`    | `/api/tasks`      | List tasks.              |
| `POST`   | `/api/tasks`      | Create a task.           |
| `PATCH`  | `/api/tasks/:id`  | Update title / done.     |
| `DELETE` | `/api/tasks/:id`  | Delete a task.           |

## Configuration

| Env var     | Default              | Description                       |
| ----------- | -------------------- | --------------------------------- |
| `PORT`      | `3000`               | Port the server listens on.       |
| `DATA_FILE` | `data/tasks.json`    | JSON file used to persist tasks.  |

## Cloud Agent environment

The Cloud Agent environment is defined in [`.cursor/environment.json`](.cursor/environment.json):

- `install`: `npm ci` restores dependencies from the lockfile.
- `terminals`: a `dev-server` terminal runs `npm run dev` on port `3000`.
