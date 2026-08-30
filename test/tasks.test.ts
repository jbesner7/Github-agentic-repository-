import { describe, it, expect, beforeEach } from 'vitest';
import request from 'supertest';
import { createApp } from '../src/app';
import { TaskStore } from '../src/store';

describe('Task API', () => {
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    // Fresh in-memory store (no file persistence) for each test.
    app = createApp(new TaskStore());
  });

  it('health check returns ok', async () => {
    const res = await request(app).get('/api/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });

  it('starts with no tasks', async () => {
    const res = await request(app).get('/api/tasks');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it('creates a task', async () => {
    const res = await request(app).post('/api/tasks').send({ title: 'Write docs' });
    expect(res.status).toBe(201);
    expect(res.body.title).toBe('Write docs');
    expect(res.body.done).toBe(false);
    expect(res.body.id).toBeTruthy();
  });

  it('rejects an empty title', async () => {
    const res = await request(app).post('/api/tasks').send({ title: '   ' });
    expect(res.status).toBe(400);
  });

  it('toggles and deletes a task', async () => {
    const created = await request(app).post('/api/tasks').send({ title: 'Toggle me' });
    const id = created.body.id as string;

    const patched = await request(app).patch(`/api/tasks/${id}`).send({ done: true });
    expect(patched.status).toBe(200);
    expect(patched.body.done).toBe(true);

    const del = await request(app).delete(`/api/tasks/${id}`);
    expect(del.status).toBe(204);

    const list = await request(app).get('/api/tasks');
    expect(list.body).toEqual([]);
  });

  it('returns 404 when updating a missing task', async () => {
    const res = await request(app).patch('/api/tasks/does-not-exist').send({ done: true });
    expect(res.status).toBe(404);
  });
});
