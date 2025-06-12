import asyncio
import sys
from typing import Optional, List
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

class MCPClient:
    def __init__(self):
        self.sessions: List[ClientSession] = []
        self.all_tools = []
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()



    async def connect_from_config(self, config: dict):
        """Connect to multiple MCP servers from a configuration dictionary."""
        servers = config.get("mcpServers", {})
        for name, server in servers.items():
            command = server.get("command")
            args = server.get("args", [])

            if not command:
                raise ValueError(f"Missing 'command' for server '{name}'")

            server_params = StdioServerParameters(command=command, args=args)
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
            await session.initialize()

            self.sessions.append(session)
            response = await session.list_tools()
            self.all_tools.extend(response.tools)

            print(f"\nConnected to '{name}' with tools:", [tool.name for tool in response.tools])
            
            
    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server and store session/tools."""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()

        self.sessions.append(session)

        response = await session.list_tools()
        self.all_tools.extend(response.tools)

        print("\nModded Client Connected to server with tools:", [tool.name for tool in response.tools])

    async def call_tool_from_any_session(self, tool_name: str, tool_args: dict):
        """Try calling tool on the first session that has it."""
        for session in self.sessions:
            tools = await session.list_tools()
            for tool in tools.tools:
                if tool.name == tool_name:
                    return await session.call_tool(tool_name, tool_args)
        raise RuntimeError(f"Tool '{tool_name}' not found in any session.")

    async def process_query(self, messages) -> str:
        """Process a query using Claude and available tools."""
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in self.all_tools]

        # Uses claude-3-5-sonnet model for this. This should be something that we can replace correct?
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            tools=available_tools
        )
        print('response called in process query', response, messages)
        print('=====')
        print(response)

        final_text = []
        assistant_message_content = []

        for content in response.content:
            if content.type == 'text':
                print('=============== TEXT ================')
                print('text', content.text)
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == 'tool_use':
                print('================TOOL USE===============')
                tool_name = content.name
                tool_args = content.input

                # Call tool from appropriate session
                result = await self.call_tool_from_any_session(tool_name, tool_args)

                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                assistant_message_content.append(content)
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": result.content
                        }
                    ]
                })

                # Recursive Claude follow-up with tool result
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools
                )
                print('response called inside tool use with', response, messages)

                final_text.append(response.content[0].text)
                print('=====')
                print(response)
                break  # Optional: prevent multiple tool uses at once

        return "\n".join(final_text)

    async def chat(self, messages):
        """Run a single interaction with Claude and tools."""
        print("\nMCP Client Started!")
        try:
            return await self.process_query(messages)
        except Exception as e:
            print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up all open sessions."""
        await self.exit_stack.aclose()

# === CLI runner ===

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script> [<path_to_server_script2> ...]")
        sys.exit(1)

    client = MCPClient()
    try:
        for path in sys.argv[1:]:
            await client.connect_to_server(path)

        # Example message payload (replace or modify this for testing)
        user_messages = [
            {"role": "user", "content": "What's the time? Can you also read from a file?"}
        ]
        result = await client.chat(user_messages)
        print("\nResponse:\n", result)

    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
