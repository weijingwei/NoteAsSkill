"""MCP 服务器管理模块

管理多个 MCP 服务器的生命周期，包括启动、停止和工具发现。
"""

import asyncio
import json
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, QThread, Slot


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

            # 检查命令是否存在（Windows 需要特殊处理 .cmd 后缀）
            command = self.server.command
            cmd_path = shutil.which(command)

            # Windows: 检查找到的路径是否是 .cmd 文件
            if cmd_path and platform.system() == "Windows" and cmd_path.upper().endswith(".CMD"):
                command = cmd_path

            # Windows: 尝试添加 .cmd 后缀
            if cmd_path is None and platform.system() == "Windows":
                cmd_path = shutil.which(command + ".cmd")
                if cmd_path:
                    command = cmd_path

            # Windows: 使用 shell=True 来正确执行 .cmd 文件
            use_shell = platform.system() == "Windows" and command.upper().endswith(".CMD")

            if use_shell:
                # 对于 .cmd 文件，需要将命令和参数组合成字符串
                full_command = " ".join([command] + self.server.args)
                self.server.process = subprocess.Popen(
                    full_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True,
                    bufsize=1,
                    shell=True,
                )
            else:
                # 非 Windows 或非 .cmd 文件，使用原有逻辑
                self.server.process = subprocess.Popen(
                    [command] + self.server.args,
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
                        "version": "0.2.61"
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

    def list_tools(self) -> list[MCPTool]:
        """列出所有可用工具（get_all_tools 的别名）"""
        return self.get_all_tools()

    def get_tools_for_server(self, name: str) -> list[MCPTool]:
        server = self._servers.get(name)
        return server.tools if server else []

    def call_tool(self, tool_name: str, arguments: dict) -> tuple[str, bool]:
        """调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            tuple[str, bool]: (结果内容, 是否错误)
        """
        # 查找工具所属的服务器
        for server_name, server in self._servers.items():
            for tool in server.tools:
                if tool.name == tool_name:
                    return self._call_tool_on_server(server, tool_name, arguments)

        return f"Error: Tool '{tool_name}' not found", True

    def _call_tool_on_server(self, server: MCPServer, tool_name: str, arguments: dict) -> tuple[str, bool]:
        """在指定服务器上调用工具

        Args:
            server: MCP 服务器实例
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            tuple[str, bool]: (结果内容, 是否错误)
        """
        if not server.process or server.status != "running":
            return f"Error: Server '{server.name}' is not running", True

        try:
            import json

            request = {
                "jsonrpc": "2.0",
                "id": 100,  # 使用固定 ID，每次调用应该递增
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            # 发送请求
            message = json.dumps(request) + "\n"
            server.process.stdin.write(message)
            server.process.stdin.flush()

            # 读取响应
            response = self._read_server_response(server)
            if response is None:
                return "Error: No response from server", True

            if "error" in response:
                error_msg = response["error"].get("message", str(response["error"]))
                return f"Error: {error_msg}", True

            if "result" in response:
                result = response["result"]
                # 处理不同格式的结果
                if isinstance(result, dict):
                    # MCP 返回格式: {"content": [...]}
                    if "content" in result:
                        contents = result["content"]
                        text_parts = []
                        for item in contents:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                            elif isinstance(item, str):
                                text_parts.append(item)
                        return "\n".join(text_parts), False
                    return json.dumps(result, ensure_ascii=False), False
                elif isinstance(result, str):
                    return result, False
                else:
                    return str(result), False

            return "Error: Unexpected response format", True

        except Exception as e:
            return f"Error: {str(e)}", True

    def _read_server_response(self, server: MCPServer) -> dict | None:
        """读取服务器响应

        Args:
            server: MCP 服务器实例

        Returns:
            dict | None: 响应字典或 None
        """
        if server.process and server.process.stdout:
            try:
                line = server.process.stdout.readline()
                if line:
                    return json.loads(line.strip())
            except json.JSONDecodeError:
                pass
        return None

    @Slot(str, list)
    def _on_tools_discovered(self, server_name: str, tools: list[MCPTool]) -> None:
        # 更新服务器的工具列表
        server = self._servers.get(server_name)
        if server:
            server.tools = tools
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
