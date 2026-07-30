import os
import time
from uuid import uuid4
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError


def load_env_file(path=".env"):
    """Tiny .env loader so we do not depend on python-dotenv."""
    if not os.path.exists(path):
        print(f".env not found at: {os.path.abspath(path)}")
        return

    print(f"Loading .env from: {os.path.abspath(path)}")

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            # overwrite current process values
            os.environ[key] = value


load_env_file(".env")

project = os.getenv("LANGSMITH_PROJECT", "ai-anki-language-assistant")
endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
api_key = os.getenv("LANGSMITH_API_KEY")

print("\n=== ENV CHECK ===")
print("LANGSMITH_PROJECT =", project)
print("LANGSMITH_ENDPOINT =", endpoint)
print("LANGSMITH_TRACING =", os.getenv("LANGSMITH_TRACING"))
print("API_KEY_CONFIGURED =", bool(api_key))

try:
    print("LANGSMITH_PACKAGE_VERSION =", version("langsmith"))
except PackageNotFoundError:
    print("LANGSMITH_PACKAGE_VERSION = NOT INSTALLED")
    raise SystemExit("Install with: py -m pip install langsmith")

if not api_key:
    raise SystemExit("ERROR: LANGSMITH_API_KEY missing in .env")

# Force both modern and legacy env names.
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGSMITH_PROJECT"] = project
os.environ["LANGCHAIN_PROJECT"] = project
os.environ["LANGSMITH_ENDPOINT"] = endpoint
os.environ["LANGCHAIN_ENDPOINT"] = endpoint
os.environ["LANGSMITH_API_KEY"] = api_key
os.environ["LANGCHAIN_API_KEY"] = api_key

from langsmith import Client

client = Client(api_key=api_key, api_url=endpoint)

run_id = uuid4()
run_name = "ai_anki_minimal_direct_test_" + datetime.now().strftime("%Y%m%d_%H%M%S")
now = datetime.now(timezone.utc)

print("\n=== SENDING DIRECT RUN ===")
print("run_name =", run_name)
print("run_id =", run_id)
print("project =", project)

client.create_run(
    id=run_id,
    name=run_name,
    run_type="chain",
    project_name=project,
    inputs={
        "message": "Hello from AI Anki minimal direct LangSmith test",
    },
    outputs={
        "status": "ok",
        "result": "LangSmith received a direct test run",
    },
    start_time=now,
    end_time=datetime.now(timezone.utc),
    extra={
        "metadata": {
            "source": "standalone_test_script",
            "feature": "langsmith_direct_connection_test",
            "provider": "system",
            "model": "none",
            "outcome": "test",
            "app": "AI Anki Language Assistant",
        }
    },
    tags=["ai-anki", "minimal-test", "direct-client"],
)

# Your SDK has Client.flush(), not wait_for_all_tracers.
client.flush(timeout=10)

time.sleep(2)

print("\nDONE")
print("Now open LangSmith project:")
print(project)
print("Search for run:")
print(run_name)
print("or run_id:")
print(run_id)