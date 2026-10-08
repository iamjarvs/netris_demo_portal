import re
from pathlib import Path

main = Path("demo-portal/app/main.py")
content = main.read_text()

api_logic = """@app.post("/api/system/update")
async def update_portal():
    import subprocess
    try:
        res = subprocess.run(["git", "pull", "--rebase"], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
        return {"success": True, "message": "Demo portal updated: " + res.stdout.strip()}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Git pull failed: {e.stderr or e.output}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(e)}")

@app.get("/api/tools")"""

content = content.replace('@app.get("/api/tools")', api_logic)
main.write_text(content)
print("main portal update added")
