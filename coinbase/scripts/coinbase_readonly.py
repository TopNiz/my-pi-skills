"""Run only allowlisted read-only Coinbase operations after a VPN egress check."""

from __future__ import annotations

import ipaddress
import os
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


SKILL_DIR = Path(__file__).resolve().parents[1]
REPOSITORY = Path("/Users/nizarayed/MyDocuments/002-git/xrp-strategy")
ENV_PATH = SKILL_DIR / ".env"
ALLOWED_COMMANDS = frozenset({"account", "portfolios", "portfolio", "orders"})


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
