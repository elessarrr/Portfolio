import os

class Config:
    pass

class ProductionConfig(Config):
    DEBUG = False
    
    @property
    def SECRET_KEY(self):
        key = os.environ.get('SECRET_KEY')
        if not key:
            raise ValueError("No SECRET_KEY set for Flask application. This is required in production.")
        return key

print(getattr(ProductionConfig, 'SECRET_KEY'))
