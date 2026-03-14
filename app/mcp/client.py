"""MCP 客户端模块

提供 MCP 工具调用的同步封装。
"""

import json
import subprocess
from typing import Any

from .manager import MCPServer, MCPTool


class MCPClient:
    """MCP 客户端 - 同步封装"""

    def __init__(self, server: MCPServer):
        self.server = server
        self._request_id = 0

    def _get_next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def call_tool(self, tool_name: str, arguments: dict[str, Any] = None) -> dict:
        """调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具调用结果
        """
        if self.server.process is None or self.server.status != "running":
            return {
                "success": False,
                "error": "服务器未运行",
            }

        if arguments is None:
            arguments = {}

        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            }
        }

        try:
            self._send_request(request)
            response = self._read_response()

            if response is None:
                return {
                    "success": False,
                    "error": "无响应",
                }

            if "error" in response:
                return {
                    "success": False,
                    "error": response["error"].get("message", "未知错误"),
                }

            result = response.get("result", {})
            return {
                "success": True,
                "result": result,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _send_request(self, request: dict) -> None:
        if self.server.process and self.server.process.stdin:
            message = json.dumps(request) + "\n"
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

    def list_tools(self) -> list[MCPTool]:
        """获取服务器提供的工具列表"""
        return self.server.tools


def parse_mcp_config(json_str: str) -> tuple[bool, dict[str, dict] | None, str]:
    """解析 MCP 配置 JSON，支持两种格式

    支持的格式:
    1. 带 mcpServers 键的完整格式:
       {"mcpServers": {"server-name": {"command": "...", "args": [...]}}}

    2. 直接服务器配置格式:
       {"server-name": {"command": "...", "args": [...]}}

    Args:
        json_str: JSON 字符串

    Returns:
        (是否成功, 解析后的服务器配置字典, 错误信息)
        服务器配置字典格式: {"server-name": {"command": "...", "args": [...]}}
    """
    try:
        config = json.loads(json_str)
    except json.JSONDecodeError as e:
        error_msg = f"JSON 语法错误 (行 {e.lineno}, 列 {e.colno}): {e.msg}"
        return False, None, error_msg

    if not isinstance(config, dict):
        return False, None, "配置必须是字典格式"

    if "mcpServers" in config:
        servers = config["mcpServers"]
        if not isinstance(servers, dict):
            return False, None, "'mcpServers' 必须是字典格式"
        return True, servers, ""

    for key, value in config.items():
        if not isinstance(key, str):
            return False, None, "服务器名称必须是字符串"
        if not isinstance(value, dict):
            return False, None, f"服务器 '{key}' 的配置必须是字典格式"

    return True, config, ""


def validate_mcp_server_config(config: dict) -> tuple[bool, str]:
    """验证 MCP 服务器配置

    Args:
        config: 服务器配置字典

    Returns:
        (是否有效, 错误信息)
    """
    if not isinstance(config, dict):
        return False, "配置必须是字典格式"

    if "command" not in config:
        return False, "缺少必需字段 'command'"

    if not isinstance(config["command"], str):
        return False, "'command' 必须是字符串"

    if not config["command"].strip():
        return False, "'command' 不能为空"

    if "args" in config:
        if not isinstance(config["args"], list):
            return False, "'args' 必须是列表"
        for i, arg in enumerate(config["args"]):
            if not isinstance(arg, str):
                return False, f"'args[{i}]' 必须是字符串"

    if "env" in config:
        if not isinstance(config["env"], dict):
            return False, "'env' 必须是字典"
        for key, value in config["env"].items():
            if not isinstance(key, str):
                return False, "'env' 的键必须是字符串"
            if not isinstance(value, str):
                return False, f"'env[{key}]' 的值必须是字符串"

    return True, ""


def test_mcp_server_connection(config: dict, timeout: int = 10) -> tuple[bool, str, list[str]]:
    """测试 MCP 服务器连接

    Args:
        config: 服务器配置
        timeout: 超时时间（秒）

    Returns:
        (是否成功, 消息, 发现的工具列表)
    """
    is_valid, error = validate_mcp_server_config(config)
    if not is_valid:
        return False, f"配置验证失败: {error}", []

    try:
        import subprocess
        import os
        import shutil
        import platform

        # 检查命令是否存在（Windows 需要特殊处理 .cmd 后缀）
        command = config["command"]
        cmd_path = shutil.which(command)

        # Windows: 检查找到的路径是否是 .cmd 文件
        if cmd_path and platform.system() == "Windows" and cmd_path.upper().endswith(".CMD"):
            command = cmd_path  # 使用完整路径

        # Windows: 尝试添加 .cmd 后缀（如果上面的查找失败）
        if cmd_path is None and platform.system() == "Windows":
            cmd_path = shutil.which(command + ".cmd")
            if cmd_path:
                command = cmd_path  # 使用完整路径

        if cmd_path is None:
            return False, f"找不到命令「{config['command']}」，请确保已安装并在 PATH 中", []

        env = dict(os.environ)
        if "env" in config:
            env.update(config["env"])

        # Windows: 使用 shell=True 来正确执行 .cmd 文件
        use_shell = platform.system() == "Windows" and command.upper().endswith(".CMD")

        if use_shell:
            # 对于 .cmd 文件，需要将命令和参数组合成字符串
            full_command = " ".join([command] + config.get("args", []))
            process = subprocess.Popen(
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
            process = subprocess.Popen(
                [command] + config.get("args", []),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1,
            )

        try:
            init_request = {
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

            message = json.dumps(init_request) + "\n"
            process.stdin.write(message)
            process.stdin.flush()

            import threading
            import queue

            result_queue = queue.Queue()

            def read_output():
                try:
                    line = process.stdout.readline()
                    if line:
                        result_queue.put(("stdout", line))
                except Exception as e:
                    result_queue.put(("error", str(e)))

            thread = threading.Thread(target=read_output, daemon=True)
            thread.start()

            try:
                source, data = result_queue.get(timeout=timeout)
                if source == "error":
                    return False, f"读取响应失败: {data}", []

                response = json.loads(data.strip())
                if "error" in response:
                    return False, f"初始化失败: {response['error'].get('message', '未知错误')}", []

                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                process.stdin.write(json.dumps(initialized_notification) + "\n")
                process.stdin.flush()

                list_tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }

                result_queue = queue.Queue()

                def read_tools():
                    try:
                        line = process.stdout.readline()
                        if line:
                            result_queue.put(("stdout", line))
                    except Exception as e:
                        result_queue.put(("error", str(e)))

                thread = threading.Thread(target=read_tools, daemon=True)
                thread.start()

                process.stdin.write(json.dumps(list_tools_request) + "\n")
                process.stdin.flush()

                source, data = result_queue.get(timeout=timeout)
                if source == "error":
                    return True, "连接成功，但无法获取工具列表", []

                tools_response = json.loads(data.strip())
                tools = []
                if "result" in tools_response:
                    for tool_data in tools_response["result"].get("tools", []):
                        tools.append(tool_data.get("name", ""))

                return True, f"连接成功，发现 {len(tools)} 个工具", tools

            except queue.Empty:
                return False, f"连接超时（{timeout}秒内无响应）", []

        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

    except FileNotFoundError:
        return False, f"找不到命令: {config['command']}", []
    except PermissionError:
        return False, f"没有权限执行命令: {config['command']}", []
    except Exception as e:
        return False, f"连接失败: {str(e)}", []
