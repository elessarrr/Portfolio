import os
from app import create_app, db
from app.models import Aircraft, Incident, Request

app = create_app(os.getenv('FLASK_CONFIG') or os.getenv('FLASK_ENV') or 'default')

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Aircraft': Aircraft, 'Incident': Incident, 'Request': Request}

if __name__ == '__main__':
    app.run()
