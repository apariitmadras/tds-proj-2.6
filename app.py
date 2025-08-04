# app.py

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google import genai
import openai, os, subprocess, base64, io

# Initialize FastAPI
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Load prompt templates
BASE_DIR = os.path.dirname(__file__)
with open(os.path.join(BASE_DIR, "prompts/abdul_task_breakdown.txt")) as f:
    TASK_BREAKDOWN_PROMPT = f.read()

# 1. Task breakdown using Google Gemini
def task_breakdown(task: str) -> str:
    """
    Use Google Gemini (via google-genai) to break down the user task into steps.
    """
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=[task, TASK_BREAKDOWN_PROMPT],
    )
    # Save breakdown to file (for debugging or future use)
    with open("abdul_breaked_task.txt", "w") as f:
        f.write(response.text)
    return response.text

# 2. Helper to run generated Python code
def run_python_code(code: str) -> str:
    """
    Write generated code to a temp file and execute it, returning stdout.
    """
    with open("temp_script.py", "w") as f:
        f.write(code)
    result = subprocess.run(["python", "temp_script.py"], capture_output=True, text=True)
    if result.stderr:
        raise RuntimeError(f"Error executing code: {result.stderr}")
    return result.stdout

# 3. Endpoint to analyze the question
@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Accepts a file containing the analysis task description.
    Breaks down the task, calls LLMs to generate and run code, and returns JSON answer.
    """
    try:
        content = await file.read()
        question = content.decode("utf-8")

        # Break down the task into steps
        breakdown = task_breakdown(question)
        print("Task breakdown:", breakdown)

        # Call OpenAI (ChatCompletion) to handle the analysis.
        # We pass the original question and breakdown as context.
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.ChatCompletion.create(
            model="gpt-4", 
            messages=[
                {"role": "system", "content": "You are a helpful data analyst."},
                {"role": "user", "content": question},
                {"role": "assistant", "content": breakdown}
            ],
            functions=[
                # Define functions that the model can call. These should match tools.py.
                {
                    "name": "scrape_website",
                    "description": "Scrapes a URL and saves its HTML.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to scrape"},
                            "output_file": {"type": "string", "description": "Filename to save HTML"}
                        },
                        "required": ["url", "output_file"]
                    }
                },
                {
                    "name": "get_relevant_data",
                    "description": "Parses saved HTML and extracts data by CSS selector.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_name": {"type": "string", "description": "HTML file to read"},
                            "css_selector": {"type": "string", "description": "CSS selector for data"}
                        },
                        "required": ["file_name", "css_selector"]
                    }
                },
                {
                    "name": "answer_questions",
                    "description": "Executes analysis code and returns stdout",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Python code to run"}
                        },
                        "required": ["code"]
                    }
                }
            ],
            function_call="auto"
        )

        message = response.choices[0].message

        # If the model returned a function call, handle it
        if message.get("function_call"):
            name = message["function_call"]["name"]
            args = message["function_call"]["arguments"]
            import json
            params = json.loads(args)
            # Dispatch to the appropriate function
            if name == "scrape_website":
                from tools import scrape_website
                scrape_website(**params)
                # After scraping, we might re-query the model for next steps (loop omitted for brevity)
            elif name == "get_relevant_data":
                from tools import get_relevant_data
                data = get_relevant_data(**params)
                # (Process data as needed or feed back to model)
            elif name == "answer_questions":
                output = run_python_code(params["code"])
                return {"result": output}

        # If no function call, assume the model answered directly.
        return JSONResponse(content={"result": message["content"]})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
