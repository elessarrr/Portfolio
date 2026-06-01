## Relevant Files

- `Planning/tasks/0005-prd-security-trust-boundary-fixes.md` - Security PRD and acceptance criteria.
- `app/static/js/main.js` - Frontend rendering of AI analysis output; must avoid XSS.
- `app/services/report_analyzer.py` - URL fetching (SSRF) and rate limiting; must enforce trust boundaries.
- `app/routes.py` - `/api/analyze-report` endpoint; ties request handling to analyzer service.
- `tests/test_security.py` - Security regression tests for SSRF and rate limiting.

### Notes

- Complete one sub-task at a time.
- After each sub-task, mark it `[x]` and pause for approval before proceeding.

## Tasks

- [ ] 1.0 Frontend XSS mitigation
  - [x] 1.1 Render AI analysis output using DOM nodes (`textContent`), not `innerHTML`.
  - [x] 1.2 Add a regression test preventing reintroduction of `innerHTML` for analysis output.
- [ ] 2.0 Backend SSRF mitigation
  - [x] 2.1 Resolve hostnames and block private/loopback/link-local/multicast/reserved IPs.
  - [x] 2.2 Validate redirects at every hop; block unsafe redirect targets.
  - [x] 2.3 Add SSRF unit tests for blocked IP ranges and invalid schemes.
- [ ] 3.0 Atomic rate limiting
  - [x] 3.1 Implement atomic increment with backend-compatible fallback.
  - [x] 3.2 Add rate-limiter tests ensuring the limit cannot be bypassed.
- [ ] 4.0 Security regression coverage
  - [x] 4.1 Run full test suite and ensure all security tests pass.
  - [x] 4.2 Add any additional regression tests discovered during implementation.

- [x] 1.0 Frontend XSS mitigation
- [x] 2.0 Backend SSRF mitigation
- [x] 3.0 Atomic rate limiting
- [x] 4.0 Security regression coverage
