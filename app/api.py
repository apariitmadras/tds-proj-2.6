from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, subprocess, json, uuid

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# ---- STEP 2: call Gemini to break the task down --------------------
from google import genai
PROMPT_PATH = "prompts/abdul_task_breakdown.txt"

def task_breakdown(question: str) -> str:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = open(PROMPT_PATH).read()
    resp = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=[question, prompt],
    )
    open("abdul_breaked_task.txt", "w").write(resp.text)
    return resp.text
# --------------------------------------------------------------------

@app.post("/api/")
async def analyze(file: UploadFile = File(...)):
    try:
        question = (await file.read()).decode()
        task_breakdown(question)                       # Steps 1-2
        result = subprocess.check_output(["python", "main.py", "--stdin"], input=question.encode())
        return json.loads(result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
