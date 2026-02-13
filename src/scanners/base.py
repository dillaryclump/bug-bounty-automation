"""
Base scanner class providing common functionality for all scanner tools.
"""

import asyncio
import json
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
import tempfile

from src.utils.logging import get_logger

logger = get_logger(__name__)


class ScannerError(Exception):
    """Base exception for scanner errors."""
    pass


class ScannerNotInstalledError(ScannerError):
    """Raised when a required scanner tool is not installed."""
    pass


class BaseScanner(ABC):
    """Base class for all scanner tool integrations."""

    def __init__(self, binary_name: str) -> None:
        """
        Initialize scanner.
        
        Args:
            binary_name: Name of the binary executable (e.g., 'subfinder')
        """
        self.binary_name = binary_name
        self.binary_path = self._find_binary()

    def _find_binary(self) -> str:
        """Find the scanner binary in PATH."""
        try:
            result = subprocess.run(
                ["where" if subprocess.sys.platform == "win32" else "which", self.binary_name],
                capture_output=True,
                text=True,
                check=True,
            )
            binary_path = result.stdout.strip().split("\n")[0]
            logger.debug(f"Found {self.binary_name} at: {binary_path}")
            return binary_path
        except subprocess.CalledProcessError:
            raise ScannerNotInstalledError(
                f"{self.binary_name} is not installed or not in PATH. "
                f"Please install it first."
            )

    async def _run_command(
        self,
        args: List[str],
        timeout: Optional[int] = None,
        input_data: Optional[str] = None,
    ) -> tuple[str, str, int]:
        """
        Run scanner command asynchronously.
        
        Args:
            args: Command arguments
            timeout: Timeout in seconds
            input_data: Optional stdin input
            
        Returns:
            (stdout, stderr, return_code)
        """
        cmd = [self.binary_path] + args
        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if input_data else None,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=input_data.encode() if input_data else None),
                    timeout=timeout,
                )
                return stdout.decode(), stderr.decode(), process.returncode or 0
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise ScannerError(f"Command timed out after {timeout} seconds")

        except Exception as e:
            raise ScannerError(f"Failed to run {self.binary_name}: {e}")

    def _parse_json_lines(self, output: str) -> List[Dict[str, Any]]:
        """Parse JSON lines output (one JSON object per line)."""
        results = []
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON line: {line[:100]}... Error: {e}")
        return results

    def _create_temp_file(self, content: str, suffix: str = ".txt") -> Path:
        """Create a temporary file with content."""
        fd, path = tempfile.mkstemp(suffix=suffix)
        with open(fd, "w") as f:
            f.write(content)
        return Path(path)

    @abstractmethod
    async def scan(self, *args: Any, **kwargs: Any) -> Any:
        """Execute scan. Must be implemented by subclasses."""
        pass

    async def check_installation(self) -> Dict[str, Any]:
        """Check if scanner is installed and get version info."""
        try:
            stdout, stderr, code = await self._run_command(["-version"], timeout=5)
            return {
                "installed": True,
                "path": self.binary_path,
                "version": stdout.strip() or stderr.strip(),
            }
        except Exception as e:
            return {
                "installed": False,
                "error": str(e),
            }
