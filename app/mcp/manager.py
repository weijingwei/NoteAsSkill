"""MCP 服务器管理模块

管理多个 MCP 服务器的生命周期，包括启动、停止和工具发现。
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, QThread, Slot

from app.core.config import get_version


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)
    server_name: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "server_name": self.server_name,
        }


@dataclass
class MCPServer:
    """MCP 服务器配置和状态"""
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    tools: list[MCPTool] = field(default_factory=list)
    process: subprocess.Popen | None = None
    status: str = "stopped"  # stopped, running, error
    error_message: str = ""

    def to_config(self) -> dict:
        config = {
            "command": self.command,
            "args": self.args,
        }
        if self.env:
            config["env"] = self.env
        return config

    @classmethod
    def from_config(cls, name: str, config: dict) -> "MCPServer":
        return cls(
            name=name,
            command=config.get("command", ""),
            args=config.get("args", []),
            env=config.get("env", {}),
        )


class MCPServerWorker(QThread):
    """MCP 服务器工作线程"""
    tools_discovered = Signal(str, list)  # server_name, tools
    error_occurred = Signal(str, str)  # server_name, error_message
    server_started = Signal(str)  # server_name
    server_stopped = Signal(str)  # server_name

    def __init__(self, server: MCPServer, parent=None):
        super().__init__(parent)
        self.server = server
        self._running = False

    def run(self) -> None:
        self._running = True
        try:
            env = dict(subprocess.os.environ)
            env.update(self.server.env)

            self.server.process = subprocess.Popen(
                [self.server.command] + self.server.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1,
            )

            self.server.status = "running"
            self.server_started.emit(self.server.name)

            self._discover_tools()

        except Exception as e:
            self.server.status = "error"
            self.server.error_message = str(e)
            self.error_occurred.emit(self.server.name, str(e))

    def _discover_tools(self) -> None:
        try:
            initialize_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "NoteAsSkill",
                        "version": get_version().lstrip("v")
                    }
                }
            }

            self._send_request(initialize_request)
            response = self._read_response()

            if not response or "error" in response:
                error_msg = response.get("error", {}).get("message", "初始化失败") if response else "无响应"
                self.error_occurred.emit(self.server.name, f"初始化失败: {error_msg}")
                return

            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            self._send_notification(initialized_notification)

            list_tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }

            self._send_request(list_tools_request)
            tools_response = self._read_response()

            if tools_response and "result" in tools_response:
                tools = []
                for tool_data in tools_response["result"].get("tools", []):
                    tool = MCPTool(
                        name=tool_data.get("name", ""),
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                        server_name=self.server.name,
                    )
                    tools.append(tool)
                self.server.tools = tools
                self.tools_discovered.emit(self.server.name, tools)

        except Exception as e:
            self.error_occurred.emit(self.server.name, f"发现工具失败: {str(e)}")

    def _send_request(self, request: dict) -> None:
        if self.server.process and self.server.process.stdin:
            message = json.dumps(request) + "\n"
            self.server.process.stdin.write(message)
            self.server.process.stdin.flush()

    def _send_notification(self, notification: dict) -> None:
        if self.server.process and self.server.process.stdin:
            message = json.dumps(notification) + "\n"
            self.server.process.stdin.write(message)
            self.server.process.stdin.flush()

    def _read_response(self) -> dict | None:
        if self.server.process and self.server.process.stdout:
            try:
                line = self.server.process.stdout.readline()
                if line:
                    return json.loads(line.strip())
            except json.JSONDecodeError:
                pass
        return None

    def stop(self) -> None:
        self._running = False
        if self.server.process:
            try:
                self.server.process.terminate()
                self.server.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server.process.kill()
            except Exception:
                pass
            finally:
                self.server.process = None
                self.server.status = "stopped"
                self.server_stopped.emit(self.server.name)


class MCPManager(QObject):
    """MCP 服务器管理器（单例）"""

    _instance: "MCPManager | None" = None

    server_started = Signal(str)
    server_stopped = Signal(str)
    server_error = Signal(str, str)
    tools_updated = Signal(str, list)

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, parent=None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        super().__init__(parent)
        self._initialized = True
        self._servers: dict[str, MCPServer] = {}
        self._workers: dict[str, MCPServerWorker] = {}

    @classmethod
    def get_instance(cls) -> "MCPManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_servers(self, servers_config: dict[str, dict]) -> None:
        for name, config in servers_config.items():
            server = MCPServer.from_config(name, config)
            self._servers[name] = server

    def get_servers(self) -> dict[str, MCPServer]:
        return self._servers

    def get_server(self, name: str) -> MCPServer | None:
        return self._servers.get(name)

    def add_server(self, name: str, config: dict) -> MCPServer:
        server = MCPServer.from_config(name, config)
        self._servers[name] = server
        return server

    def remove_server(self, name: str) -> bool:
        if name in self._servers:
            self.stop_server(name)
            del self._servers[name]
            return True
        return False

    def start_server(self, name: str) -> bool:
        server = self._servers.get(name)
        if not server:
            self.server_error.emit(name, "服务器不存在")
            return False

        if server.status == "running":
            return True

        worker = MCPServerWorker(server, self)
        worker.tools_discovered.connect(self._on_tools_discovered)
        worker.error_occurred.connect(self._on_server_error)
        worker.server_started.connect(self._on_server_started)
        worker.server_stopped.connect(self._on_server_stopped)

        self._workers[name] = worker
        worker.start()
        return True

    def stop_server(self, name: str) -> bool:
        worker = self._workers.get(name)
        if worker:
            worker.stop()
            worker.quit()
            worker.wait()
            del self._workers[name]
            return True
        return False

    def start_all_servers(self) -> None:
        for name in self._servers:
            self.start_server(name)

    def stop_all_servers(self) -> None:
        for name in list(self._workers.keys()):
            self.stop_server(name)

    def get_all_tools(self) -> list[MCPTool]:
        tools = []
        for server in self._servers.values():
            tools.extend(server.tools)
        return tools

    def get_tools_for_server(self, name: str) -> list[MCPTool]:
        server = self._servers.get(name)
        return server.tools if server else []

    @Slot(str, list)
    def _on_tools_discovered(self, server_name: str, tools: list[MCPTool]) -> None:
        self.tools_updated.emit(server_name, tools)

    @Slot(str, str)
    def _on_server_error(self, server_name: str, error: str) -> None:
        self.server_error.emit(server_name, error)

    @Slot(str)
    def _on_server_started(self, server_name: str) -> None:
        self.server_started.emit(server_name)

    @Slot(str)
    def _on_server_stopped(self, server_name: str) -> None:
        self.server_stopped.emit(server_name)

    def cleanup(self) -> None:
        self.stop_all_servers()


def get_mcp_manager() -> MCPManager:
    return MCPManager.get_instance()
