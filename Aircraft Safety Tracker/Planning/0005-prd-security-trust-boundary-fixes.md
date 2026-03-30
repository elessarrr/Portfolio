# Product Requirements Document (PRD)

## 1. Introduction/Overview
This PRD outlines the required security and trust boundary fixes for the Aircraft Safety Tracker. Recent codebase reviews identified vulnerabilities relating to Cross-Site Scripting (XSS), Server-Side Request Forgery (SSRF), and Rate Limiter concurrency. The goal is to safely resolve these issues with simple, robust, and verifiable solutions without adding unnecessary dependencies.

## 2. Goals
- Eliminate XSS risks when rendering AI-generated text in the frontend.
- Secure the backend URL fetcher against SSRF, protecting internal and reserved network IP addresses.
- Prevent rate limiting bypasses during concurrent request spikes.
- Establish baseline security tests to prevent future regressions.

## 3. User Stories
- As an administrator, I want the application to be secure from malicious actors who might attempt to inject malicious scripts through the AI summarization features.
- As a security-conscious user, I want the backend to reject fetching internal IP addresses to ensure the application isn't used as a proxy for malicious attacks.
- As a system operator, I want the rate limits to reliably prevent abuse, even when users spam the endpoint concurrently.

## 4. Functional Requirements
1. **Frontend XSS Mitigation (`main.js`):** The application must render AI analysis output using `textContent` instead of `innerHTML`. DOM nodes must be created manually to safely append structured data.
2. **Backend SSRF Mitigation (`report_analyzer.py`):** The system must resolve the IP address of any provided URL before initiating an HTTP request. It must explicitly block private, loopback, link-local, multicast, and reserved IPs. Redirects must be tracked and validated at every hop.
3. **Atomic Rate Limiting (`report_analyzer.py`):** The cache-based rate limiter must use atomic increment operations (`cache.inc()` or fallback mechanisms) to ensure concurrent requests properly increment the hit counter.
4. **Security Testing:** The system must include automated unit tests verifying the rejection of invalid SSRF URLs and the proper blocking of concurrent requests that exceed the rate limit.

## 5. Non-Goals (Out of Scope)
- Adding third-party HTML sanitization libraries (e.g., DOMPurify) is out of scope. We will rely purely on DOM text nodes.
- Migrating the rate limiter from cache to PostgreSQL is out of scope for this task.

## 6. Technical Considerations
- **SSRF Validation:** DNS rebinding attacks can occur if the IP changes between validation and fetching. A robust implementation will manually resolve the IP and ensure the HTTP client uses the validated IP, or it will manually follow redirects to validate each step.
- **Cache Compatibility:** The atomic `inc` method behaves differently depending on the Flask-Caching backend. A safe fallback must be implemented for environments using `SimpleCache`.

## 7. Success Metrics
- 100% of the security unit tests pass.
- No ability to inject arbitrary HTML tags via the report analyzer output.
- No successful requests made to `localhost`, `127.0.0.1`, or `169.254.169.254` via the `/api/analyze-report` endpoint.

## 8. Open Questions
- None at this time. All technical options have been clarified and selected by the product team.
