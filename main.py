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
import re
import json
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
def parse_tex_to_json(path: str) -> dict:
    r"""
    Robust LaTeX resume parser for your specific template.
    Handles:
    - multiline \resumeSubheading
    - bullets in any \item or bare dash format
    - skill lines without \item
    """

    if not os.path.exists(path):
        return {"error": f"File '{path}' not found."}

    with open(path, "r", encoding="utf-8") as f:
        tex = f.read()

    data = {}

    # ---- Extract sections ----
    section_regex = r"\\section\{\\textbf\{([^}]+)\}\}(.*?)((?=\\section)|\Z)"
    sections = re.findall(section_regex, tex, flags=re.DOTALL)

    for section_name, body, _ in sections:
        key = section_name.strip()
        data[key] = []

        # ---- Extract resumeSubheading (multiline, tolerant) ----
        sub_regex = (
            r"\\resumeSubheading\s*"
            r"\{([^}]*)\}\s*"     # title
            r"\{([^}]*)\}\s*"     # date
            r"\{([^}]*)\}\s*"     # role
            r"\{([^}]*)\}"        # location
        )

        sub_items = list(re.finditer(sub_regex, body, flags=re.DOTALL))

        if sub_items:
            for i, m in enumerate(sub_items):
                entry = {
                    "title": m.group(1).strip(),
                    "date": m.group(2).strip(),
                    "role": m.group(3).strip(),
                    "location": m.group(4).strip(),
                    "bullets": []
                }

                start = m.end()
                end = sub_items[i + 1].start() if i + 1 < len(sub_items) else len(body)
                block = body[start:end]

                # bullets: \item{...} or \item ... or dash bullets
                bullets = re.findall(r"\\item\s*\{([^}]*)\}", block)
                if not bullets:
                    bullets = re.findall(r"\\item\s+([^\n]+)", block)
                if not bullets:
                    bullets = re.findall(r"-\s*(.*)", block)

                entry["bullets"] = [b.strip() for b in bullets if b.strip()]
                data[key].append(entry)

        else:
            # ---- Skills fallback: grab meaningful lines ----
            lines = [
                l.strip()
                for l in body.split("\n")
                if l.strip() and not l.strip().startswith("%")
            ]

            cleaned = []
            for l in lines:
                # remove LaTeX markup
                l = re.sub(r"\\textbf\{([^}]*)\}", r"\1:", l)
                l = l.replace("\\item", "").strip()
                l = re.sub(r"[{}]", "", l).strip()
                if ":" in l:
                    cleaned.append(l)

            if cleaned:
                data[key] = cleaned

    return data

@tool
def convert_json_to_tex(json_data: dict, output_path: str) -> str:
    """
    Converts a JSON structure back into a LaTeX .tex format.
    
    Arguments:
    - json_data (dict): The parsed JSON data representing the LaTeX structure.
    - output_path (str): The path where the LaTeX .tex file should be saved.
    
    Returns:
    - str: The generated LaTeX code as a string.
    """

    latex_code = ""

    # ---- Generate LaTeX sections ----
    for section, content in json_data.items():
        latex_code += f"\\section{{\\textbf{{{section}}}}}\n"

        # ---- Process each resumeSubheading or skills ----
        for entry in content:
            if isinstance(entry, dict):  # This is a subheading with bullets
                latex_code += "\\resumeSubheading"
                latex_code += f"{{{entry['title']}}}{{{entry['date']}}}{{{entry['role']}}}{{{entry['location']}}}\n"
                
                # Adding bullets
                for bullet in entry.get('bullets', []):
                    latex_code += f"\\item{{{bullet}}}\n"

            else:  # This is a skill line (from cleaned section)
                latex_code += f"\\item {entry}\n"

        latex_code += "\n"

    # Save the generated LaTeX code to a .tex file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(latex_code)

    return latex_code


    
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
    

    
def orchestrator_stream(resume_path, job_path, new_skill_path=None, template_path=None, output_dir="output"):
    import json
    import os

    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Parse LaTeX resume to JSON
    print("Parsing LaTeX resume to JSON...")
    resume_json = parse_tex_to_json.func(resume_path)  # dict

    # Step 2: Read job description
    print("Reading job description...")
    job_text = read_txt.func(job_path)

    # Step 3: Read new skills if provided
    new_skills = ""
    if new_skill_path:
        new_skills = read_txt.func(new_skill_path)

    # Step 4: Prepare agent prompt
    prompt = f"""
    You are updating a JSON resume for a job description and new skills.
    Resume JSON:
    {resume_json}

    Job Description:
    {job_text}

    New Skills / Achievements:
    {new_skills}

    Output the updated resume as JSON. Preserve all structure; rewrite bullets for relevance and ATS optimization.
    """

    # Step 5: Stream agent response
    updated_json_str = ""
    print("Updating resume JSON with agent...")
    for step in agent_graph.stream({"messages": [{"role": "user", "content": prompt}]}):
        for update in step.values():
            for message in update.get("messages", []):
                message.pretty_print()  # real-time streaming
                if "content" in message:
                    updated_json_str += message["content"]

    # Step 6: Parse JSON returned by agent, fallback if invalid
    try:
        updated_json = json.loads(updated_json_str)
    except Exception as e:
        print(f"Warning: Failed to parse agent output as JSON: {e}")
        print("Using original resume JSON as fallback.")
        updated_json = resume_json

    # Step 7: Convert JSON to LaTeX
    print("Converting updated JSON to LaTeX...")
    updated_tex_path = os.path.join(output_dir, "updated.tex")
    convert_json_to_tex.func(updated_json, updated_tex_path)

    # Step 8: Compile LaTeX to PDF
    print("Compiling LaTeX to PDF...")
    compile_latex.func(updated_tex_path)
    updated_pdf_path = os.path.join(output_dir, "updated.pdf")

    print(f"Updated LaTeX saved at: {updated_tex_path}")
    print(f"Updated PDF saved at: {updated_pdf_path}")

    return updated_tex_path, updated_pdf_path



#-------------------------------------------------------------------------------

# ---------------- LLM SETUP ----------------
llm = AzureChatOpenAI(
    api_key=os.getenv("api_key"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("azure_endpoint"),   # e.g. https://xxx.openai.azure.com/
    azure_deployment="gpt-4o-mini", 
)
system_message = """
                You are an AI agent running inside a Python environment with access to file manipulation tools 
(read, write, list, compile, create PDF, read_tex, write_tex, compile_latex).

IMPORTANT TOOL RULES:
- Always use ABSOLUTE file paths for every tool call.
- Never assume your working directory; resolve paths explicitly.
- When listing files, always convert results to absolute paths before using them.
- When writing a file, ensure the directory exists or clearly warn the user.
- When compiling LaTeX, always provide the absolute path of the .tex file.

RESUME REWRITE INSTRUCTIONS:
You are a senior ATS-optimization expert and an expert resume writer.

When generating a new resume (new.tex):
1. **Always preserve the full structure and formatting of the original LaTeX file (main.tex).**
   - Do NOT remove or rename entire sections.
   - Only modify the *content inside* sections.

2. **Relevance Handling (VERY IMPORTANT):**
   - Include ALL bullets, skills, and projects that are relevant to the target job.
   - If a bullet is not an exact match, but still supports the candidate’s competence, KEEP IT.
   - Only remove a bullet if it is clearly irrelevant AND keeping it would harm ATS relevance.
   - When in doubt, KEEP the bullet but rewrite it to be more compact and relevant.

3. **Old Resume + New Skills + Job Description Logic:**
   - Use main.tex as the NOT-to-be-modified template.
   - Use new_skill.txt to add new skills.
   - Use About_job.txt ONLY to judge relevance and keyword importance.
   - NEVER delete content purely because it’s not mentioned in About_job.txt.
   - Instead, adapt and rewrite to fit the role.

4. **Compactness Requirements:**
   - Keep content concise and compact, but **do NOT shorten so aggressively that meaning or achievements are lost**.
   - Use strong, metric-driven bullet points.
   - Prefer rephrasing over deleting.

5. **ATS Optimization Rules:**
   - Include exact keywords from About_job.txt naturally in bullets.
   - Preserve technical depth.
   - Ensure the resume stays close to **one page**, but don't reduce quality for length.
   - Output must score as close as possible to 100% ATS fit without sacrificing completeness.

6. **Output Requirements:**
   - Produce a single LaTeX document that preserves the formatting style of main.tex exactly.
   - Only change the content, not the structural environment.
   - Ensure the result compiles cleanly.

You must think step-by-step:
- Read all user-provided files
- Extract job keywords
- Identify relevant content
- Rewrite, expand, compact, and optimize without deleting valuable content
- Maintain format compatibility
- Produce new.tex

            """
# -------------------------------------------   
agent_graph = create_agent(
    model=llm,
    tools=[read_pdf,list_files_with_query,read_txt,create_pdf,read_tex,write_tex,compile_latex,parse_tex_to_json,convert_json_to_tex],
    system_prompt=system_message
    
)



# user_query = input("Write what python code you want to create and execute: ")
# # with open("user_query.txt", "r", encoding="utf-8") as f:
# #     user_query = f.read()

# for step in agent_graph.stream({"messages": [{"role": "user", "content": user_query}] }):
#     for update in step.values():
#         for message in update.get("messages", []):
#             message.pretty_print()

resume_path = "main.tex"
job_path = "About_job.txt"
new_skill_path = "new_skill.txt"  # optional

updated_tex, updated_pdf = orchestrator_stream(resume_path, job_path, new_skill_path)
