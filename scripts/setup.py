"""
JARVIS Setup Script — First-time project setup.
"""

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    print("Setting up JARVIS...\n")

    # 1. Create .env from template
    env_file = PROJECT_ROOT / ".env"
    env_example = PROJECT_ROOT / ".env.example"
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("[OK] Created .env from .env.example")
        print("     -> Edit .env with your API keys!")
    else:
        print("[SKIP] .env already exists")

    # 2. Create data directories
    data_dirs = [
        "data/conversations",
        "data/knowledge_base",
        "data/vector_store",
        "data/long_term_memory",
        "data/logs",
    ]
    for d in data_dirs:
        path = PROJECT_ROOT / d
        path.mkdir(parents=True, exist_ok=True)
    print("[OK] Data directories created")

    # 3. Install dependencies
    print("\nInstalling dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], cwd=PROJECT_ROOT)
    print("\n[OK] Dependencies installed")

    print("\n" + "=" * 50)
    print("  JARVIS setup complete!")
    print("  1. Edit .env with your API keys")
    print("  2. Run: python -m jarvis")
    print("=" * 50)


if __name__ == "__main__":
    main()
