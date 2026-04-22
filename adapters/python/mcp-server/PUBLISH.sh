#!/usr/bin/env bash
# PUBLISH.sh — Publish agentcard-mcp to PyPI then register with MCP Registry
#
# Run this script from adapters/python/mcp-server/
# Requires: pip install build twine  AND  mcp-publisher in PATH
#
# MCP registry name: io.github.kwailapt/agentcard
# PyPI name:         agentcard-mcp

set -euo pipefail

echo "=== Step 1: Build wheel + sdist ==="
python3 -m build

echo ""
echo "=== Step 2: Upload to PyPI ==="
echo "You will need your PyPI API token. Set TWINE_PASSWORD or enter interactively."
python3 -m twine upload dist/*

echo ""
echo "=== Step 3: Verify PyPI package is live ==="
echo "Waiting 30s for PyPI to index..."
sleep 30
pip index versions agentcard-mcp 2>/dev/null || curl -s "https://pypi.org/pypi/agentcard-mcp/json" | python3 -c "import sys,json; d=json.load(sys.stdin); print('PyPI:', d['info']['version'])"

echo ""
echo "=== Step 4: Publish to MCP Registry ==="
# mcp-publisher must be authenticated (mcp-publisher login github)
mcp-publisher publish

echo ""
echo "=== Done! ==="
echo "agentcard-mcp is now live at:"
echo "  PyPI:         https://pypi.org/project/agentcard-mcp/"
echo "  MCP Registry: https://registry.modelcontextprotocol.io/servers/io.github.kwailapt%2Fagentcard"
echo ""
echo "Also track the PR to modelcontextprotocol/servers:"
echo "  https://github.com/modelcontextprotocol/servers/pull/4015"
