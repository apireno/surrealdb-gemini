"""Load and insert Wikipedia embeddings into SurrealDB"""

import ast
import contextlib
import datetime
import logging
import string
from typing import AsyncGenerator
import zipfile

import fastapi
import pandas as pd
import surrealdb 
import tqdm
import wget
from fastapi import templating, responses, staticfiles

import git
import csv
import os
from bs4 import BeautifulSoup  # For HTML parsing
import markdown  # For Markdown parsing 

FORMATTED_RECORD_FOR_INSERT_SURREAL_DOC_EMBEDDING = string.Template(
    """{url: "$url", contents: s"$contents", content_vector: []}"""
)

INSERT_SURREAL_DOC_EMBEDDING_QUERY = string.Template(
    """
    INSERT INTO surreal_doc_embedding [\n $records\n];
    """
)

UPDATE_SURREAL_DOC_EMBEDDING_QUERY = """
    UPDATE surreal_doc_embedding SET content_vector=fn::embeddings_complete("embedding-001", contents) WHERE content_vector = none;
    """




TOTAL_ROWS = 25000
CHUNK_SIZE = 100

NS = "surreal_gemini"
DB = "surreal_gemini"
SURREAL_DB_ADDRESS = "ws://0.0.0.0:8080/"



def surreal_docs_insert() -> None:
    """Main entrypoint to insert Surreal Docs embeddings into SurrealDB."""
    logger = setup_logger("surreal_insert")
    
    out_dir = "Surreal_Docs_Rag/"
    out_csv =  "surreal_docs.txt";
    
    path_to_csv = out_dir +  out_csv;
    
   
    logger.info("reading file {0}".format(path_to_csv))

    logger.info("Connecting to SurrealDB")
    db = surrealdb.SurrealDB(SURREAL_DB_ADDRESS)
    db.signin({"username": "root", "password": "root"})
    db.use(NS,DB)

    logger.info("Inserting rows into SurrealDB")
    df = pd.read_csv(
                path_to_csv,
                usecols=[
                    "url",
                    "contents"
                ]
            );
            
    formatted_rows = [
        FORMATTED_RECORD_FOR_INSERT_SURREAL_DOC_EMBEDDING.substitute(
            url=row["url"],
            contents=row["contents"].replace("\\", "\\\\").replace('"', '\\"'),
        )
        for _, row in df.iterrows()  # type: ignore
    ]

    query = INSERT_SURREAL_DOC_EMBEDDING_QUERY.substitute(
            records=",\n ".join(formatted_rows)
        )
    #

    result = db.query(
        query
    )

    logger.info("insert result {0}".format(result))


    #logger.info("executing {0}".format(UPDATE_SURREAL_DOC_EMBEDDING_QUERY))
    result = db.query(
        UPDATE_SURREAL_DOC_EMBEDDING_QUERY
    )

    logger.info("update result {0}".format(result))







def extract_id(surrealdb_id: str) -> str:
    """Extract numeric ID from SurrealDB record ID.

    SurrealDB record ID comes in the form of `<table_name>:<unique_id>`.
    CSS classes cannot be named with a `:` so for CSS we extract the ID.

    Args:
        surrealdb_id: SurrealDB record ID.

    Returns:
        ID.
    """
    return surrealdb_id.split(":")[1]


def convert_timestamp_to_date(timestamp: str) -> str:
    """Convert a SurrealDB `datetime` to a readable string.

    The result will be of the format: `April 05 2024, 15:30`.

    Args:
        timestamp: SurrealDB `datetime` value.

    Returns:
        Date as a string.
    """
    parsed_timestamp = datetime.datetime.fromisoformat(timestamp.rstrip("Z"))
    return parsed_timestamp.strftime("%B %d %Y, %H:%M")


templates = templating.Jinja2Templates(directory="templates")
templates.env.filters["extract_id"] = extract_id
templates.env.filters["convert_timestamp_to_date"] = convert_timestamp_to_date
life_span = {}


@contextlib.asynccontextmanager
async def lifespan(_: fastapi.FastAPI) -> AsyncGenerator:
    """FastAPI lifespan to create and destroy objects."""
    async with surrealdb.AsyncSurrealDB(url=SURREAL_DB_ADDRESS) as connection:
        await connection.connect()
        await connection.signin(data={"username": "root", "password": "root"})
        await connection.use_namespace(NS)
        await connection.use_database(DB)
        life_span["surrealdb"] = connection
        yield
        life_span.clear()


app = fastapi.FastAPI(lifespan=lifespan)
app.mount("/static", staticfiles.StaticFiles(directory="static"), name="static")


@app.get("/", response_class=responses.HTMLResponse)
async def index(request: fastapi.Request) -> responses.HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/create-chat", response_class=responses.HTMLResponse)
async def create_chat(request: fastapi.Request) -> responses.HTMLResponse:
    chat_record = await life_span["surrealdb"].query(
        """RETURN fn::create_chat();"""
    )
    return templates.TemplateResponse(
        "create_chat.html",
        {
            "request": request,
            "chat_id": chat_record.get("id"),
            "chat_title": chat_record.get("title"),
        },
    )


@app.get("/load-chat/{chat_id}", response_class=responses.HTMLResponse)
async def load_chat(
    request: fastapi.Request, chat_id: str
) -> responses.HTMLResponse:
    message_records = await life_span["surrealdb"].query(
        f"""RETURN fn::load_chat({chat_id})"""
    )
    return templates.TemplateResponse(
        "load_chat.html",
        {
            "request": request,
            "messages": message_records,
            "chat_id": chat_id,
        },
    )


@app.get("/chats", response_class=responses.HTMLResponse)
async def chats(request: fastapi.Request) -> responses.HTMLResponse:
    """Load all chats."""
    chat_records = await life_span["surrealdb"].query(
        """RETURN fn::load_all_chats();"""
    )
    return templates.TemplateResponse(
        "chats.html", {"request": request, "chats": chat_records}
    )


@app.post("/send-user-message", response_class=responses.HTMLResponse)
async def send_user_message(
    request: fastapi.Request,
    chat_id: str = fastapi.Form(...),
    content: str = fastapi.Form(...),
) -> responses.HTMLResponse:
    """Send user message."""
    message = await life_span["surrealdb"].query(
        f"""RETURN fn::create_user_message({chat_id}, s"{content}");"""
    )
    return templates.TemplateResponse(
        "send_user_message.html",
        {
            "request": request,
            "chat_id": chat_id,
            "content": message.get("content"),
            "timestamp": message.get("timestamp"),
        },
    )


@app.get(
    "/send-system-message/{chat_id}", response_class=responses.HTMLResponse
)
async def send_system_message(
    request: fastapi.Request, chat_id: str
) -> responses.HTMLResponse:
    message = await life_span["surrealdb"].query(
        f"""RETURN fn::create_system_message({chat_id});"""
    )

    title = await life_span["surrealdb"].query(
        f"""RETURN fn::get_chat_title({chat_id});"""
    )

    return templates.TemplateResponse(
        "send_system_message.html",
        {
            "request": request,
            "content": message.get("content"),
            "timestamp": message.get("timestamp"),
            "create_title": title == "Untitled chat",
            "chat_id": chat_id,
        },
    )


@app.get("/create-title/{chat_id}", response_class=responses.PlainTextResponse)
async def create_title(chat_id: str) -> responses.PlainTextResponse:
    title = await life_span["surrealdb"].query(
        f"RETURN fn::generate_chat_title({chat_id});"
    )
    return responses.PlainTextResponse(title.strip('"'))


def setup_logger(name: str) -> logging.Logger:
    """Configure and return a logger with the given name."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

def get_file_url(repo_path, file_path,current_directory):
    return repo_path  + "/" + file_path.replace(current_directory, "");
    
def extract_plain_text_from_markdown(file_path):
    with open(file_path, 'r') as f:
        text = f.read()
        html = markdown.markdown(text)  # Convert to HTML first (cleaner extraction)
        return BeautifulSoup(html, 'html.parser').get_text(strip=True)

def extract_plain_text_from_html(file_path):
    with open(file_path, 'r') as f:
        soup = BeautifulSoup(f, 'html.parser')
        return soup.get_text(strip=True)


def extract_file_info(repo_path, repo_dir, csv_filename):
    #"""Extracts file info (URL, title, author, contents) and writes to CSV."""

    if not os.path.exists(repo_dir):
        repo = git.Repo.clone_from(repo_path, repo_dir)
    else:
        repo = git.Repo(repo_dir)
        repo.remotes[0].pull()

    
    
    current_directory = os.getcwd() + "/" +repo_dir
     
    with open(repo_dir+csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["url", "contents"])  # Header row

        for root, _, files in os.walk(repo.working_dir):
            for file in files:
                file_path = os.path.join(root, file)
                url = get_file_url(repo_path, file_path,current_directory)  # You'll need a function to generate URLs
                contents = ""

                if file.endswith(".md") or file.endswith(".mdx"):
                    contents = extract_plain_text_from_markdown(file_path)
                    #title = extract_markdown_title(contents) 
                elif file.endswith(".html"):
                    contents = extract_plain_text_from_html(file_path)
                    #title = extract_html_title(contents)
                # ... Add more cases for other file types
                if contents:
                    writer.writerow([url, contents])

        
def get_docs_data() -> None:
    """Extract `surreal db docs` to `/data`."""
    logger = setup_logger("get-data")


    repo_to_extract = "https://github.com/surrealdb/docs.surrealdb.com";
    out_dir = "Surreal_Docs_Rag/"
    out_csv =  "surreal_docs.txt";

    extract_file_info(repo_to_extract, out_dir, out_csv);
    logger.info("Extracted file successfully. Please check the folder {0} for the data file named {1}".format(out_dir,out_csv))


    
            
