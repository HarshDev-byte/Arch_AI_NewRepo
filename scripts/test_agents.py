"""Agent test runner – smoke-tests each agent."""
import asyncio, sys
sys.path.insert(0, "../backend")

from agents import geo_agent, cost_agent, layout_agent, design_agent

async def main():
    project_id = "test-001"
    print("Testing geo_agent...",    await geo_agent.run(project_id, {}))
    print("Testing cost_agent...",   await cost_agent.run(project_id, {}))
    print("Testing layout_agent...", await layout_agent.run(project_id, {}))
    print("Testing design_agent...", await design_agent.run(project_id, {}))
    print("All agents OK.")

asyncio.run(main())
