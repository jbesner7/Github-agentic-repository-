import fs from 'node:fs';
import path from 'node:path';

export interface Task {
  id: string;
  title: string;
  done: boolean;
  createdAt: string;
}

export type TaskPatch = Partial<Pick<Task, 'title' | 'done'>>;

/**
 * Small in-memory task store with optional JSON-file persistence.
 * Kept dependency-free so the app runs end-to-end with no external services.
 */
export class TaskStore {
  private tasks: Task[] = [];
  private readonly file?: string;

  constructor(file?: string) {
    this.file = file;
    if (file && fs.existsSync(file)) {
      try {
        this.tasks = JSON.parse(fs.readFileSync(file, 'utf8')) as Task[];
      } catch {
        // Corrupt or partial file: start from an empty list rather than crash.
        this.tasks = [];
      }
    }
  }

  list(): Task[] {
    return [...this.tasks].sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  }

  add(title: string): Task {
    const task: Task = {
      id: `t_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`,
      title,
      done: false,
      createdAt: new Date().toISOString(),
    };
    this.tasks.push(task);
    this.persist();
    return task;
  }

  update(id: string, patch: TaskPatch): Task | undefined {
    const task = this.tasks.find((t) => t.id === id);
    if (!task) return undefined;
    if (typeof patch.title === 'string') task.title = patch.title;
    if (typeof patch.done === 'boolean') task.done = patch.done;
    this.persist();
    return task;
  }

  remove(id: string): boolean {
    const before = this.tasks.length;
    this.tasks = this.tasks.filter((t) => t.id !== id);
    const changed = this.tasks.length !== before;
    if (changed) this.persist();
    return changed;
  }

  private persist(): void {
    if (!this.file) return;
    fs.mkdirSync(path.dirname(this.file), { recursive: true });
    fs.writeFileSync(this.file, JSON.stringify(this.tasks, null, 2));
  }
}
