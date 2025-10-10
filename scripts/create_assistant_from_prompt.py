"""Create an OpenAI Assistant from assistant_prompt.md and store it in the database.

This script is runnable directly and will:
- add the project root to sys.path so `import app` works
- load .env file variables into os.environ if they are not already set
- call OpenAI to create an assistant and persist it in the DB

Usage: run inside project venv:
    .\venv\Scripts\Activate.ps1
    python scripts\create_assistant_from_prompt.py
"""

import os
import sys

# ensure project root is on sys.path so `import app` works
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# load .env file into environment (if keys not already set)
ENV_PATH = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(ENV_PATH):
    try:
        with open(ENV_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"')
                # don't overwrite existing env vars
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        print('Warning: failed to load .env file')

from app import create_app
from app.database.models import db, Assistant
from app.services.openai_service import create_assistant

APP_DIR = PROJECT_ROOT

def main():
    # prometheus exporter in extensions expects PROMETHEUS_MULTIPROC_DIR to be set; set a temp dir to avoid errors
    import tempfile
    if not os.environ.get('PROMETHEUS_MULTIPROC_DIR') and not os.environ.get('prometheus_multiproc_dir'):
        tmpd = tempfile.mkdtemp(prefix='prom_multiproc_')
        os.environ['PROMETHEUS_MULTIPROC_DIR'] = tmpd
    app = create_app()
    with app.app_context():
        prompt_path = os.path.join(app.root_path, 'config', 'assistant_prompt.md')
        if not os.path.exists(prompt_path):
            print('assistant_prompt.md not found at', prompt_path)
            return
        with open(prompt_path, 'r', encoding='utf-8') as f:
            instructions = f.read()
        name = 'MyWave Assistant'
        # sanitize model: some envs mistakenly store API keys in GPTS_MODEL; avoid passing that as model
        raw_model = (app.config.get('GPTS_MODEL') or '').strip()
        if raw_model and not raw_model.startswith('sk-') and len(raw_model) < 50:
            model = raw_model
        else:
            # fallback to a safe default
            model = 'gpt-4'
        print('Using model:', model)
        try:
            assistant = create_assistant(name=name, instructions=instructions, model=model)
            # Save to DB
            db_assistant = Assistant(
                assistant_id=assistant.id,
                name=assistant.name,
                instructions=assistant.instructions,
                model=assistant.model
            )
            db.session.add(db_assistant)
            db.session.commit()
            print('Assistant created with id:', assistant.id)
        except Exception as e:
            print('Failed to create assistant:', e)

if __name__ == '__main__':
    main()
