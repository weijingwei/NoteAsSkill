"""MCP 客户端测试"""
import pytest
import json
from app.mcp.client import (
    parse_mcp_config,
    validate_mcp_server_config,
    MCPClient,
)


class TestParseMcpConfig:
    def test_full_format(self):
        json_str = '{"mcpServers": {"server1": {"command": "echo", "args": ["hello"]}}}'
        ok, config, err = parse_mcp_config(json_str)
        assert ok is True
        assert "server1" in config
        assert config["server1"]["command"] == "echo"
        assert err == ""

    def test_direct_format(self):
        json_str = '{"server1": {"command": "echo"}}'
        ok, config, err = parse_mcp_config(json_str)
        assert ok is True
        assert "server1" in config

    def test_invalid_json(self):
        ok, config, err = parse_mcp_config("{invalid}")
        assert ok is False
        assert "JSON" in err

    def test_not_dict(self):
        ok, config, err = parse_mcp_config("[]")
        assert ok is False

    def test_nested_value_not_dict(self):
        ok, config, err = parse_mcp_config('{"server1": "not-a-dict"}')
        assert ok is False


class TestValidateMcpServerConfig:
    def test_valid_config(self):
        ok, err = validate_mcp_server_config({"command": "echo", "args": ["hello"]})
        assert ok is True

    def test_missing_command(self):
        ok, err = validate_mcp_server_config({"args": ["hello"]})
        assert ok is False
        assert "command" in err

    def test_empty_command(self):
        ok, err = validate_mcp_server_config({"command": ""})
        assert ok is False

    def test_invalid_args(self):
        ok, err = validate_mcp_server_config({"command": "echo", "args": "not-list"})
        assert ok is False

    def test_minimal_config(self):
        ok, err = validate_mcp_server_config({"command": "echo"})
        assert ok is True

    def test_invalid_env(self):
        ok, err = validate_mcp_server_config({"command": "echo", "env": "not-dict"})
        assert ok is False


class TestMCPClient:
    def test_call_tool_server_not_running(self):
        from app.mcp.manager import MCPServer
        server = MCPServer(name="test", command="echo")
        client = MCPClient(server)
        result = client.call_tool("test-tool", {})
        assert result["success"] is False
        assert "未运行" in result["error"]

    def test_list_tools_empty(self):
        from app.mcp.manager import MCPServer
        server = MCPServer(name="test", command="echo")
        client = MCPClient(server)
        assert client.list_tools() == []
