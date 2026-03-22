# Code Review and Fixes - 22 Mar

## Findings
While the new background processing for AI summaries and the expanded database models are good additions, there are a few critical issues and failing tests that need to be addressed before this is "good to go".

1. **Critical Configuration Bug:** In `config.py`, `SECRET_KEY` is defined as a `@property` on the `ProductionConfig` class. Flask's config loader reads the class attribute directly (which will be the property object itself, not the evaluated string). This will completely break sessions and CSRF protection in production.
2. **Failing Tests (Mismatched Services):** The codebase was updated to use `DeepSeekService` with background threading for summary generation, but `tests/test_summary.py` is still trying to mock the old `GeminiService` synchronously, causing tests to error out. 
3. **Failing Tests (Mocking Errors):** `tests/test_gemini.py` tries to mock `app.services.gemini.genai`, but it is imported as `google_genai` internally, causing an `AttributeError`.
4. **Incomplete Test Assertion:** In `tests/test_routes.py`, an assertion for the search endpoint was deleted and replaced with a comment, leaving the test without proper validation for 1-character queries.

## Plan to Fix / Recommendations

### 1. Fix `config.py` (Multiple Options)
* **Option 1 (Simplest & Recommended):** Remove the `@property` and evaluate `os.environ.get('SECRET_KEY')` directly at the class level. If it's missing, we raise a `ValueError` right there so the app fails immediately at startup rather than during a user request.
* **Option 2:** Just remove the `@property` and let it evaluate to `None`. Flask will eventually throw a runtime error only when a session is accessed.

### 2. Update `tests/test_summary.py`
Update the mocks to patch `DeepSeekService` and `threading.Thread` to properly test the new asynchronous background generation and the updated "Summary generation started" flash messages.

### 3. Update `tests/test_gemini.py`
Fix the mock target from `genai` to `google_genai` so the tests pass.

### 4. Update `tests/test_routes.py`
Add the missing assertion to verify that searching for "B" returns the correct HTML payload (or empty results if no match) instead of just checking the status code.
