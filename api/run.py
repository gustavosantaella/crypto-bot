import sys
import os
import uvicorn

if __name__ == "__main__":
    env_file = ".env"
    
    # Si no se pasa argumento --env, y no existe .env, usar .sol.env como fallback
    has_env_arg = False
    for arg in sys.argv:
        if arg.startswith("--env="):
            env = arg.split("=")[1]
            env_file = f"../environments/.{env}.env"
            has_env_arg = True
            break
            
    if not has_env_arg and not os.path.exists(env_file):
        if os.path.exists("../environments/.sol.env"):
            env_file = "../environments/.sol.env"
            
    os.environ["ENV_FILE"] = env_file

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
