import os
import time
import logging

logger = logging.getLogger(__name__)

# Try to import google-generativeai
try:
    import google.generativeai as google_genai
    # Check if we have the modern API
    if hasattr(google_genai, 'GenerativeModel'):
        HAS_GEMINI = True
        logger.info(f"Gemini library loaded successfully. Version: {getattr(google_genai, '__version__', 'unknown')}")
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
    else:
        logger.warning("Old version of google-generativeai installed. AI features disabled.")
        HAS_GEMINI = False
except ImportError:
    logger.warning("google-generativeai not installed. AI features disabled.")
    HAS_GEMINI = False

class GeminiService:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('GOOGLE_GEMINI_API_KEY')
        
        # Debug logging for API Key
        if self.api_key:
            logger.info(f"GeminiService initialized with API Key: {self.api_key[:5]}... (Length: {len(self.api_key)})")
        else:
            logger.error("GeminiService initialized WITHOUT API Key.")

        self.enabled = False
        self.model = None

        if not self.api_key:
            logger.warning("GOOGLE_GEMINI_API_KEY not set. Using mock AI service.")
            return

        if not HAS_GEMINI:
            logger.warning("Gemini library unavailable. Using mock AI service.")
            return

        try:
            google_genai.configure(api_key=self.api_key)
            # Use the latest stable flash model
            self.model = google_genai.GenerativeModel('gemini-flash-latest')
            
            # Safety settings to allow more content (as aviation incidents might be flagged)
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }
            self.enabled = True
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")

    def generate_aircraft_summary(self, aircraft_data):
        """
        Generates a summary for an aircraft model using Gemini.
        """
        prompt = f"""
        Provide a concise, factual summary of the safety record and history of the {aircraft_data['manufacturer']} {aircraft_data['model_name']}.
        
        Key Data:
        - Years in service: {aircraft_data['years_in_service']}
        - Total incidents: {aircraft_data['total_incidents']}
        - Fatal incidents: {aircraft_data['fatal_incidents']}
        - Total fatalities: {aircraft_data['total_fatalities']}
        
        Focus on:
        1. Brief history of the aircraft
        2. Safety reputation
        3. Notable technical issues or improvements over time
        4. Context for the accident statistics (e.g. is it a widely used plane?)
        
        Keep it under 200 words. Do not include markdown formatting like **bold** or headers. Just plain text.
        """
        return self.generate_content(prompt)

    def generate_content(self, prompt, retry_count=3):
        """
        Generates content using Gemini API with retry logic and rate limiting.
        """
        if not self.enabled:
            return "AI summary unavailable (Mock Mode: API key missing or library error)."

        for attempt in range(retry_count):
            try:
                response = self.model.generate_content(
                    prompt, 
                    safety_settings=self.safety_settings
                )
                return response.text
            except Exception as e:
                logger.error(f"Gemini API error (attempt {attempt+1}/{retry_count}): {str(e)}")
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    # Rate limit hit, wait and retry
                    wait_time = (2 ** attempt) + 1
                    time.sleep(wait_time)
                else:
                    # Other errors might not be recoverable
                    if attempt == retry_count - 1:
                        return f"Error generating summary: {str(e)}"
