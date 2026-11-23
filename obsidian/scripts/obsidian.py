#!/usr/bin/env python3
"""Small, dependency-free client for a local Obsidian HTTP MCP server."""

import argparse
import json
import os
from pathlib import Path
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parent.parent


class ClientError(Exception):
    pass


def load_config():
    config = {}
    env_file = ROOT / '.env'
    if env_file.exists():
        if env_file.stat().st_mode & 0o077:
            raise ClientError('Restrict .env permissions with chmod 600 before using the client.')
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('export '):
                line = line[7:]
            if '=' not in line:
                raise ClientError('Invalid .env entry. Use NAME=value without shell expressions.')
            name, value = line.split('=', 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            config[name.strip()] = value
    for name in ('OBSIDIAN_API_KEY', 'OBSIDIAN_MCP_URL', 'OBSIDIAN_CA_CERT',
                 'OBSIDIAN_ALLOW_INSECURE_LOCAL_TLS'):
        if name in os.environ:
            config[name] = os.environ[name]
    if not config.get('OBSIDIAN_API_KEY'):
        raise ClientError('OBSIDIAN_API_KEY is missing. Enter it locally in the skill .env file.')
    return config


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ClientError('HTTP redirects are blocked to protect credentials.')


class Client:
    def __init__(self, config):
        self.key = config['OBSIDIAN_API_KEY']
        self.url = config.get('OBSIDIAN_MCP_URL') or 'https://127.0.0.1:27124/mcp/'
        parsed = urllib.parse.urlsplit(self.url)
        if (parsed.scheme != 'https' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ClientError('Use an HTTPS loopback URL without credentials, query, or fragment.')
        ca = config.get('OBSIDIAN_CA_CERT')
        try:
            context = ssl.create_default_context(cafile=str(Path(ca).expanduser()) if ca else None)
        except (OSError, ssl.SSLError):
            raise ClientError('Cannot load the configured CA certificate.') from None
        insecure = config.get('OBSIDIAN_ALLOW_INSECURE_LOCAL_TLS', '').lower() == 'true'
        if insecure:
            context = ssl._create_unverified_context()
            print('Warning: TLS certificate verification is disabled for this local client.', file=sys.stderr)
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPSHandler(context=context))
        self.session = None
        self.protocol = None
        self.counter = 0

    def safe(self, text):
        for secret in (self.key, self.session):
            if secret:
                text = text.replace(secret, '[REDACTED]')
        text = re.sub(r'(?i)Bearer\s+[^\s"\']+', 'Bearer [REDACTED]', text)
        text = re.sub(
            r'(?i)(["\']?(?:api[_-]?key|password|secret|access[_-]?token|refresh[_-]?token|authorization)["\']?\s*[:=]\s*)("[^"\n]*"|\'[^\'\n]*\'|[^\s,}\n]+)',
            r'\1"[REDACTED]"', text)
        return text

    def request(self, method, params=None, notification=False):
        self.counter += 1
        payload = {'jsonrpc': '2.0', 'method': method}
        if not notification:
            payload['id'] = self.counter
        if params is not None:
            payload['params'] = params
        headers = {'Authorization': 'Bearer ' + self.key,
                   'Content-Type': 'application/json',
                   'Accept': 'application/json, text/event-stream'}
        if self.session:
            headers['Mcp-Session-Id'] = self.session
        if self.protocol:
            headers['MCP-Protocol-Version'] = self.protocol
        req = urllib.request.Request(self.url, json.dumps(payload).encode(), headers, method='POST')
        try:
            with self.opener.open(req, timeout=30) as response:
                if response.headers.get('Mcp-Session-Id'):
                    self.session = response.headers['Mcp-Session-Id']
                if notification or response.status == 202:
                    return None
                if 'text/event-stream' in response.headers.get('Content-Type', ''):
                    data = []
                    size = 0
                    for raw_line in response:
                        size += len(raw_line)
                        if size > 8 * 1024 * 1024:
                            raise ClientError('MCP event stream exceeds the 8 MiB limit.')
                        line = raw_line.decode('utf-8').rstrip('\r\n')
                        if not line:
                            if data:
                                message = json.loads('\n'.join(data))
                                data = []
                                if message.get('id') == payload['id']:
                                    return self.result(message)
                        elif line.startswith('data:'):
                            data.append(line[5:].lstrip(' '))
                    raise ClientError('MCP event stream ended without a matching response.')
                body = response.read(8 * 1024 * 1024 + 1)
                if len(body) > 8 * 1024 * 1024:
                    raise ClientError('MCP response exceeds the 8 MiB limit.')
                message = json.loads(body)
                if message.get('id') != payload['id']:
                    raise ClientError('MCP response ID does not match the request.')
                return self.result(message)
        except urllib.error.HTTPError as exc:
            explanations = {401: 'Authentication failed.', 403: 'Access denied.',
                            404: 'MCP endpoint not found.', 405: 'Endpoint does not accept MCP POST requests.'}
            raise ClientError(f'HTTP {exc.code}: ' + explanations.get(exc.code, 'MCP request failed.')) from None
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, ssl.SSLCertVerificationError):
                raise ClientError('TLS verification failed. Configure OBSIDIAN_CA_CERT with a trusted PEM certificate.') from None
            raise ClientError('Connection failed. Check that Obsidian and its MCP plugin are running on this machine.') from None
        except (TimeoutError, OSError):
            raise ClientError('Connection interrupted or timed out. Check state before retrying a write.') from None
        except (ValueError, UnicodeError, AttributeError, TypeError):
            raise ClientError('Server returned an invalid MCP response.') from None

    @staticmethod
    def result(message):
        if 'error' in message:
            # Do not print arbitrary server errors, which can contain credentials.
            raise ClientError('Server returned an MCP error. Check plugin configuration and tool arguments.')
        if 'result' not in message:
            raise ClientError('MCP response has no result.')
        return message['result']

    def initialize(self):
        result = self.request('initialize', {
            'protocolVersion': '2024-11-05', 'capabilities': {},
            'clientInfo': {'name': 'obsidian-skill', 'version': '0.1.0'}})
        self.protocol = result.get('protocolVersion')
        self.request('notifications/initialized', notification=True)

    def tools(self):
        tools = []
        cursor = None
        seen = set()
        while True:
            result = self.request('tools/list', {'cursor': cursor} if cursor else {})
            tools.extend(result.get('tools', []))
            cursor = result.get('nextCursor')
            if not cursor:
                return tools
            if cursor in seen:
                raise ClientError('Server returned a repeated pagination cursor.')
            seen.add(cursor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('tools', help='Authenticate and list available tools without changing notes')
    call = sub.add_parser('call', help='Call a discovered MCP tool')
    call.add_argument('tool')
    call.add_argument('--args', default='{}', help='JSON object; never include credentials')
    call.add_argument('--confirm-write', action='store_true',
                      help='Use only after explicit user approval for this specific change')
    args = parser.parse_args()
    client = None
    try:
        config = load_config()
        client = Client(config)
        client.initialize()
        tools = client.tools()
        if args.command == 'tools':
            output = {'tools': tools}
        else:
            tool = next((tool for tool in tools if tool.get('name') == args.tool), None)
            if tool is None:
                raise ClientError('Unknown tool. List tools first.')
            hints = tool.get('annotations') or {}
            read_only = hints.get('readOnlyHint') is True and hints.get('destructiveHint') is not True
            if not read_only and not args.confirm_write:
                raise ClientError('Tool is not declared read-only. Explicit user approval and --confirm-write are required.')
            try:
                arguments = json.loads(args.args)
            except ValueError:
                raise ClientError('--args must be a valid JSON object.') from None
            if not isinstance(arguments, dict):
                raise ClientError('--args must be a JSON object.')
            output = client.request('tools/call', {'name': args.tool, 'arguments': arguments})
        print(client.safe(json.dumps(output, indent=2, ensure_ascii=False)))
        return 1 if isinstance(output, dict) and output.get('isError') else 0
    except ClientError as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Interrupted. Check state before retrying a write.', file=sys.stderr)
        return 130
    except Exception:
        print('Error: Unexpected client failure; details suppressed to protect credentials.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
