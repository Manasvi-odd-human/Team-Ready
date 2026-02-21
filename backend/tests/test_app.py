import pytest
import os
import json
from unittest.mock import patch
from flask_socketio import SocketIO, emit
from io import StringIO

# Ensure the .team-ready directory is unique for testing
TEST_TEAM_READY_DIR = '.team-ready-test'

# Dynamically import the Flask app from the backend directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, socketio, DATA_DIR, TEAM_READY_DIR, read_json_file, write_json_file, append_to_log_file
import app as backend_app # Import app module to access module-level variables

@pytest.fixture
def client():
    # Use a test-specific data directory
    original_data_dir = app.config.get('DATA_DIR', None)
    app.config['DATA_DIR'] = os.path.join(os.getcwd(), TEST_TEAM_READY_DIR)
    
    # Ensure the test data directory is clean before each test
    if os.path.exists(app.config['DATA_DIR']):
        import shutil
        shutil.rmtree(app.config['DATA_DIR'])
    os.makedirs(app.config['DATA_DIR'])

    with app.test_client() as client:
        yield client

    # Clean up the test data directory after each test
    if os.path.exists(app.config['DATA_DIR']):
        import shutil
        shutil.rmtree(app.config['DATA_DIR'])

    # Restore original data directory if it was set
    if original_data_dir is not None:
        app.config['DATA_DIR'] = original_data_dir
    
    # Reset global agent_paused state from the imported app module
    backend_app.agent_paused = False


def test_index_route(client):
    """Test the base route."""
    rv = client.get('/')
    assert rv.status_code == 200
    assert b"Team Ready Backend is running!" in rv.data

def test_init_project(client):
    """Test project initialization."""
    repo_url = "https://github.com/test/repo"
    path = "/user/projects/test_project"
    rv = client.post('/init', json={'repo_url': repo_url, 'path': path})
    assert rv.status_code == 200
    assert "Project initialization request received and data dir ensured." in rv.json['message']

    # Check if .team-ready-test directory is created
    assert os.path.exists(app.config['DATA_DIR'])
    assert os.path.exists(os.path.join(app.config['DATA_DIR'], 'config.json'))
    assert os.path.exists(os.path.join(app.config['DATA_DIR'], 'todo.json'))
    assert os.path.exists(os.path.join(app.config['DATA_DIR'], 'agents_internal.log'))
    assert os.path.exists(os.path.join(app.config['DATA_DIR'], 'decisions.log'))

    config = read_json_file('config.json')
    assert config['hard_limit'] == 10.0
    assert config['project_spend'] == 0.0

def test_status_route_empty_todo(client):
    """Test status route with an empty todo.json."""
    client.post('/init', json={'repo_url': 'a', 'path': 'b'}) # Initialize project first
    rv = client.get('/status?id=test_project_id')
    assert rv.status_code == 200
    assert rv.json['project_id'] == 'test_project_id'
    assert rv.json['todo_list'] == []

def test_simulate_llm_call_and_budget_exhaustion(client):
    """Test LLM call simulation and budget exhaustion."""
    client.post('/init', json={'repo_url': 'a', 'path': 'b'}) # Initialize project
    config_file_path = os.path.join(app.config['DATA_DIR'], 'config.json')
    config = read_json_file('config.json')
    config['hard_limit'] = 1.0 # Set a low limit for testing
    write_json_file('config.json', config)

    # First call, within budget
    rv = client.post('/simulate_llm_call', json={'cost': 0.5})
    assert rv.status_code == 200
    assert "LLM call simulated" in rv.json['message']
    updated_config = read_json_file('config.json')
    assert updated_config['project_spend'] == 0.5

    # Second call, exceeding budget
    rv = client.post('/simulate_llm_call', json={'cost': 0.6})
    assert rv.status_code == 403
    assert "Budget exhausted" in rv.json['message']
    updated_config = read_json_file('config.json')
    assert updated_config['project_spend'] == 1.1 # Spend still updated

def test_pause_and_approve_agent_flow(client):
    """Test pausing and approving agent actions."""
    client.post('/init', json={'repo_url': 'a', 'path': 'b'}) # Initialize project

    # Pause agent
    rv = client.post('/pause_agent')
    assert rv.status_code == 200
    assert "Agent paused." in rv.json['message']
    assert backend_app.agent_paused is True

    # Try to kickoff while paused
    rv = client.post('/kickoff', json={'project_id': 'proj1', 'task': 'task1'})
    assert rv.status_code == 403
    assert "Agent is paused. Approval pending." in rv.json['message']

    # Approve agent
    rv = client.post('/approve')
    assert rv.status_code == 200
    assert "Agent resumed." in rv.json['message']
    assert backend_app.agent_paused is False

    # Try to kickoff after approval
    rv = client.post('/kickoff', json={'project_id': 'proj1', 'task': 'task1'})
    assert rv.status_code == 200
    assert "Agent kickoff request received." in rv.json['message']

def test_submit_agent_output(client):
    """Test submitting agent output and simulated criticism."""
    client.post('/init', json={'repo_url': 'a', 'path': 'b'}) # Initialize project
    
    agent_id = "DesignerAgent"
    output_content = "Here is the new UI wireframe design."
    
    rv = client.post('/submit_agent_output', json={'agent_id': agent_id, 'output': output_content})
    assert rv.status_code == 200
    assert "Agent output submitted and criticism simulated." in rv.json['message']

    # Check agents_internal.log for the output and criticism
    log_file_path = os.path.join(app.config['DATA_DIR'], 'agents_internal.log')
    with open(log_file_path, 'r') as f:
        content = f.read()
    
    assert f"Agent {agent_id} submitted output: {output_content}" in content
    assert f"Critique from Agent X for {agent_id}'s output: This output lacks detail and does not address edge cases. Needs refinement." in content

def test_manager_agent_workflow(client):
    """
    Tests a complete manager agent workflow involving initialization, task kickoff,
    agent output submission, budget management, and pause/approve cycle.
    """
    project_id = "manager-test-project"
    repo_url = "https://github.com/manager/project"
    path = "/tmp/manager_project"

    # 1. Initialize Project
    rv = client.post('/init', json={'repo_url': repo_url, 'path': path})
    assert rv.status_code == 200
    assert "Project initialization request received and data dir ensured." in rv.json['message']
    
    # Verify initial config
    config = read_json_file('config.json')
    assert config['project_spend'] == 0.0

    # 2. Manager Agent kicks off an initial task
    task1 = "Develop core features for new app"
    rv = client.post('/kickoff', json={'project_id': project_id, 'task': task1})
    assert rv.status_code == 200
    assert "Agent kickoff request received." in rv.json['message']
    
    # Verify log content
    log_file_path = os.path.join(app.config['DATA_DIR'], 'agents_internal.log')
    with open(log_file_path, 'r') as f:
        content = f.read()
    assert f"Agent kickoff for project {project_id}: {task1}" in content

    # 3. Simulate a Sub-Agent submitting output
    agent_id_design = "DesignAgent"
    output_design = "Completed initial UI wireframes."
    rv = client.post('/submit_agent_output', json={'agent_id': agent_id_design, 'output': output_design})
    assert rv.status_code == 200
    assert "Agent output submitted and criticism simulated." in rv.json['message']
    
    with open(log_file_path, 'r') as f:
        content = f.read()
    assert f"Agent {agent_id_design} submitted output: {output_design}" in content
    assert f"Critique from Agent X for {agent_id_design}'s output:" in content

    # 4. Check project status
    rv = client.get(f'/status?id={project_id}')
    assert rv.status_code == 200
    assert rv.json['project_id'] == project_id
    # todo_list is still empty as we haven't added items to it in this test

    # 5. Simulate LLM calls and exhaust budget
    config = read_json_file('config.json')
    config['hard_limit'] = 5.0 # Set a low limit for this test
    write_json_file('config.json', config)

    # First call - within budget
    rv = client.post('/simulate_llm_call', json={'cost': 2.0})
    assert rv.status_code == 200
    assert read_json_file('config.json')['project_spend'] == 2.0

    # Second call - exceeds budget
    rv = client.post('/simulate_llm_call', json={'cost': 4.0})
    assert rv.status_code == 403
    assert "Budget exhausted" in rv.json['message']
    assert read_json_file('config.json')['project_spend'] == 6.0 # Spend still updated

    # 6. Manager Agent tries to kickoff a task, but encounters a paused state (implicit check)
    # This also tests the initial state of agent_paused being False
    task_paused = "Task while budget exhausted"
    rv = client.post('/kickoff', json={'project_id': project_id, 'task': task_paused})
    # If budget was exhausted, the agent would be terminated, and this kickoff would not happen
    # For this test, we are simulating the budget exhaustion, but the kickoff logic
    # does not explicitly check the budget status.
    # The important part is that a manager agent would react to the budget exhaustion event.
    assert rv.status_code == 200 # It should still receive the request, but the underlying system would stop

    # 7. Explicitly pause the agent
    rv = client.post('/pause_agent')
    assert rv.status_code == 200
    assert backend_app.agent_paused is True

    # 8. Manager Agent tries to kickoff a task while paused
    task_blocked = "Implement user authentication"
    rv = client.post('/kickoff', json={'project_id': project_id, 'task': task_blocked})
    assert rv.status_code == 403
    assert "Agent is paused. Approval pending." in rv.json['message']

    # 9. Manager Agent approves the action
    rv = client.post('/approve')
    assert rv.status_code == 200
    assert backend_app.agent_paused is False

    # 10. Manager Agent tries to kickoff task again, should now succeed
    task_approved = "Implement user authentication"
    rv = client.post('/kickoff', json={'project_id': project_id, 'task': task_approved})
    assert rv.status_code == 200
    assert "Agent kickoff request received." in rv.json['message']
    
    with open(log_file_path, 'r') as f:
        content = f.read()
    assert f"Agent kickoff for project {project_id}: {task_approved}" in content