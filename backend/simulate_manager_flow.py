import requests
import json
import time

BASE_URL = "http://localhost:5000"

def call_api(method, endpoint, data=None, params=None):
    url = f"{BASE_URL}{endpoint}"
    print(f"
--- Calling {method} {url} ---")
    try:
        if method == "POST":
            response = requests.post(url, json=data)
        elif method == "GET":
            response = requests.get(url, params=params)
        
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        print(f"Response Status: {response.status_code}")
        print(f"Response JSON: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error Response Status: {e.response.status_code}")
            print(f"Error Response Text: {e.response.text}")
        return None

def main():
    print("--- Starting Manager Agent Flow Simulation ---")

    # 1. Initialize Project
    print("
[Step 1] Initializing a new project...")
    call_api("POST", "/init", data={"repo_url": "https://github.com/product-team/new-app", "path": "/projects/new-app"})
    time.sleep(1)

    # 2. Manager Agent kicks off an initial task
    print("
[Step 2] Manager Agent kicks off a task: 'Develop core features for new app'.")
    call_api("POST", "/kickoff", data={"project_id": "new-app-project", "task": "Develop core features for new app"})
    time.sleep(1)

    # 3. Simulate a Sub-Agent submitting output
    print("
[Step 3] Simulating 'Design Agent' submitting UI wireframes.")
    call_api("POST", "/submit_agent_output", data={"agent_id": "DesignAgent", "output": "Completed initial UI wireframes for user login and dashboard."})
    time.sleep(1)

    # 4. Simulate a Sub-Agent submitting more output, triggering criticism
    print("
[Step 4] Simulating 'Frontend Agent' submitting code, triggering criticism.")
    call_api("POST", "/submit_agent_output", data={"agent_id": "FrontendAgent", "output": "Implemented login component with React."})
    time.sleep(1)

    # 5. Check project status
    print("
[Step 5] Manager Agent checks project status (todo list).")
    call_api("GET", "/status", params={"id": "new-app-project"})
    time.sleep(1)

    # 6. Simulate LLM calls and check budget
    print("
[Step 6] Simulating several LLM calls, eventually exhausting the budget.")
    for i in range(1, 4):
        print(f"  Simulating LLM call {i} with cost 4.0...")
        response = call_api("POST", "/simulate_llm_call", data={"cost": 4.0})
        if response and response.get("status") == "error":
            print("  Budget exhausted! Manager Agent observes the kill switch activation.")
            break
        time.sleep(1)
    
    # 7. Manager Agent attempts to kickoff a task, but encounters a paused state
    print("
[Step 7] Manager Agent tries to kickoff another task while the system is not explicitly paused.")
    call_api("POST", "/kickoff", data={"project_id": "new-app-project", "task": "Integrate backend API for user auth"})
    time.sleep(1)

    # 8. Explicitly pause the agent (e.g., manager intervention or automated rule)
    print("
[Step 8] Manager Agent or system rule pauses the agent for approval.")
    call_api("POST", "/pause_agent")
    time.sleep(1)

    # 9. Manager Agent tries to kickoff a task while paused
    print("
[Step 9] Manager Agent tries to kickoff a task again, should be blocked by pause.")
    call_api("POST", "/kickoff", data={"project_id": "new-app-project", "task": "Integrate backend API for user auth"})
    time.sleep(1)

    # 10. Manager Agent approves the action
    print("
[Step 10] Manager Agent approves pending action.")
    call_api("POST", "/approve")
    time.sleep(1)

    # 11. Manager Agent tries to kickoff task again, should now succeed
    print("
[Step 11] Manager Agent tries to kickoff task after approval, should succeed.")
    call_api("POST", "/kickoff", data={"project_id": "new-app-project", "task": "Integrate backend API for user auth"})
    time.sleep(1)

    print("
--- Manager Agent Flow Simulation Finished ---")

if __name__ == "__main__":
    main()
