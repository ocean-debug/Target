"""Protocol smoke for the installed Target stdio MCP entry point."""
from __future__ import annotations

import asyncio
import sys

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client


async def _run() -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "target_agent.mcp_server"],
    )
    async with Client(stdio_client(server)) as client:
        listed = await client.list_tools()
        names = {tool.name for tool in listed.tools}
        expected = {
            "target_capabilities",
            "target_create_disease_project",
            "target_run_project",
            "target_get_project",
            "target_list_projects",
            "target_get_events",
            "target_get_domain_activities",
            "target_accept_checkpoint",
            "target_read_text_artifact",
        }
        missing = expected - names
        if missing:
            raise RuntimeError(f"Target MCP tools are missing: {sorted(missing)}")
        result = await client.call_tool("target_capabilities", {})
        payload = result.structured_content
        if payload is None or payload.get("research_contract_version") != "3.0.0":
            raise RuntimeError("Target MCP capabilities did not return the research contract witness")
        print(f"TARGET_MCP_STDIO_TOOLS={len(names)}")
        print("TARGET_MCP_STDIO=OK")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
