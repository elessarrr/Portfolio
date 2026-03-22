import hashlib
import io
import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from flask import current_app

from app import cache
from app.services.deepseek import DeepSeekService
from app.services.gemini import GeminiService


class BaseAnalyzerAdapter:
    model_name = "base"

    def generate(self, prompt):
        raise NotImplementedError


class GeminiAnalyzerAdapter(BaseAnalyzerAdapter):
    model_name = "gemini"

    def __init__(self):
        self.service = GeminiService()

    def generate(self, prompt):
        return self.service.generate_content(prompt)


class DeepSeekAnalyzerAdapter(BaseAnalyzerAdapter):
    model_name = "deepseek"

    def __init__(self):
        self.service = DeepSeekService()

    def generate(self, prompt):
        if not self.service.enabled:
            return "AI summary unavailable (DeepSeek API key missing)."
        response = self.service.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Extract structured aviation safety findings in JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.2,
            stream=False
        )
        return response.choices[0].message.content.strip()


class MockAnalyzerAdapter(BaseAnalyzerAdapter):
    model_name = "mock"

    def generate(self, prompt):
        return json.dumps({
            "root_cause": "Unavailable",
            "contributing_factors": [],
            "summary": "AI analysis unavailable for this environment."
        })


class ReportAnalyzerService:
    def __init__(self, model_name=None):
        selected_model = model_name or os.environ.get("REPORT_ANALYZER_MODEL", "gemini")
        self.adapters = {
            "gemini": GeminiAnalyzerAdapter,
            "deepseek": DeepSeekAnalyzerAdapter
        }
        adapter_class = self.adapters.get(selected_model, MockAnalyzerAdapter)
        self.adapter = adapter_class()
        self.rate_limit_per_hour = int(os.environ.get("REPORT_ANALYZER_RATE_LIMIT_PER_HOUR", "10"))
        self.cache_timeout_seconds = int(os.environ.get("REPORT_ANALYZER_CACHE_SECONDS", "86400"))

    def analyze_report(self, client_id, report_text=None, report_url=None):
        allowed, remaining = self._consume_rate_limit(client_id)
        if not allowed:
            return {
                "error": "Rate limit exceeded",
                "details": "Maximum analysis requests per hour reached.",
                "remaining": 0
            }, 429

        extracted_text = report_text
        if not extracted_text and report_url:
            extracted_text = self._extract_report_text(report_url)

        if not extracted_text:
            return {
                "error": "Missing report content",
                "details": "Provide report_text or a supported report_url."
            }, 400

        cache_key = self._build_cache_key(report_url, extracted_text)
        cached = cache.get(cache_key)
        if cached:
            cached["cached"] = True
            cached["remaining"] = remaining
            return cached, 200

        prompt = self._build_prompt(extracted_text)
        raw_output = self.adapter.generate(prompt)
        parsed = self._parse_analysis(raw_output)
        parsed["ai_model"] = getattr(self.adapter, "model_name", "unknown")
        parsed["cached"] = False
        parsed["remaining"] = remaining
        cache.set(cache_key, parsed, timeout=self.cache_timeout_seconds)
        return parsed, 200

    def _consume_rate_limit(self, client_id):
        hour_bucket = datetime.utcnow().strftime("%Y%m%d%H")
        key = f"report-rate:{client_id}:{hour_bucket}"
        current = cache.get(key) or 0
        if current >= self.rate_limit_per_hour:
            return False, 0
        updated = current + 1
        cache.set(key, updated, timeout=3600)
        return True, max(self.rate_limit_per_hour - updated, 0)

    def _build_cache_key(self, report_url, report_text):
        payload = json.dumps({
            "url": report_url or "",
            "text_hash": hashlib.sha256((report_text or "").encode("utf-8")).hexdigest(),
            "model": self.adapter.model_name
        }, sort_keys=True)
        return f"report-analysis:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"

    def _extract_report_text(self, report_url):
        parsed = urlparse(report_url)
        if parsed.scheme not in {"http", "https"}:
            return None
        host = (parsed.hostname or "").lower()
        if host in {"localhost", "127.0.0.1", "0.0.0.0"}:
            return None

        try:
            with httpx.Client(follow_redirects=True, timeout=30.0) as client:
                response = client.get(report_url)
                response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "application/pdf" in content_type or report_url.lower().endswith(".pdf"):
                return self._extract_pdf_text(response.content)
            if "text/html" in content_type:
                soup = BeautifulSoup(response.text, "html.parser")
                return soup.get_text(" ", strip=True)[:25000]
            return response.text[:25000]
        except Exception:
            current_app.logger.exception("Failed to fetch or parse report URL")
            return None

    def _extract_pdf_text(self, content):
        try:
            import PyPDF2
        except Exception:
            return None
        try:
            pdf_file = io.BytesIO(content)
            reader = PyPDF2.PdfReader(pdf_file)
            text = " ".join((page.extract_text() or "") for page in reader.pages)
            return text[:25000]
        except Exception:
            current_app.logger.exception("Failed to extract PDF text")
            return None

    def _build_prompt(self, report_text):
        trimmed = report_text[:20000]
        return (
            "You are an aviation safety analyst. Extract structured findings from the report text.\n"
            "Return valid JSON only with keys:\n"
            "root_cause (string), contributing_factors (array of strings), summary (string).\n"
            "Do not include markdown. Do not include extra keys.\n\n"
            f"Report text:\n{trimmed}"
        )

    def _parse_analysis(self, raw_output):
        if not raw_output:
            return {
                "root_cause": "Unavailable",
                "contributing_factors": [],
                "summary": "No analysis output was produced."
            }
        try:
            data = json.loads(raw_output)
            return {
                "root_cause": data.get("root_cause") or "Unavailable",
                "contributing_factors": data.get("contributing_factors") or [],
                "summary": data.get("summary") or ""
            }
        except Exception:
            match = re.search(r"\{[\s\S]*\}", raw_output)
            if match:
                try:
                    data = json.loads(match.group(0))
                    return {
                        "root_cause": data.get("root_cause") or "Unavailable",
                        "contributing_factors": data.get("contributing_factors") or [],
                        "summary": data.get("summary") or ""
                    }
                except Exception:
                    pass
            return {
                "root_cause": "Unavailable",
                "contributing_factors": [],
                "summary": raw_output[:2000]
            }
