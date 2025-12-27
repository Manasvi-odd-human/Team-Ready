function handleAction(actionName) {
    console.log(`Action triggered: ${actionName}`);
    alert(`Action: ${actionName} simulated.`);
}

function goToDashboard() {
    console.log('Navigate: Dashboard');
}

function goToMyTasks() {
    console.log('Navigate: My Tasks');
}

function goToProjectFiles() {
    console.log('Navigate: Project Files');
}

function goToTeamConfiguration() {
    console.log('Navigate: Team Configuration');
}

function createNewProject() {
    console.log('Action: New Project');
}

function createNewTask() {
    console.log('Action: New Task');
}

function toggleCrewAIStatus() {
    const dd = document.getElementById('crewai-status-dropdown');
    const open = dd.classList.contains('open');
    if (open) {
        dd.classList.remove('open');
        return;
    }
    eel.get_system_status()().then(r => {
        const el = document.getElementById('crewai-status-content');
        el.textContent = typeof r === 'string' ? r : JSON.stringify(r);
        dd.classList.add('open');
    }).catch(() => {
        dd.classList.add('open');
    });
}

function performSearch() {
    const q = document.getElementById('global-search').value;
    console.log(`Search: ${q}`);
}

function openNotifications() {
    const b = document.getElementById('notification-badge');
    const v = parseInt(b.textContent || '0', 10);
    b.textContent = String(Math.max(0, v - 1));
    console.log('Notifications opened');
}

function openUserSettings() {
    console.log('Open user settings');
}

function login() {
    const u = document.getElementById('login-username').value;
    const p = document.getElementById('login-password').value;
    eel.auth_login(u, p)().catch(() => {});
}

function logout() {
    eel.auth_logout()().catch(() => {});
}

function submitPrompt() {
    const prompt = document.getElementById('prompt-input').value;
    eel.crewai_submit_prompt(prompt)().then(r => {
        const el = document.getElementById('prompt-response');
        el.textContent = typeof r === 'string' ? r : JSON.stringify(r);
    }).catch(() => {});
}

function refreshEmployees() {
    eel.get_employee_overview()().then(r => {
        document.getElementById('employees-overview').textContent = JSON.stringify(r);
    }).catch(() => {});
}

function assignTask() {
    const employee = document.getElementById('task-employee').value;
    const description = document.getElementById('task-description').value;
    const dueDate = document.getElementById('task-due-date').value;
    eel.assign_task(employee, description, dueDate || null)().catch(() => {});
}

function updateTaskStatus() {
    const id = document.getElementById('update-task-id').value;
    const status = document.getElementById('update-task-status').value;
    eel.update_task_status(id, status)().catch(() => {});
}

function sendChatMessage() {
    const target = document.getElementById('chat-target').value;
    const message = document.getElementById('chat-message').value;
    eel.send_chat_message(target, message)().catch(() => {});
}

function refreshProjects() {
    eel.list_projects()().then(r => {
        document.getElementById('projects-list').textContent = JSON.stringify(r);
    }).catch(() => {});
}

function selectProject() {
    const id = document.getElementById('select-project-id').value;
    eel.select_project(id)().catch(() => {});
}

function refreshFiles() {
    const proj = document.getElementById('select-project-id').value;
    eel.list_project_files(proj)().then(r => {
        document.getElementById('files-list').textContent = JSON.stringify(r);
    }).catch(() => {});
}

function refreshSystemStatus() {
    eel.get_system_status()().then(r => {
        document.getElementById('system-status').textContent = JSON.stringify(r);
    }).catch(() => {});
}
