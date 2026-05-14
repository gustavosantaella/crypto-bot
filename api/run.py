import sys
import os
import uvicorn

if __name__ == "__main__":
    env_file = ".env"
    for arg in sys.argv:
        if arg.startswith("--env="):
            env = arg.split("=")[1]
            env_file = f"environments/.{env}.env"
            break
    os.environ["ENV_FILE"] = env_file

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
