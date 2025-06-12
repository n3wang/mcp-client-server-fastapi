from mcp.server.fastmcp import FastMCP

# Create the server
mcp = FastMCP("My Calculator Server")

# Define the calculator tool

# @server.tool(name="evaluate_expression", description="Evaluates a mathematical expression and returns the result")
@mcp.tool()
async def get_evaluate_expression(expression: str) -> float:
    """Evaluates a mathematical expression and returns the result."""
    try:
        # Warning: eval() is unsafe for untrusted input; use a proper parser in production
        result = eval(expression, {"__builtins__": {}}, {"sum": sum})
        return result
    except Exception as e:
        raise ValueError(f"Invalid expression: {e}")

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')