import os
import json
import logging
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from filelock import FileLock # Import FileLock

load_dotenv() # Load environment variables from .env file

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_secret_key')
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# Directory for storing project data
TEAM_READY_DIR = '.team-ready'
DATA_DIR = os.path.join(os.getcwd(), TEAM_READY_DIR)

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ensure_data_dir():
    """Ensures the .team-ready directory exists."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def get_file_path(filename):
    """Returns the full path for a file within the DATA_DIR, respecting app.config['DATA_DIR'] if set."""
    if 'DATA_DIR' in app.config:
        return os.path.join(app.config['DATA_DIR'], filename)
    return os.path.join(DATA_DIR, filename)

def read_json_file(filename, default_value=None):
    """Reads a JSON file with a file lock."""
    filepath = get_file_path(filename)
    lockpath = filepath + ".lock"
    lock = FileLock(lockpath)
    with lock:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return default_value

def write_json_file(filename, data):
    """Writes data to a JSON file with a file lock."""
    filepath = get_file_path(filename)
    lockpath = filepath + ".lock"
    lock = FileLock(lockpath)
    with lock:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

def append_to_log_file(filename, message):
    """Appends a message to a log file with a file lock, redacting sensitive information."""
    filepath = get_file_path(filename)
    lockpath = filepath + ".lock"
    lock = FileLock(lockpath) # Instantiate FileLock here
    
    # Basic sensitive data redaction
    sensitive_keywords = ["API_KEY", "SECRET", "PASSWORD", "TOKEN"]
    for keyword in sensitive_keywords:
        message = message.replace(keyword, "[REDACTED]")

    with lock:
        with open(filepath, 'a') as f:
            f.write(message + '\n')

def get_precis():
    """
    Reads the last 10 lines from agents_internal.log and returns them as a formatted string (The Precis).
    """
    filepath = get_file_path('agents_internal.log')
    lockpath = filepath + ".lock"
    lock = FileLock(lockpath)
    precis = "No internal agent logs yet."
    with lock:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                lines = f.readlines()
                last_10_lines = [line.strip() for line in lines[-10:]]
                if last_10_lines:
                    precis = "Previous internal agent thoughts:\n" + "\n".join(last_10_lines)
    return precis

def emit_internal_chat(message):
    """Emits a message to the internal_chat Socket.io channel."""
    logging.info(f"Internal Chat: {message}")
    socketio.emit('internal_chat', {'data': message})

def emit_client_chat(message):
    """Emits a message to the client_chat Socket.io channel."""
    logging.info(f"Client Chat: {message}")
    socketio.emit('client_chat', {'data': message})

def update_project_spend(cost):
    """
    Updates the project spend and checks against the hard limit.
    If the limit is reached, emits a BUDGET_EXHAUSTED event.
    """
    config = read_json_file('config.json')
    if config is None:
        logging.error("config.json not found or empty.")
        return

    config['project_spend'] += cost
    write_json_file('config.json', config)

    if config['project_spend'] >= config['hard_limit']:
        emit_client_chat("BUDGET_EXHAUSTED: Project spend limit reached! Agent process will be terminated.")
        # Placeholder for actual SIGKILL. This would involve tracking the agent process PID.
        logging.warning("Hard spending limit reached. Agent process would be terminated here.")
        return True
    return False

# Global state for agent pausing
agent_paused = False

@app.route('/')
def index():
    return "Team Ready Backend is running!"

@app.route('/approve', methods=['POST'])
def approve_agent():
    global agent_paused
    agent_paused = False
    emit_client_chat("Agent action approved. Resuming operations.")
    return jsonify({"status": "success", "message": "Agent resumed."})

@app.route('/pause_agent', methods=['POST'])
def pause_agent():
    global agent_paused
    agent_paused = True
    emit_client_chat("Agent paused for approval.")
    return jsonify({"status": "success", "message": "Agent paused."})

@app.route('/init', methods=['POST'])
def init_project():
    data = request.get_json()
    repo_url = data.get('repo_url')
    path = data.get('path')
    print(f"Init project: {repo_url} at {path}")
    
    ensure_data_dir()
    
    # Initialize config.json if it doesn't exist
    config = read_json_file('config.json', {})
    if not config:
        config = {
            "hard_limit": 10.0, # Example hard spending limit
            "project_spend": 0.0,
            "approval_level": "strict"
        }
        write_json_file('config.json', config)

    # Initialize todo.json if it doesn't exist
    todo_list = read_json_file('todo.json', [])
    if not todo_list:
        write_json_file('todo.json', [])

    append_to_log_file('agents_internal.log', 'Project initialized.')
    append_to_log_file('decisions.log', 'Project initialized.')
    emit_client_chat("Project initialized successfully.")

    return jsonify({"status": "success", "message": "Project initialization request received and data dir ensured."})

@app.route('/kickoff', methods=['POST'])
def kickoff_agent():
    global agent_paused
    if agent_paused:
        emit_client_chat("Agent is paused. Approval required to resume operations.")
        return jsonify({"status": "error", "message": "Agent is paused. Approval pending."}), 403

    data = request.get_json()
    project_id = data.get('project_id')
    task = data.get('task')
    
    precis = get_precis()
    
    logging.info(f"Kickoff agent for project {project_id} with task: {task}. Context: {precis}")
    append_to_log_file('agents_internal.log', f"Agent kickoff for project {project_id}: {task}\nContext:\n{precis}")
    append_to_log_file('decisions.log', f"Agent kickoff for project {project_id}: {task}")
    emit_internal_chat(f"Agent {project_id} kicked off with task: {task}\nContext:\n{precis}")
    emit_client_chat(f"Agent {project_id} started on task: {task}")
    # Placeholder for starting CrewAI async background process
    return jsonify({"status": "success", "message": "Agent kickoff request received."})

@app.route('/stop', methods=['POST'])
def stop_agent():
    data = request.get_json()
    project_id = data.get('project_id')
    logging.info(f"Stop agent for project: {project_id}")
    append_to_log_file('agents_internal.log', f"Agent stop requested for project: {project_id}")
    append_to_log_file('decisions.log', f"Agent stop requested for project: {project_id}")
    emit_internal_chat(f"Agent {project_id} stop request received.")
    emit_client_chat(f"Agent {project_id} has been stopped.")
    # Placeholder for immediate process termination
    return jsonify({"status": "success", "message": "Agent stop request received."})

@app.route('/status', methods=['GET'])
def get_status():
    project_id = request.args.get('id')
    print(f"Get status for project: {project_id}")
    
    todo_list = read_json_file('todo.json', [])
    return jsonify({"status": "success", "project_id": project_id, "todo_list": todo_list})

@app.route('/simulate_llm_call', methods=['POST'])
def simulate_llm_call():
    data = request.get_json()
    cost = data.get('cost', 0.0)
    
    budget_exhausted = update_project_spend(cost)
    
    if budget_exhausted:
        return jsonify({"status": "error", "message": "Budget exhausted, agent process terminated."}), 403
    return jsonify({"status": "success", "message": f"LLM call simulated, cost {cost} added."})

@app.route('/submit_agent_output', methods=['POST'])
def submit_agent_output():
    data = request.get_json()
    agent_id = data.get('agent_id', 'UnknownAgent')
    output = data.get('output', 'No output provided.')

    message_to_log = f"Agent {agent_id} submitted output: {output}"
    append_to_log_file('agents_internal.log', message_to_log)
    emit_internal_chat(message_to_log)
    emit_client_chat(f"Agent {agent_id} has submitted output. Reviewing...")

    # Simulate criticism from another agent
    criticism = f"Critique from Agent X for {agent_id}'s output: This output lacks detail and does not address edge cases. Needs refinement."
    append_to_log_file('agents_internal.log', criticism)
    emit_internal_chat(criticism)
    emit_client_chat(f"Critique for {agent_id}'s output has been generated.")

    return jsonify({"status": "success", "message": "Agent output submitted and criticism simulated."})


@socketio.on('connect')
def test_connect():
    print('Client connected')
    emit('my response', {'data': 'Connected'})

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    ensure_data_dir()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
