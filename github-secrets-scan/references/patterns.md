# 🔒 Secret Scanning Patterns

Each pattern is used by `scripts/scan.py` to detect sensitive data in code and commit history.

---

## Pattern Categories

### 🔑 Credentials (Severity: CRITICAL)

```yaml
- name: generic_password
  description: "Hardcoded password assignment"
  severity: critical
  contexts: [files, commits]
  regex: '(?i)(?:password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{4,}['\"]'
  false_positive:
    - skip_if_contains: ["example", "placeholder", "password_hash", "hashed_password"]
    - skip_if_file_ends: [".md", ".rst", ".txt"]
  example_match: 'password = "supersecret123"'
  example_false_positive: 'password_hash = hash_password("test")'
```

### 🔐 API Keys (Severity: CRITICAL)

```yaml
- name: aws_access_key
  description: "AWS Access Key ID"
  severity: critical
  contexts: [files, commits]
  regex: 'AKIA[0-9A-Z]{16}'
  false_positive:
    - skip_if_file_contains: ["example", "your_"]
  example_match: 'AKIAIOSFODNN7EXAMPLE'

- name: openai_api_key
  description: "OpenAI API Key (sk-...) in code"
  severity: critical
  contexts: [files, commits]
  regex: 'sk-[A-Za-z0-9]{20,}'
  false_positive:
    - skip_if_file_contains: ["example"]

- name: google_api_key
  description: "Google API Key"
  severity: critical
  contexts: [files, commits]
  regex: 'AIza[0-9A-Za-z\-_]{35}'
  false_positive:
    - skip_if_file_contains: ["example"]

- name: generic_api_key
  description: "Generic API key/secret assignment"
  severity: high
  contexts: [files, commits]
  regex: '(?i)(?:api[_-]?key|api[_-]?secret|apikey)\s*[=:]\s*['\"][^'\"]{8,}['\"]'
  false_positive:
    - skip_if_contains: ["example", "placeholder", "your_", "YOUR_"]

- name: generic_secret
  description: "Generic secret in code"
  severity: high
  contexts: [files, commits]
  regex: '(?i)(?:secret|secret_key|secret_token)\s*[=:]\s*['\"][^'\"]{8,}['\"]'
  false_positive:
    - skip_if_contains: ["example", "placeholder"]
```

### 🎫 Tokens (Severity: CRITICAL)

```yaml
- name: github_token
  description: "GitHub personal access token (ghp_/gho_/ghu_/ghs_/ghr_)"
  severity: critical
  contexts: [files, commits]
  regex: '(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}'
  false_positive:
    - skip_if_match_contains: ["xxxx", "XXXX"]

- name: github_fine_grained_pat
  description: "GitHub fine-grained PAT"
  severity: critical
  contexts: [files, commits]
  regex: 'github_pat_[A-Za-z0-9_]{22,}'
  false_positive:
    - skip_if_match_contains: ["xxxx", "XXXX", "xxxxxxxx"]

- name: slack_token
  description: "Slack Bot/API/Webhook token"
  severity: critical
  contexts: [files, commits]
  regex: 'xox[baprs]-[A-Za-z0-9-]{10,}'

- name: jwt_token
  description: "JSON Web Token (JWT) in code"
  severity: high
  contexts: [files, commits]
  regex: 'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'
  false_positive:
    - skip_if_file_contains: ["example"]
    - skip_if_contains: ["eyJleGFtcGxl"]

- name: bearer_token
  description: "Authorization Bearer token"
  severity: high
  contexts: [files, commits]
  regex: '(?i)(?:Bearer|bearer)\s+[A-Za-z0-9._\-+/]{20,}'
  false_positive:
    - skip_if_contains: ["example", "sample"]
```

### 🔏 Private Keys (Severity: CRITICAL)

```yaml
- name: private_key
  description: "Any PEM-encoded private key"
  severity: critical
  contexts: [files, commits]
  regex: '-----BEGIN[ A-Z]+PRIVATE KEY-----'
  false_positive:
    - skip_if_file_contains: ["example", "test_key", "TEST_PRIVATE"]

- name: pgp_private_key
  description: "PGP private key block"
  severity: critical
  contexts: [files, commits]
  regex: '-----BEGIN PGP PRIVATE KEY BLOCK-----'

- name: ssh_public_key
  description: "SSH public key embedded in code"
  severity: high
  contexts: [files, commits]
  regex: 'ssh-(rsa|ed25519|dss|ecdsa)\s+[A-Za-z0-9+/=]{50,}'
  false_positive:
    - skip_if_file_contains: ["# authorized_keys"]
```

### 🔌 Connection Strings (Severity: CRITICAL)

```yaml
- name: db_connection_string
  description: "Database URL with embedded credentials"
  severity: critical
  contexts: [files, commits]
  regex: '(postgresql|mysql|mongodb|redis|amqp|rabbitmq|rediss)://[^:]+:[^@]+@'
  false_positive:
    - skip_if_contains: ["example", "localhost", "USER", "password_field"]

- name: url_credentials
  description: "URL with embedded username:password"
  severity: high
  contexts: [files, commits]
  regex: 'https?://[^:/\s]+:[^@\s]+@'
  false_positive:
    - skip_if_contains: ["example.com"]
```

### 📧 Contact Info (Severity: MEDIUM to INFO)

```yaml
- name: email_address
  description: "Real email addresses in code or commits"
  severity: medium
  contexts: [files, commits]
  regex: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
  false_positive:
    - skip_if_domain: ["example.com", "domain.com", "test.com", "example.org", "acm.org"]
    - skip_if_contains: ["user@", "your@", "test@", "email@", "you@"]
    - skip_if_file_ends: [".jpg", ".png", ".gif", ".ico"]
    - skip_if_file_contains_npm_email: true
    # npm package.json maintainer emails are common false positives
    - skip_if_path_contains: ["/node_modules/", "/package.json"]
  notes: >
    Flags are categorized:
    - PERSONAL (your own emails in git commits) → INFO
    - APP_INTERNAL (emails like admin@app.com) → INFO
    - OTHER_PERSON (real third-party emails) → MEDIUM

- name: phone_tunisia
  description: "Tunisian phone numbers (+216)"
  severity: medium
  contexts: [files, commits]
  regex: '(?:(?:\+216|00216)[1-9][0-9]{7}|0[1-9][0-9]{7})'
  false_positive:
    - skip_if_contains: ["example", "0{8}", "12345678"]
  example_match: '+21650123456'
  example_false_positive: '0212345678'

- name: phone_france
  description: "French phone numbers (+33)"
  severity: medium
  contexts: [files, commits]
  regex: '(?:(?:\+33|0033)[1-9][0-9]{8}|0[1-9][0-9]{8})'
  false_positive:
    - skip_if_contains: ["example", "0{8,}", "12345678"]
```

### 🌐 Network / Infrastructure (Severity: MEDIUM to HIGH)

```yaml
- name: internal_ip
  description: "Private/internal IP addresses"
  severity: medium
  contexts: [files, commits]
  regex: '(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})'
  false_positive:
    - skip_if_contains: ["example", "x.x.x.x", "0.0.0.0"]

- name: localhost_url
  description: "Localhost URLs (possible internal services exposed)"
  severity: info
  contexts: [files, commits]
  regex: 'https?://localhost(:\d+)?[/\s]'
  false_positive:
    - skip_if_file_contains: ["development", "dev"]

- name: internal_hostname
  description: "Internal domain names (.local, .internal)"
  severity: medium
  contexts: [files, commits]
  regex: 'https?://[a-zA-Z0-9.-]+\.(local|internal|corp|lan)(?::\d+)?'
```

### 🔍 Other (Severity: varies)

```yaml
- name: aws_secret_key
  description: "AWS Secret Access Key"
  severity: critical
  contexts: [files, commits]
  regex: '(?i)aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*['\"][A-Za-z0-9/+=]{40}['\"]'
  false_positive:
    - skip_if_contains: ["example"]

- name: heroku_api_key
  description: "Heroku API Key"
  severity: critical
  contexts: [files, commits]
  regex: '(?i)heroku[_-]?api[_-]?key\s*[=:]\s*['\"][A-Za-z0-9-]{36}['\"]'

- name: mysql_config
  description: "MySQL configuration with password"
  severity: high
  contexts: [files, commits]
  regex: '(?i)\[client\]\s*\n\s*(?:user|password)\s*='
  false_positive:
    - skip_if_contains: ["example"]
```

---

## Adding Custom Patterns

Edit this file and add your pattern following the format:

```yaml
- name: my_custom_pattern
  description: "What it detects"
  severity: critical|high|medium|info
  contexts: [files, commits]   # or just one
  regex: 'your-regex-here'
  false_positive:
    - skip_if_contains: ["known_false_positive_string"]
    - skip_if_file_contains: ["indicator_of_test_data"]
```

The scanner reads this file at runtime and applies all patterns.

---

## Default Exclusions (always skipped)

The following are never scanned regardless of pattern:

| Criteria | Reason |
|----------|--------|
| Binary files (.png, .jpg, .pdf, .zip, etc.) | Can't read as text |
| node_modules/ | Third-party code, not yours |
| dist/, build/, .next/, .nuxt/ | Build artifacts |
| __pycache__/, .bundle/, vendor/ | Cached/third-party deps |
| *.lock files | Auto-generated dependency manifests |
| Files > 500KB | Too large for text scanning |
