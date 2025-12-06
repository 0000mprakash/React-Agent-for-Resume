import subprocess
from langchain.agents import create_agent
from langchain_openai import AzureChatOpenAI
# from langchain.tools import Tool
from langchain_core.tools import tool
import subprocess
from typing import List
from langchain.tools import tool
from reportlab.pdfgen import canvas
import PyPDF2
import webbrowser
from dotenv import load_dotenv
import os

load_dotenv() 
# ---------------------------Tools---------------------------------------------------
@tool
def read_tex(path: str) -> str:
    """
    Reads the content of a LaTeX (.tex) file.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading tex file: {e}"
    
@tool
def write_tex(content: str, output_path: str) -> str:
    """
    Writes LaTeX content to a new .tex file.
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"LaTeX file saved to {output_path}"
    except Exception as e:
        return f"Error writing tex file: {e}"
    
@tool
def compile_latex(tex_path: str) -> str:
    """
    Compiles a LaTeX file into PDF using pdflatex.
    """
    try:
        tex_path = os.path.abspath(tex_path)
        subprocess.run(
            ["pdflatex", tex_path],
            check=True,
            cwd=os.path.dirname(tex_path)
        )
        return "PDF successfully compiled."
    except Exception as e:
        return f"Error compiling LaTeX: {e}"

@tool
def read_pdf(path: str) -> str:
    """
    Reads the content of a PDF file and returns it as a string.
    """
    try:
        with open(path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
                
        return text if text else "No text found in PDF."
    
    except Exception as e:
        return f"Error reading PDF: {str(e)}"
    
@tool
def read_txt(path: str) -> str:
    """
    Reads the content of a text (.txt) file and returns it as a string.
    """
    try:
        with open(path, 'r', encoding='utf-8') as file:
            text = file.read()

        return text if text else "The file is empty."

    except FileNotFoundError:
        return "Error: File not found."
    except UnicodeDecodeError:
        return "Error: Could not decode file as UTF-8 text."
    except Exception as e:
        return f"Error reading TXT: {str(e)}"

    
@tool
def list_files_with_query(query: str) -> List[str]:
    """
    List all files in the current directory that contain the query string in their names.
    Input: query string to search for in file names.
    Output: List of file names containing the query string.
    """
    try:
        # Get the current working directory
        current_directory = os.getcwd()

        # List all files in the current directory
        files_in_directory = os.listdir(current_directory)

        # Filter files that contain the query string in their names
        matching_files = [
            os.path.abspath(os.path.join(current_directory, file))
            for file in files_in_directory
            if query.lower() in file.lower()
        ]

        if not matching_files:
            return [f"No files found with '{query}' in the name."]

        return matching_files

    except Exception as e:
        return [f"Error searching for files: {str(e)}"]
    


@tool
def create_pdf(text: str, output_path: str) -> str:
    """
    Creates a PDF file with the provided text and saves it to the given path.
    Example:
        create_pdf("Hello World", "output.pdf")
    """
    try:
        c = canvas.Canvas(output_path)
        text_object = c.beginText(40, 800)

        # Add text line-by-line
        for line in text.split("\n"):
            text_object.textLine(line)

        c.drawText(text_object)
        c.save()

        return f"PDF successfully created at: {output_path}"
    except Exception as e:
        return f"Error creating PDF: {str(e)}"



#-------------------------------------------------------------------------------

# ---------------- LLM SETUP ----------------
llm = AzureChatOpenAI(
    api_key=os.getenv("api_key"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("azure_endpoint"),   # e.g. https://xxx.openai.azure.com/
    azure_deployment="gpt-4o-mini", 
)
system_message = """
                You are an AI agent running inside a Python environment with access to file manipulation tools (read, write, list, compile, create PDF,read tex, write_tex,compile tex).

IMPORTANT RULES:
- Always use ABSOLUTE file paths when interacting with any tool.
- Never assume your working directory. Always resolve the full absolute path before calling a tool.
- When you list files, always convert filenames into absolute paths before using them.
- If a tool returns a path, treat it as an absolute path and use it directly.
- When compiling LaTeX, always pass the absolute path to the .tex file.
- When writing files, ensure the directory exists or inform the user in a clear way.

Your job is to figure out what the user wants, gather required file paths, and call the correct tools in the correct order.
Only call tools when necessary.

You are an expert resume writer. When generating a new resume:
- Base it on the old resume format.
- Incorporate new skills, projects, and experiences.
- Highlight achievements, results, and measurable impacts.
- Keep it concise and optimized to **fit one page**.
- Prioritize relevance to the target job description.
- Use bullet points for clarity.
- Ensure all sections (Education, Skills, Projects, Experience) are complete and correctly placed.
- Avoid repeating information.
- Make language professional and ATS-friendly.
 Do not remove entire sections from the old resume.
- Summarize or rephrase content instead of deleting it, to keep the resume close to one page.
- When optimizing for relevance, focus on bullets and skills, not whole sections.
            """
# -------------------------------------------   
agent_graph = create_agent(
    model=llm,
    tools=[read_pdf,list_files_with_query,read_txt,create_pdf,read_tex,write_tex,compile_latex],
    system_prompt=system_message
    
)



messa = input("Write what python code you want to create and execute: ")
for step in agent_graph.stream(
    {"messages": [{"role": "user", "content": messa}]}
):
    for update in step.values():
        for message in update.get("messages", []):
            message.pretty_print()