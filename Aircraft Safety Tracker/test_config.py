from flask import Flask
from config import ProductionConfig

app = Flask(__name__)
app.config.from_object(ProductionConfig)
print("Loaded SECRET_KEY:", app.config.get('SECRET_KEY'))
