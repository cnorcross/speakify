import asyncio
import edge_tts
import os
import json
import random
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse
from PyPDF2 import PdfReader  # Add this import for PDF processing

output = "/tmp"
if not os.path.exists(output):
    os.mkdir(output)

app = FastAPI(title="Speakify")
app.mount("/tmp", StaticFiles(directory="/tmp"), name="temp")
app.mount ("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Load JSON data
with open('voices.json') as f:
    voice_data = json.load(f)
# Extract voice options from JSON data
voices = [entry['voice'] for entry in voice_data]

async def _convert_text_to_speech(text: str, voice: str) -> str:
    id=random.randint(1,1000000)
    output_file = f"{voice}{id}.mp3"
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(os.path.join(output, output_file))
        return output_file
    except Exception as e:
        return {"error": str(e)}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "voice_data": voice_data})

@app.post("/convert")
async def convert_text(request: Request, text: str = Form(...), voice: str = Form(...)):
    if voice not in voices:
        return {"error": f"Voice '{voice}' not available."}
    output_file = await _convert_text_to_speech(text, voice)
    if "error" in output_file:
        return {"error": output_file["error"]}
    return templates.TemplateResponse("index.html", {"request": request, "output_file": output_file,"voice_data": voice_data})

@app.post("/convert_pdf")
async def convert_pdf(request: Request, file: UploadFile = File(...), voice: str = Form(...)):
    if voice not in voices:
        return {"error": f"Voice '{voice}' not available."}
    
    # Save the uploaded PDF file
    pdf_path = os.path.join(output, file.filename)
    with open(pdf_path, "wb") as pdf_file:
        pdf_file.write(await file.read())
    
    # Extract text from the PDF
    try:
        with open(pdf_path, "rb") as pdf_file:
            reader = PdfReader(pdf_file)  # Use PdfReader instead of PdfFileReader
            text = ""
            for page in reader.pages:  # Iterate over pages directly
                text += page.extract_text()
    except Exception as e:
        return {"error": f"Failed to extract text from PDF: {str(e)}"}
    
    # Convert extracted text to speech
    output_file = await _convert_text_to_speech(text, voice)
    if "error" in output_file:
        return {"error": output_file["error"]}
    
    return templates.TemplateResponse("index.html", {"request": request, "output_file": output_file, "voice_data": voice_data})

@app.get("/audio/{output_file}")
async def get_audio(output_file: str):
    file_path = os.path.join(output, output_file)
    return FileResponse(file_path)

if __name__=="__main__":
    import uvicorn
    uvicorn.run('main:app', host="0.0.0.0", port=8000, log_level="info", reload=True)
