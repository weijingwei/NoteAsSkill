"""MCP Manager 测试"""
import pytest
from app.mcp.manager import (
    MCPTool, MCPServer, MCPManager,
    get_mcp_manager,
)


class TestMCPTool:
    def test_defaults(self):
        tool = MCPTool(name="test-tool")
        assert tool.description == ""
        assert tool.input_schema == {}
        assert tool.server_name == ""

    def test_to_dict(self):
        tool = MCPTool(name="test", description="desc", input_schema={"type": "object"})
        d = tool.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "desc"


class TestMCPServer:
    def test_from_config(self):
        config = {"command": "echo", "args": ["hello"], "env": {"KEY": "val"}}
        server = MCPServer.from_config("my-server", config)
        assert server.name == "my-server"
        assert server.command == "echo"
        assert server.args == ["hello"]
        assert server.env == {"KEY": "val"}

    def test_to_config(self):
        server = MCPServer(name="test", command="echo", args=["-n", "hello"])
        config = server.to_config()
        assert config["command"] == "echo"
        assert config["args"] == ["-n", "hello"]

    def test_to_config_without_env(self):
        server = MCPServer(name="test", command="echo")
        config = server.to_config()
        assert "env" not in config
        assert config["command"] == "echo"

    def test_default_status(self):
        server = MCPServer(name="test", command="echo")
        assert server.status == "stopped"
        assert server.process is None


class TestMCPManager:
    def test_singleton(self):
        m1 = MCPManager()
        m2 = MCPManager()
        assert m1 is m2

    def test_get_instance(self):
        instance = MCPManager.get_instance()
        assert instance is not None

    def test_load_servers(self):
        manager = MCPManager()
        manager._servers.clear()
        manager._workers.clear()

        config = {
            "server1": {"command": "echo", "args": ["hello"]},
            "server2": {"command": "ls"},
        }
        manager.load_servers(config)

        servers = manager.get_servers()
        assert "server1" in servers
        assert "server2" in servers

    def test_get_server(self):
        manager = MCPManager()
        manager._servers.clear()
        manager._workers.clear()

        manager.add_server("test", {"command": "echo"})
        server = manager.get_server("test")
        assert server is not None
        assert server.command == "echo"

    def test_get_nonexistent_server(self):
        manager = MCPManager()
        assert manager.get_server("nonexistent") is None

    def test_add_server(self):
        manager = MCPManager()
        manager._servers.clear()
        manager._workers.clear()

        server = manager.add_server("new", {"command": "cat"})
        assert server.name == "new"
        assert server.command == "cat"

    def test_remove_server(self):
        manager = MCPManager()
        manager._servers.clear()
        manager._workers.clear()

        manager.add_server("del", {"command": "echo"})
        assert manager.remove_server("del") is True
        assert manager.get_server("del") is None

    def test_remove_nonexistent_server(self):
        manager = MCPManager()
        assert manager.remove_server("nonexistent") is False

    def test_start_nonexistent_server(self):
        manager = MCPManager()
        manager._servers.clear()
        manager._workers.clear()
        assert manager.start_server("nonexistent") is False

    def test_stop_nonexistent_server(self):
        manager = MCPManager()
        assert manager.stop_server("nonexistent") is False

    def test_get_all_tools_empty(self):
        manager = MCPManager()
        manager._servers.clear()
        manager._workers.clear()
        assert manager.get_all_tools() == []

    def test_list_tools_empty(self):
        manager = MCPManager()
        manager._servers.clear()
        manager._workers.clear()
        assert manager.list_tools() == []

    def test_get_tools_for_server_empty(self):
        manager = MCPManager()
        manager._servers.clear()
        manager._workers.clear()
        assert manager.get_tools_for_server("test") == []

    def test_call_tool_not_found(self):
        manager = MCPManager()
        manager._servers.clear()
        manager._workers.clear()
        result, is_error = manager.call_tool("nonexistent-tool", {})
        assert "not found" in result.lower() or "not found" in result
        assert is_error is True

    def test_cleanup(self):
        manager = MCPManager()
        manager._servers.clear()
        manager._workers.clear()
        manager.cleanup()
