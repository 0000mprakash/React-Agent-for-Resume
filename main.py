import subprocess
from langchain.agents import create_agent
from langchain_openai import AzureChatOpenAI
# from langchain.tools import Tool
from langchain_core.tools import tool
import subprocess
from typing import List
import PyPDF2
import webbrowser
from dotenv import load_dotenv
import os

load_dotenv() 
# ---------------------------Tools---------------------------------------------------

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
        matching_files = [file for file in files_in_directory if query.lower() in file.lower()]

        if not matching_files:
            return [f"No files found with '{query}' in the name."]

        return matching_files

    except Exception as e:
        return [f"Error searching for files: {str(e)}"]


#-------------------------------------------------------------------------------

# ---------------- LLM SETUP ----------------
llm = AzureChatOpenAI(
    api_key=os.getenv("api_key"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("azure_endpoint"),   # e.g. https://xxx.openai.azure.com/
    azure_deployment="gpt-4o-mini", 
)
# -------------------------------------------   
agent_graph = create_agent(
    model=llm,
    tools=[read_pdf,list_files_with_query]
)



messa = input("Write what python code you want to create and execute: ")
for step in agent_graph.stream(
    {"messages": [{"role": "user", "content": messa}]}
):
    for update in step.values():
        for message in update.get("messages", []):
            message.pretty_print()