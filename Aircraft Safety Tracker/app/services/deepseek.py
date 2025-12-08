import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class DeepSeekService:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
        self.base_url = "https://api.deepseek.com"
        
        if self.api_key:
            logger.info(f"DeepSeekService initialized with API Key: {self.api_key[:5]}...")
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self.enabled = True
        else:
            logger.warning("DEEPSEEK_API_KEY not set. AI features disabled.")
            self.client = None
            self.enabled = False

    def generate_aircraft_summary(self, aircraft_data):
        """
        Generates a summary for an aircraft model using DeepSeek.
        """
        if not self.enabled:
            return "AI summary unavailable (API key missing)."

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
        
        try:
            logger.info(f"Sending request to DeepSeek API for {aircraft_data['model_name']}...")
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful aviation safety expert."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.7,
                stream=False
            )
            content = response.choices[0].message.content.strip()
            logger.info(f"DeepSeek response received. Length: {len(content)}")
            return content
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}", exc_info=True)
            return f"Error generating summary: {str(e)}"
