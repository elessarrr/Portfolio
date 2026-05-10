import json
import random
from datetime import datetime, timedelta

with open('data/raw/boeing_incidents.json', 'r') as f:
    existing_data = json.load(f)

missing_models = [
    'Boeing 737-800', 'Boeing 747-400', 'Boeing 757-200', 
    'Boeing 767-300', 'Boeing 777-300ER', 'Boeing 787-9 Dreamliner'
]

for model in missing_models:
    for i in range(10):
        date = datetime(2000 + random.randint(0, 24), random.randint(1, 12), random.randint(1, 28))
        existing_data.append({
            'date': date.strftime('%d %b %Y'),
            'type': model,
            'operator': 'Synthetic Airlines',
            'fatalities': str(random.choice([0, 0, 0, 0, 10, 50])),
            'location': 'Synthetic City, Country',
            'category': 'A1',
            'narrative': f'This is a synthetic incident generated for testing the {model}.',
            'asn_url': f'https://aviation-safety.net/synthetic/{model.replace(" ", "_")}/{i}',
            'model_name': model,
            'is_synthetic': True
        })

with open('data/raw/boeing_incidents.json', 'w') as f:
    json.dump(existing_data, f, indent=2)

print('Synthetic data added successfully.')