import path from 'node:path';
import { createApp } from './app';
import { TaskStore } from './store';

const PORT = Number(process.env.PORT) || 3000;
const DATA_FILE = process.env.DATA_FILE || path.join(__dirname, '..', 'data', 'tasks.json');

const store = new TaskStore(DATA_FILE);
const app = createApp(store);

app.listen(PORT, () => {
  console.log(`Task Board running at http://localhost:${PORT}`);
});
