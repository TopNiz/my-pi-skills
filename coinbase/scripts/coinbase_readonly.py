"""Run only allowlisted read-only Coinbase operations after a VPN egress check."""

from __future__ import annotations

import ipaddress
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
REPOSITORY = Path("/Users/nizarayed/MyDocuments/002-git/xrp-strategy")
ENV_PATH = SKILL_DIR / ".env"
ALLOWED_COMMANDS = frozenset({"account", "portfolios", "portfolio", "orders"})

_VENV_PYTHON = SKILL_DIR / ".venv" / (
    "Scripts" if os.name == "nt" else "bin"
) / ("python.exe" if os.name == "nt" else "python")
_RUNNING_IN_VENV_ENV = "PI_COINBASE_IN_VENV"


def _force_utf8_stdio() -> None:
    """Make stdout/stderr UTF-8 on every platform (Windows consoles default to
    a legacy code page, which crashes on non-ASCII output)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):  # non-reconfigurable stream
            pass


def _venv_site_packages() -> Path:
    """site-packages of the skill venv, for entry points we cannot re-exec."""
    if os.name == "nt":
        return SKILL_DIR / ".venv" / "Lib" / "site-packages"
    return (
        SKILL_DIR / ".venv" / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    )


def _ensure_skill_venv() -> None:
    """Re-exec under the uv-managed skill venv declared in ``pyproject.toml``.

    ``uv sync`` installs python-dotenv into ``<skill>/.venv``. Calling the script
    with any other interpreter would miss it, so transparently re-run under that
    venv when needed. The tool stays usable on macOS/Windows as long as the
    developer runs ``uv sync`` once per machine.
    """
    if os.environ.get(_RUNNING_IN_VENV_ENV) == "1" or not _VENV_PYTHON.is_file():
        return
    if os.path.realpath(sys.executable) == os.path.realpath(str(_VENV_PYTHON)):
        return
    # subprocess (not os.execv) so stdout/stderr stay attached: on Windows
    # execv exits the parent before the child writes, losing piped output.
    # Only re-exec when sys.argv[0] is a real script we can replay; for piped
    # stdin (`python3 - < script`) or `-c` use the venv's packages in-process,
    # since replaying an exhausted stdin would silently run nothing.
    entry = sys.argv[0] if sys.argv else ""
    if entry and entry != "-" and Path(entry).is_file():
        os.environ[_RUNNING_IN_VENV_ENV] = "1"
        raise SystemExit(
            subprocess.run([str(_VENV_PYTHON), *sys.argv], env=os.environ).returncode
        )

    site_packages = _venv_site_packages()
    if site_packages.is_dir() and str(site_packages) not in sys.path:
        sys.path.insert(0, str(site_packages))


_force_utf8_stdio()
_ensure_skill_venv()

from dotenv import load_dotenv  # noqa: E402


def _fail(message: str) -> int:
    print(f"Error: {message}", file=sys.stderr)
    return 1


def _public_ipv4() -> str:
    request = urllib.request.Request(
        "https://api.ipify.org", headers={"User-Agent": "coinbase-readonly-vpn-check/1.0"}
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        value = response.read(64).decode("ascii").strip()
    address = ipaddress.ip_address(value)
    if address.version != 4:
        raise ValueError("public endpoint did not return IPv4")
    return address.compressed


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ALLOWED_COMMANDS:
        return _fail("only account, portfolios, portfolio, and orders are permitted")
    if not ENV_PATH.is_file():
        return _fail("local Coinbase credential configuration is missing")
    if not REPOSITORY.is_dir():
        return _fail("the local XRP Strategy integration is unavailable")

    load_dotenv(dotenv_path=ENV_PATH, override=True)
    allowed_value = os.environ.get("COINBASE_ALLOWED_IP", "").strip()
    try:
        allowed_network = ipaddress.ip_network(allowed_value, strict=False)
        if allowed_network.version != 4:
            raise ValueError("configured network is not IPv4")
        active_address = ipaddress.ip_address(_public_ipv4())
    except Exception:
        return _fail("VPN allowlist configuration or public IPv4 check failed")

    if active_address not in allowed_network:
        return _fail("active public IP does not match the configured VPN allowlist")

    sys.path.insert(0, str(REPOSITORY / "src"))
    os.chdir(REPOSITORY)
    from xrp_strategy.cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
