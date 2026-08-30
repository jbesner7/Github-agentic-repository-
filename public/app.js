const taskList = document.getElementById('task-list');
const form = document.getElementById('new-task-form');
const input = document.getElementById('new-task-input');
const statusEl = document.getElementById('status');

function setStatus(message) {
  statusEl.textContent = message;
}

async function api(path, options) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok && res.status !== 204) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}

function renderTasks(tasks) {
  taskList.innerHTML = '';

  if (tasks.length === 0) {
    const li = document.createElement('li');
    li.className = 'empty';
    li.textContent = 'No tasks yet. Add your first one above.';
    taskList.appendChild(li);
    return;
  }

  for (const task of tasks) {
    const li = document.createElement('li');
    li.className = `task${task.done ? ' task--done' : ''}`;

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'task__checkbox';
    checkbox.checked = task.done;
    checkbox.addEventListener('change', () => toggleTask(task, checkbox.checked));

    const title = document.createElement('span');
    title.className = 'task__title';
    title.textContent = task.title;

    const del = document.createElement('button');
    del.className = 'task__delete';
    del.type = 'button';
    del.setAttribute('aria-label', 'Delete task');
    del.textContent = '×';
    del.addEventListener('click', () => deleteTask(task));

    li.append(checkbox, title, del);
    taskList.appendChild(li);
  }
}

async function loadTasks() {
  try {
    const tasks = await api('/api/tasks');
    renderTasks(tasks);
    setStatus(`${tasks.length} task${tasks.length === 1 ? '' : 's'}.`);
  } catch (err) {
    setStatus(err.message);
  }
}

async function toggleTask(task, done) {
  try {
    await api(`/api/tasks/${task.id}`, { method: 'PATCH', body: JSON.stringify({ done }) });
    await loadTasks();
  } catch (err) {
    setStatus(err.message);
  }
}

async function deleteTask(task) {
  try {
    await api(`/api/tasks/${task.id}`, { method: 'DELETE' });
    await loadTasks();
  } catch (err) {
    setStatus(err.message);
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const title = input.value.trim();
  if (!title) return;
  try {
    await api('/api/tasks', { method: 'POST', body: JSON.stringify({ title }) });
    input.value = '';
    input.focus();
    await loadTasks();
  } catch (err) {
    setStatus(err.message);
  }
});

loadTasks();
