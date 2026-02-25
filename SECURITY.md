# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.3.x   | Yes                |
| < 0.3   | No                 |

## Reporting Vulnerabilities

**Email**: security@metavolve.com

We take security seriously. If you discover a vulnerability, please report it
responsibly via email. Do not open a public GitHub issue for security problems.

**Response timeline**:
- Acknowledgment: 48 hours
- Assessment: 5 business days
- Fix (critical): 7 business days
- Fix (moderate): 30 business days

## Security Architecture

- **Authentication**: x402 EIP-712 signature verification, Stripe webhook validation, Bearer token auth
- **Secrets management**: All credentials stored in GCP Secret Manager, never in environment variables or code
- **Payment verification**: x402 payments verified on-chain via Base L2 RPC before tool execution
- **Data isolation**: Per-wallet Firestore documents with server-side-only security rules
- **Transport**: HTTPS-only (TLS 1.2+), CORS restricted to known origins
- **Infrastructure**: Google Cloud Run with automatic patching, IAM least-privilege service accounts

## Rate Limits

- Free tools: 100 requests/minute per IP
- Paid tools: Unlimited (rate limited by payment verification latency)
- MCP sessions: 50 concurrent per IP

## Responsible Disclosure

We follow coordinated disclosure. Reporters who follow responsible disclosure
practices will be credited (with permission) in release notes.
