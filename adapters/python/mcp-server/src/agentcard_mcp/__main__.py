"""
agentcard_mcp.__main__
======================

Entry point for ``python -m agentcard_mcp``.

Usage:
    python -m agentcard_mcp              # stdio transport (default)
    python -m agentcard_mcp --http       # HTTP/SSE on port 8890
    python -m agentcard_mcp --port 9000  # HTTP/SSE on custom port
"""

import sys

from .server import mcp


def main() -> None:
    args = sys.argv[1:]
    if "--http" in args:
        port_idx = args.index("--port") if "--port" in args else -1
        port = int(args[port_idx + 1]) if port_idx >= 0 else 8890
        mcp.run(transport="sse", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
