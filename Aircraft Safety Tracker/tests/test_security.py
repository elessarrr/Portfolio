import os

import pytest
from app.services.report_analyzer import ReportAnalyzerService

def test_ssrf_protection(app):
    """Test that the SSRF protection blocks private, local, and reserved IPs."""
    with app.app_context():
        service = ReportAnalyzerService(model_name="mock")
        
        # Test basic loopback
        assert service._extract_report_text("http://localhost/secret") is None
        assert service._extract_report_text("http://127.0.0.1/admin") is None
        
        # Test AWS metadata IP
        assert service._extract_report_text("http://169.254.169.254/latest/meta-data/") is None
        
        # Test internal network IPs
        assert service._extract_report_text("http://10.0.0.5/api") is None
        assert service._extract_report_text("http://192.168.1.100/admin") is None
        
        # Test invalid scheme
        assert service._extract_report_text("ftp://example.com") is None
        assert service._extract_report_text("file:///etc/passwd") is None


def test_ssrf_blocks_hostname_resolving_to_private_ip(app, monkeypatch):
    with app.app_context():
        service = ReportAnalyzerService(model_name="mock")

        def fake_getaddrinfo(_host, _port, *args, **kwargs):
            return [(
                0,
                0,
                0,
                "",
                ("10.0.0.5", 0),
            )]

        import socket

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        assert service._extract_report_text("http://example.com/report") is None


def test_ssrf_blocks_unsafe_redirect_target(app, monkeypatch):
    with app.app_context():
        service = ReportAnalyzerService(model_name="mock")

        def fake_getaddrinfo(_host, _port, *args, **kwargs):
            return [(
                0,
                0,
                0,
                "",
                ("93.184.216.34", 0),
            )]

        import socket

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        class FakeResponse:
            def __init__(self, status_code, headers=None, text="", content=b""):
                self.status_code = status_code
                self.headers = headers or {}
                self.text = text
                self.content = content

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise RuntimeError("http error")

        class FakeClient:
            def __init__(self, *args, **kwargs):
                self.calls = []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def get(self, url):
                self.calls.append(url)
                if url == "http://example.com/report":
                    return FakeResponse(302, headers={"location": "http://127.0.0.1/internal"})
                return FakeResponse(200, headers={"content-type": "text/plain"}, text="ok")

        import httpx

        monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: FakeClient())
        assert service._extract_report_text("http://example.com/report") is None


def test_ssrf_blocks_excessive_redirects(app, monkeypatch):
    with app.app_context():
        service = ReportAnalyzerService(model_name="mock")
        monkeypatch.setenv("REPORT_ANALYZER_MAX_REDIRECTS", "1")

        def fake_getaddrinfo(_host, _port, *args, **kwargs):
            return [(
                0,
                0,
                0,
                "",
                ("93.184.216.34", 0),
            )]

        import socket

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        class FakeResponse:
            def __init__(self, status_code, headers=None):
                self.status_code = status_code
                self.headers = headers or {}
                self.text = ""
                self.content = b""

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise RuntimeError("http error")

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def get(self, url):
                return FakeResponse(302, headers={"location": "/loop"})

        import httpx

        monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: FakeClient())
        assert service._extract_report_text("http://example.com/report") is None


def test_ssrf_allows_safe_http_url_and_trims_text(app, monkeypatch):
    with app.app_context():
        service = ReportAnalyzerService(model_name="mock")

        def fake_getaddrinfo(_host, _port, *args, **kwargs):
            return [(
                0,
                0,
                0,
                "",
                ("93.184.216.34", 0),
            )]

        import socket

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        class FakeResponse:
            def __init__(self, text):
                self.status_code = 200
                self.headers = {"content-type": "text/plain"}
                self.text = text
                self.content = text.encode("utf-8")

            def raise_for_status(self):
                return None

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def get(self, url):
                return FakeResponse("x" * 30000)

        import httpx

        monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: FakeClient())
        text = service._extract_report_text("http://example.com/report")
        assert text is not None
        assert len(text) == 25000

def test_rate_limiter_concurrency(app):
    """Test that the rate limiter accurately limits requests."""
    with app.app_context():
        service = ReportAnalyzerService(model_name="mock")
        
        # Set a low limit for testing
        service.rate_limit_per_hour = 3
        client_id = "test_security_client"
        
        # Consume allowed requests
        for _ in range(3):
            allowed, remaining = service._consume_rate_limit(client_id)
            assert allowed is True
            
        # 4th request should be blocked
        allowed, remaining = service._consume_rate_limit(client_id)
        assert allowed is False
        assert remaining == 0


def test_rate_limiter_uses_cache_inc_when_available(app, monkeypatch):
    with app.app_context():
        service = ReportAnalyzerService(model_name="mock")
        service.rate_limit_per_hour = 2

        import app.services.report_analyzer as report_analyzer

        class FakeCache:
            def __init__(self):
                self.data = {}

            def get(self, key):
                return self.data.get(key)

            def set(self, key, value, timeout=None):
                self.data[key] = value

            def inc(self, key):
                self.data[key] = int(self.data.get(key) or 0) + 1
                return self.data[key]

        fake_cache = FakeCache()
        monkeypatch.setattr(report_analyzer, "cache", fake_cache)

        allowed, remaining = service._consume_rate_limit("c")
        assert allowed is True
        allowed, remaining = service._consume_rate_limit("c")
        assert allowed is True
        allowed, remaining = service._consume_rate_limit("c")
        assert allowed is False


def test_rate_limiter_blocks_concurrent_spikes_with_atomic_inc(app, monkeypatch):
    with app.app_context():
        service = ReportAnalyzerService(model_name="mock")
        service.rate_limit_per_hour = 5

        import app.services.report_analyzer as report_analyzer
        import threading

        class ThreadSafeCache:
            def __init__(self):
                self.data = {}
                self.lock = threading.Lock()

            def get(self, key):
                with self.lock:
                    return self.data.get(key)

            def set(self, key, value, timeout=None):
                with self.lock:
                    self.data[key] = value

            def inc(self, key):
                with self.lock:
                    self.data[key] = int(self.data.get(key) or 0) + 1
                    return self.data[key]

        monkeypatch.setattr(report_analyzer, "cache", ThreadSafeCache())

        barrier = threading.Barrier(20)
        results = []
        results_lock = threading.Lock()

        def worker():
            barrier.wait()
            allowed, _ = service._consume_rate_limit("burst")
            with results_lock:
                results.append(allowed)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.count(True) == 5
        assert results.count(False) == 15


def test_frontend_does_not_use_innerhtml_for_analysis_output():
    path = os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'js', 'main.js')
    path = os.path.abspath(path)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert 'analysisOutput.innerHTML' not in content
