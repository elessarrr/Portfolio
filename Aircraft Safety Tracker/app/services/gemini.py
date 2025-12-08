import os
import time
import logging

logger = logging.getLogger(__name__)

# Try to import google-generativeai
try:
    import google.generativeai as genai
    # Check if we have the modern API
    if hasattr(genai, 'GenerativeModel'):
        HAS_GEMINI = True
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
        self.enabled = False
        self.model = None

        if not self.api_key:
            logger.warning("GOOGLE_GEMINI_API_KEY not set. Using mock AI service.")
            return

        if not HAS_GEMINI:
            logger.warning("Gemini library unavailable. Using mock AI service.")
            return

        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            
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
                    time.sleep(1)
        
        return "Failed to generate summary after multiple attempts."

    def generate_aircraft_summary(self, aircraft_data):
        """
        Generates a summary for an aircraft based on its data.
        
        Args:
            aircraft_data (dict): Dictionary containing:
                - manufacturer
                - model_name
                - years_in_service
                - total_incidents
                - fatal_incidents
                - total_fatalities
                - notable_incidents (list of dicts, optional)
        """
        prompt = f"""
        Please provide a concise, objective safety summary (3-5 sentences) for the {aircraft_data.get('manufacturer')} {aircraft_data.get('model_name')}.
        
        Key Data:
        - Years in Service: {aircraft_data.get('years_in_service')}
        - Total Recorded Incidents: {aircraft_data.get('total_incidents')}
        - Fatal Incidents: {aircraft_data.get('fatal_incidents')}
        - Total Fatalities: {aircraft_data.get('total_fatalities')}
        
        Context to include if relevant:
        - Overall safety reputation.
        - Any major groundings or design issues (e.g. 737 MAX MCAS, DC-10 cargo door).
        - Current operational status (widely used, retired, etc.).
        
        Tone: Professional, factual, and balanced. Avoid sensationalism.
        """
        return self.generate_content(prompt)
