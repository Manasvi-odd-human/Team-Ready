from crewai import Agent

class OrchestratorAgent:
    def __init__(self):
        self.agent = Agent(
            role='Orchestrator',
            goal='Break down high-level goals and assign tasks to other agents.',
            backstory='You are the master of ceremonies, the conductor of the AI orchestra.',
            verbose=True,
            allow_delegation=False
        )

class CoderAgent:
    def __init__(self):
        self.agent = Agent(
            role='Coder',
            goal='Write code based on task descriptions.',
            backstory='You are a master programmer, capable of writing clean, efficient, and bug-free code.',
            verbose=True,
            allow_delegation=False
        )

class CriticAgent:
    def __init__(self):
        self.agent = Agent(
            role='Critic',
            goal='Review code for quality, correctness, and adherence to standards.',
            backstory='You are a meticulous code reviewer with an eye for detail and a passion for quality.',
            verbose=True,
            allow_delegation=False
        )
