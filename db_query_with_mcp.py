from mcp.server.fastmcp import FastMCP
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
from pathlib import Path
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

load_dotenv()
mcp = FastMCP(
    "smart-db-mcp",
    json_response=True,
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("MCP_PORT", "8000")),
)
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(os.getenv("DB_URL"))


def generate_csv(results:list[dict],filename:str):
    csv_dir = Path("csv")
    csv_dir.mkdir(parents=True, exist_ok=True)
    file_path = csv_dir / f"{filename}.csv"

    df = pd.DataFrame(results)
    df.to_csv(file_path,index=False)
    return str(file_path)

def generate_xlsx(results:list[dict],filename:str):
    xlsx_dir = Path("xlsx")
    xlsx_dir.mkdir(parents=True, exist_ok=True)
    file_path = xlsx_dir / f"{filename}.xlsx"
    df = pd.DataFrame(results)
    df.to_excel(file_path,index=False)
    return str(file_path)

def generate_pdf(results:list[dict],filename:str):
    pdf_dir = Path("pdf")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    file_path = pdf_dir / f"{filename}.pdf"

    df = pd.DataFrame(results)
    table_headers = [str(col) for col in df.columns]
    table_rows = df.fillna("").astype(str).values.tolist()
    table_data = [table_headers] + table_rows

    # Use landscape A4 to fit more columns in tabular results.
    doc = SimpleDocTemplate(str(file_path), pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Query Results", styles["Title"]),
        Spacer(1, 5 * mm),
    ]

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return str(file_path)

def is_query_safe(query):
    # Basic check for SQL injection patterns
    forbidden_patterns = [";", "--", "/*", "*/", "@@", "char", "nchar", "varchar", "nvarchar", "alter", "drop", "insert", "delete", "update"]
    for pattern in forbidden_patterns:
        if pattern in query.lower():
            return False
    return True

def fetch_schema():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [row[0] for row in result]
        schema = {}
        for table in tables:
            result = connection.execute(text(f"PRAGMA table_info({table});"))
            columns = [{"name": row[1], "type": row[2]} for row in result]
            schema[table] = columns
        return schema

@mcp.tool("get_schema", description="Fetch the database schema")
def get_schema():
    return fetch_schema()

@mcp.tool("explain_schema", description="Explain the database schema")
def explain_schema():
    schema = fetch_schema()
    explanation = "Database Schema:\n"
    for table, columns in schema.items():
        explanation += f"Table: {table}\n"
        for column in columns:
            explanation += f"  - {column['name']} ({column['type']})\n"
    return explanation

@mcp.tool("genrate_csv_or_xlsx_or_pdf", description="Genrate a CSV or XLSX or PDF of the database results")
def genrate_csv_or_xlsx_or_pdf(results:list[dict],filename:str,format:str = "csv"):
    format = format.lower().strip()

    # Generate only the requested file format.
    if format == "csv":
        generate_csv(results, filename)
        file_ext = "csv"
    elif format == "xlsx":
        generate_xlsx(results, filename)
        file_ext = "xlsx"
    elif format == "pdf":
        generate_pdf(results, filename)
        file_ext = "pdf"
    else:
        return "Invalid format"

    server_url = (os.getenv("MCP_SERVER_URL") or "").strip().rstrip("/")
    if not server_url:
        return "File generated, but MCP_SERVER_URL is not configured."
    if not server_url.startswith(("http://", "https://")):
        server_url = f"http://{server_url}"

    link = f"{server_url}/{file_ext}/{filename}.{file_ext}"
    return link

@mcp.tool("execute_query", description="Execute a safe SQL query and return JSON or PDF link")
def execute_query(query:str):
    if not is_query_safe(query):
        return {"error": "Unsafe query detected. Please use a read-only SELECT query without restricted patterns."}

    try:
        with engine.connect() as connection:
            result = connection.execute(text(query))
            rows = [dict(row._mapping) for row in result]

        if len(rows) > 10:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"query_results_{timestamp}"
            pdf_link = genrate_csv_or_xlsx(rows, filename, "pdf")
            return {
                "message": "Result has more than 10 rows, returning PDF link.",
                "rows_count": len(rows),
                "pdf_link": pdf_link,
            }

        return {"rows_count": len(rows), "results": rows}
    except Exception as e:
        return {"error": f"Query execution failed: {str(e)}"}

@mcp.custom_route("/csv/{file_name:path}", methods=["GET"])
async def serve_csv(request: Request):
    file_name = request.path_params["file_name"]
    base_dir = Path("csv").resolve()
    file_path = (base_dir / file_name).resolve()
    if base_dir not in file_path.parents and file_path != base_dir:
        return PlainTextResponse("Invalid file path", status_code=400)
    if not file_path.exists() or not file_path.is_file():
        return PlainTextResponse("CSV file not found", status_code=404)
    return FileResponse(str(file_path), media_type="text/csv")

@mcp.custom_route("/xlsx/{file_name:path}", methods=["GET"])
async def serve_xlsx(request: Request):
    file_name = request.path_params["file_name"]
    base_dir = Path("xlsx").resolve()
    file_path = (base_dir / file_name).resolve()
    if base_dir not in file_path.parents and file_path != base_dir:
        return PlainTextResponse("Invalid file path", status_code=400)
    if not file_path.exists() or not file_path.is_file():
        return PlainTextResponse("XLSX file not found", status_code=404)
    return FileResponse(
        str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

@mcp.custom_route("/pdf/{file_name:path}", methods=["GET"])
async def serve_pdf(request: Request):
    file_name = request.path_params["file_name"]
    base_dir = Path("pdf").resolve()
    file_path = (base_dir / file_name).resolve()
    if base_dir not in file_path.parents and file_path != base_dir:
        return PlainTextResponse("Invalid file path", status_code=400)
    if not file_path.exists() or not file_path.is_file():
        return PlainTextResponse("PDF file not found", status_code=404)
    return FileResponse(str(file_path), media_type="application/pdf")


@mcp.prompt(title="Database Assistant", description="Assist with database queries and schema information")
def database_assistant(quetion:str):
    return f"""
    you are a helpful assistant for answering questions about the database and executing SQL queries.
    You can use the following tools:
    1. get_schema: Fetch the database schema.
    2. explain_schema: Explain the database schema in detail.
    3. execute_query: Execute a SQL query and return the results.
    4. genrate_csv_or_xlsx: Genrate a CSV or XLSX of the database results.
    When executing a query, ensure it is safe and does not contain any harmful patterns. If the query is unsafe, return a warning message instead of executing it.
    Question: {quetion}
    """

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
    
