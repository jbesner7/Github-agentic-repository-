import path from 'node:path';
import express from 'express';
import { TaskStore } from './store';

/**
 * Builds the Express application. Kept separate from server startup so tests
 * can exercise the routes without binding a network port.
 */
export function createApp(store: TaskStore): express.Express {
  const app = express();
  app.use(express.json());

  const publicDir = path.join(__dirname, '..', 'public');
  app.use(express.static(publicDir));

  app.get('/api/health', (_req, res) => {
    res.json({ status: 'ok' });
  });

  app.get('/api/tasks', (_req, res) => {
    res.json(store.list());
  });

  app.post('/api/tasks', (req, res) => {
    const rawTitle: unknown = req.body?.title;
    const title = typeof rawTitle === 'string' ? rawTitle.trim() : '';
    if (!title) {
      res.status(400).json({ error: 'title is required' });
      return;
    }
    res.status(201).json(store.add(title));
  });

  app.patch('/api/tasks/:id', (req, res) => {
    const rawTitle: unknown = req.body?.title;
    const rawDone: unknown = req.body?.done;
    const task = store.update(req.params.id, {
      title: typeof rawTitle === 'string' ? rawTitle : undefined,
      done: typeof rawDone === 'boolean' ? rawDone : undefined,
    });
    if (!task) {
      res.status(404).json({ error: 'not found' });
      return;
    }
    res.json(task);
  });

  app.delete('/api/tasks/:id', (req, res) => {
    if (!store.remove(req.params.id)) {
      res.status(404).json({ error: 'not found' });
      return;
    }
    res.status(204).end();
  });

  return app;
}
