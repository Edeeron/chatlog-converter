"""
AI Chat Log Converter - FastAPI Backend API
License: MIT

A RESTful API service for converting AI chat logs to various formats.
Supports file upload, automatic column detection, batch processing, and file download.

Features:
    - Single file processing (extract, classify, finetune, context, openai)
    - Batch file processing with auto-detection
    - Agent preview and matching
    - Multi-language support (Chinese/English)
    - Temporary file management
    - CORS enabled for frontend integration

Usage:
    uvicorn api:app --reload --host 127.0.0.1 --port 8010

API Endpoints:
    GET  /api/                    - API information
    POST /api/upload              - Upload and parse file
    POST /api/preview             - Preview agent matching
    POST /api/process             - Process single file
    POST /api/batch               - Process multiple files
    GET  /api/download/{filename} - Download processed file
    DELETE /api/cleanup           - Clean temporary files
"""

import os
import tempfile
import shutil
from typing import List, Optional
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

import logging
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Import core logic module
from core import (
    parse_file, auto_detect_columns, extract_agent, classify_agents,
    convert_to_json, batch_process, batch_process_auto, preview_match,
    ProcessResult, set_language, t
)

# Configure logger
logger = logging.getLogger(__name__)

# ============ Application Lifecycle Management ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle with proper startup and shutdown.

    This replaces the deprecated on_event decorators with modern lifespan context manager.
    """
    # Startup
    TEMP_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Clean up old temporary files on startup
    cleanup_old_files(max_age_hours=24)
    
    print(f"✓ AI Chat Log Converter API started")
    print(f"✓ Temp directory: {TEMP_DIR}")
    print(f"✓ Output directory: {OUTPUT_DIR}")

    yield

    # Shutdown
    # Clean up temporary files on shutdown
    cleanup_old_files(max_age_hours=1)
    print("✓ AI Chat Log Converter API shutting down")


# ============ Application Initialization ============

app = FastAPI(
    title="AI Chat Log Converter API",
    description="Process and transform AI chat logs - Group by Agent · Local Processing · Cross-platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# CORS Configuration - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ============ Temporary File Management ============

TEMP_DIR = Path(tempfile.gettempdir()) / "ai_chat_converter"
TEMP_DIR.mkdir(exist_ok=True)

# Output directory: use current working directory's output folder for easy access
OUTPUT_DIR = Path.cwd() / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def cleanup_old_files(max_age_hours: int = 24):
    """
    Clean up temporary files older than specified hours.

    Args:
        max_age_hours: Maximum age in hours before files are cleaned
    """
    if not TEMP_DIR.exists():
        return

    current_time = datetime.now()
    for item in TEMP_DIR.rglob("*"):
        if item.is_file():
            file_age = current_time - datetime.fromtimestamp(item.stat().st_mtime)
            if file_age.total_seconds() > max_age_hours * 3600:
                try:
                    item.unlink()
                except Exception:
                    pass


# ============ Helper Functions ============

def result_to_dict(result: ProcessResult) -> dict:
    """
    Convert ProcessResult to dictionary for JSON response.

    Args:
        result: ProcessResult object from processing

    Returns:
        Dictionary representation of the result
    """
    # Exclude only filenames from full paths for security and consistency
    safe_files = [os.path.basename(f) if os.path.isabs(f) else f for f in (result.files or [])]

    return {
        "success": result.success,
        "message": result.message,
        "files": safe_files,
        "data": result.data
    }


def save_upload(file: UploadFile) -> Path:
    """
    Save uploaded file to temporary directory with unique name.

    Args:
        file: Uploaded file from request

    Returns:
        Path to saved temporary file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_filename = f"{timestamp}_{file.filename.replace('/', '_').replace('\\', '_')}"
    file_path = TEMP_DIR / safe_filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return file_path


# ============ Validation Functions ============

def validate_file_format(filename: str) -> bool:
    """
    Validate that the file has a supported format.

    Args:
        filename: Name of the file to validate

    Returns:
        True if format is supported (.csv or .txt)
    """
    return filename.lower().endswith(('.csv', '.txt'))


def validate_processing_mode(mode: str, target: Optional[str] = None,
                             role_col: Optional[str] = None,
                             content_col: Optional[str] = None) -> None:
    """
    Validate processing mode and required parameters.
    
    Centralized validation logic for both single and batch processing endpoints.
    Raises HTTPException if validation fails.
    
    Args:
        mode: Processing mode (extract, classify, finetune, context, openai)
        target: Target agent name (required for extract mode)
        role_col: Role column name (required for JSON modes)
        content_col: Content column name (required for JSON modes)
        
    Raises:
        HTTPException: If validation fails with appropriate error message
    """
    # Check valid mode
    if mode not in ["extract", "classify", "finetune", "context", "openai"]:
        raise HTTPException(status_code=400, detail=t('error_unknown_mode').format(mode))
    
    # Extract mode requires target
    if mode == "extract" and not target:
        raise HTTPException(status_code=400, detail=t('input_target'))
    
    # JSON modes require content_col and role_col
    if mode in ["finetune", "context", "openai"]:
        if not content_col:
            raise HTTPException(status_code=400, detail=t('select_content_col'))
        if not role_col:
            raise HTTPException(status_code=400, detail=t('select_required'))


# ============ API Endpoints ============

@app.get("/api/")
async def root():
    """
    Get API information and available modes.

    Returns:
        API metadata including name, version, and supported processing modes
    """
    return {
        "name": "AI Chat Log Converter API",
        "version": "1.0.0",
        "description": "Process and transform AI chat logs",
        "modes": {
            "extract": "Extract records for a specific agent",
            "classify": "Split records by agent into separate files",
            "finetune": "Convert to JSON with full metadata (message_id, turn_id, token_count)",
            "context": "Convert to simplified JSON format (role, content, timestamp)",
            "openai": "Convert to OpenAI fine-tuning format (JSONL, pure messages)"
        },
        "endpoints": {
            "upload": "POST /api/upload - Upload and parse file",
            "preview": "POST /api/preview - Preview agent matching",
            "process": "POST /api/process - Process single file",
            "batch": "POST /api/batch - Process multiple files",
            "download": "GET /api/download/{filename} - Download processed file"
        }
    }


@app.post("/api/upload")
async def upload_file(
        file: UploadFile = File(..., description="CSV or TXT file to upload"),
        lang: str = Form("zh", description="Language code (zh or en)")
):
    """
    Upload a file and automatically detect column mappings.

    Parses the uploaded file, detects delimiter, and attempts to identify
    key columns (agent, role, content, time) automatically.

    Args:
        file: Uploaded CSV/TXT file
        lang: Language for messages (default: zh)

    Returns:
        Parsed file information including headers, detected columns, and preview

    Raises:
        HTTPException: If file format is invalid or parsing fails
    """
    try:
        # Validate file format
        if not validate_file_format(file.filename or ""):
            raise HTTPException(
                status_code=400,
                detail=t('error_load') + ": Unsupported file format. Only .csv and .txt are supported."
            )

        set_language(lang)
        file_path = save_upload(file)

        # Parse file and detect columns
        result = parse_file(str(file_path))
        detected = auto_detect_columns(result)

        # Build response
        response_data = {
            "success": True,
            "message": t('auto_detect_ok'),
            "file_info": {
                "filename": file.filename or "",
                "total_rows": len(result.rows),
                "total_cols": len(result.headers),
                "delimiter": repr(result.delimiter)
            },
            "detected": {
                "agent_col": detected.agent_col,
                "role_col": detected.role_col,
                "content_col": detected.content_col,
                "time_col": detected.time_col
            },
            "headers": result.headers,
            "preview": result.rows[:5]
        }

        return response_data

    except ValueError as e:
        logger.error(f"ValueError in upload: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload failed: {type(e).__name__}: {e}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"{t('error_load')}: {str(e)}")


@app.post("/api/preview")
async def preview_agents(
        file: UploadFile = File(..., description="CSV or TXT file to preview"),
        agent_col: str = Form(..., description="Agent column name"),
        target: str = Form(..., description="Target agent name to match"),
        lang: str = Form("zh", description="Language code (zh or en)")
):
    """
    Preview agents matching a target string.

    Performs case-insensitive substring matching to show which agent
    names will be matched before actual extraction.

    Args:
        file: Uploaded CSV/TXT file
        agent_col: Name of the agent column
        target: Target string to match against agent names
        lang: Language for messages (default: zh)

    Returns:
        List of matched agent names and count

    Raises:
        HTTPException: If parsing or matching fails
    """
    try:
        set_language(lang)
        file_path = save_upload(file)
        result = parse_file(str(file_path))

        matched = preview_match(result, agent_col, target)

        return {
            "success": True,
            "matched": matched,
            "count": len(matched),
            "target": target,
            "message": t('matched') + str(len(matched)) if matched else t('not_found')
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/process")
async def process_file(
        file: UploadFile = File(..., description="CSV or TXT file to process"),
        mode: str = Form(..., description="Processing mode: extract, classify, finetune, context, or openai"),
        agent_col: str = Form(..., description="Agent column name"),
        role_col: Optional[str] = Form(None, description="Role column name (required for finetune/context/openai)"),
        content_col: Optional[str] = Form(None, description="Content column name (required for finetune/context/openai)"),
        time_col: Optional[str] = Form(None, description="Timestamp column name (optional)"),
        target: Optional[str] = Form(None, description="Target agent name (required for extract mode)"),
        reverse: bool = Form(False, description="Reverse message order (for JSON modes)"),
        lang: str = Form("zh", description="Language code (zh or en)")
):
    """
    Process a single file with specified mode and column mappings.

    Supported modes:
    - extract: Extract records for a specific agent (requires target)
    - classify: Split records by agent into separate CSV files
    - finetune: Convert to JSON with full metadata
    - context: Convert to simplifiedJSON format
    - openai: Convert to OpenAI fine-tuning format (JSONL)

    Args:
        file: Uploaded CSV/TXT file
        mode: Processing mode
        agent_col: Agent column name
        role_col: Role column name (for JSON modes)
        content_col: Content column name (for JSON modes)
        time_col: Timestamp column name (optional)
        target: Target agent name (for extract mode)
        reverse: Reverse message order (for JSON modes)
        lang: Language for messages (default: zh)

    Returns:
        Processing result with output file information

    Raises:
        HTTPException: If validation fails or processing encounters errors
    """
    try:
        # Validate inputs using centralized validation
        validate_processing_mode(
            mode=mode,
            target=target,
            role_col=role_col,
            content_col=content_col
        )

        set_language(lang)
        file_path = save_upload(file)
        result = parse_file(str(file_path))

        base = Path(file_path).stem
        out_dir = OUTPUT_DIR
        out_dir.mkdir(exist_ok=True)

        # Process based on mode
        if mode == "extract":
            # Include agent name in filename for better identification
            safe_target = "".join(c if c.isalnum() or c in "_-" else "_" for c in target)
            save_path = out_dir / f"{base}_{safe_target}.csv"
            proc_result = extract_agent(result, agent_col, target, str(save_path))

        elif mode == "classify":
            proc_result = classify_agents(result, agent_col, str(out_dir))

        elif mode in ["finetune", "context", "openai"]:
            # Determine file extension based on mode
            ext = "jsonl" if mode == "openai" else "json"
            save_path = out_dir / f"{base}_{mode}.{ext}"
            proc_result = convert_to_json(
                result=result, agent_col=agent_col,
                role_col=role_col or "", content_col=content_col,
                time_col=time_col, mode=mode,
                save_path=str(save_path), reverse=reverse
            )

        return result_to_dict(proc_result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{t('error')}: {str(e)}")


@app.post("/api/batch")
async def batch_process_api(
        files: List[UploadFile] = File(..., description="Multiple CSV or TXT files to process"),
        mode: str = Form(..., description="Processing mode: extract, classify, finetune, context, or openai"),
        agent_col: Optional[str] = Form(None,
                                        description="Agent column name (optional, auto-detected if not provided)"),
        role_col: Optional[str] = Form(None, description="Role column name (for JSON modes)"),
        content_col: Optional[str] = Form(None, description="Content column name (for JSON modes)"),
        time_col: Optional[str] = Form(None, description="Timestamp column name (optional)"),
        target: Optional[str] = Form(None, description="Target agent name (for extract mode)"),
        reverse: bool = Form(False, description="Reverse message order (for JSON modes)"),
        auto_detect: bool = Form(True, description="Use automatic column detection"),
        lang: str = Form("zh", description="Language code (zh or en)")
):
    """
    Process multiple files with automatic or manual column detection.

    When auto_detect is True, detects columns from the first file and applies
    to all files. When False, uses manually specified column names.

    Args:
        files: List of uploaded CSV/TXT files
        mode: Processing mode
        agent_col: Agent column name (for manual mode)
        role_col: Role column name (for manual mode)
        content_col: Content column name (for manual mode)
        time_col: Timestamp column name (optional)
        target: Target agent name (for extract mode)
        reverse: Reverse message order (for JSON modes)
        auto_detect: Use automatic detection (default: True)
        lang: Language for messages (default: zh)

    Returns:
        Batch processing results with individual file results

    Raises:
        HTTPException: If validation fails or processing encounters errors
    """
    try:
        # Validate inputs
        validate_processing_mode(
            mode=mode,
            target=target,
            role_col=role_col,
            content_col=content_col
        )

        set_language(lang)

        # Save all uploaded files
        file_paths = []
        for f in files:
            if not validate_file_format(f.filename or ""):
                continue
            file_paths.append(str(save_upload(f)))

        if not file_paths:
            raise HTTPException(status_code=400, detail="No valid files provided")

        out_dir = str(OUTPUT_DIR)

        # Process files
        if auto_detect:
            results = batch_process_auto(
                file_paths, mode, target=target,
                out_dir=out_dir, reverse=reverse
            )
        else:
            results = batch_process(
                file_paths, mode,
                agent_col=agent_col, role_col=role_col,
                content_col=content_col, time_col=time_col,
                target=target, out_dir=out_dir, reverse=reverse
            )

        success_count = sum(1 for r in results if r.success)

        return {
            "success": True,
            "total": len(results),
            "success_count": success_count,
            "failed_count": len(results) - success_count,
            "results": [result_to_dict(r) for r in results]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{t('error')}: {str(e)}")


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """
    Download a processed file from the output directory.

    Args:
        filename: Name of the file to download (from output directory)

    Returns:
        File response for download

    Raises:
        HTTPException: If file does not exist or path is invalid
    """
    # Security: Only allow files from output directory
    file_path = OUTPUT_DIR / filename

    # Prevent directory traversal attacks
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Verify file is within output directory
    try:
        file_path.resolve().relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


@app.delete("/api/cleanup")
async def cleanup_files(max_age_hours: int = 24):
    """
    Clean up temporary files older than specified hours.

    Args:
        max_age_hours: Maximum age in hours before cleanup (default: 24)

    Returns:
        Cleanup status message
    """
    try:
        cleanup_old_files(max_age_hours)
        return {
            "success": True,
            "message": f"Cleaned up files older than {max_age_hours} hours"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint for monitoring.

    Returns:
        Service health status
    """
    return {
        "status": "healthy",
        "temp_dir": str(TEMP_DIR),
        "output_dir": str(OUTPUT_DIR),
        "timestamp": datetime.now().isoformat()
    }


# ============ Static Files (Web Frontend) ============

static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")

# ============ Main Entry Point ============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8020,
        log_level="info"
    )
