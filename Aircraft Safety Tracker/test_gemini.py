import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get('GOOGLE_GEMINI_API_KEY')
genai.configure(api_key=api_key)

model_name = 'gemini-flash-latest'
print(f"Testing model: {model_name}...")

try:
    start = time.time()
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("Say hello.")
    duration = time.time() - start
    print(f"Success! Response: {response.text}")
    print(f"Duration: {duration:.2f}s")
except Exception as e:
    print(f"Error: {e}")
