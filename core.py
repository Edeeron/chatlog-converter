"""
AI Chat Log Converter - Core Logic Module
License: MIT
"""

import csv
import json
import os
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import tiktoken

# Constants
SAMPLE_SIZE_FOR_DELIMITER = 2048  # Bytes to read for delimiter detection
DETECTION_SAMPLE_ROWS = 50  # Rows sampled for column type detection
CONTENT_LENGTH_THRESHOLD = 5  # Average content length threshold for content column detection
SCORE_EXACT_MATCH = 10  # Score for exact keyword match
SCORE_PARTIAL_MATCH = 5  # Score for partial keyword match

# Logging Configuration
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
try:
    os.makedirs(_LOG_DIR, exist_ok=True)
except PermissionError:
    # Fallback to temp directory on systems with restricted permissions (Linux/Mac)
    import tempfile
    _LOG_DIR = os.path.join(tempfile.gettempdir(), "chatlog_converter_logs")
    os.makedirs(_LOG_DIR, exist_ok=True)
    logger = logging.getLogger(__name__)
    logger.warning(f"Cannot write to {_LOG_DIR}, using temp directory instead")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            os.path.join(_LOG_DIR, "chat_converter.log"),
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Internationalization
_LANG_CACHE = {}
_current_lang = 'zh'


def _load_lang(lang: str) -> dict:
    """Load language dictionary with caching."""
    if lang not in _LANG_CACHE:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locales', f'{lang}.json')
        with open(path, 'r', encoding='utf-8') as f:
            _LANG_CACHE[lang] = json.load(f)
    return _LANG_CACHE[lang]


def set_language(lang: str):
    """Set current language."""
    global _current_lang
    _current_lang = lang
    logger.info(f"Language switched to: {lang}")


def t(key: str) -> str:
    """Translate key to current language."""
    return _load_lang(_current_lang).get(key, key)


# Data Models

@dataclass
class ParseResult:
    """Parsed CSV/text file result."""
    headers: List[str]
    rows: List[Dict[str, str]]
    delimiter: str
    file_path: str


@dataclass
class DetectResult:
    """Auto-detected column mapping."""
    agent_col: Optional[str] = None
    role_col: Optional[str] = None
    content_col: Optional[str] = None
    time_col: Optional[str] = None


@dataclass
class ProcessResult:
    """Processing operation result."""
    success: bool
    message: str
    files: List[str] = None
    data: Any = None

    def __post_init__(self):
        if self.files is None:
            self.files = []


# File Parsing

def parse_file(file_path: str) -> ParseResult:
    """
    Parse CSV/text file with auto delimiter detection.
    
    Args:
        file_path: Path to file
    Returns:
        ParseResult with headers, rows, delimiter
    Raises:
        ValueError: If file is empty
    """
    with open(file_path, "r", encoding="utf-8-sig") as f:
        sample = f.read(SAMPLE_SIZE_FOR_DELIMITER)
        f.seek(0)
        delimiter = "\t" if "\t" in sample else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        headers = reader.fieldnames or []
        rows = list(reader)

    if not rows:
        raise ValueError(t('error_empty'))

    logger.info(f"File loaded successfully: {file_path}, {len(rows)} rows, {len(headers)} columns")
    return ParseResult(headers, rows, delimiter, file_path)


def parse_file_streaming(file_path: str):
    """
    Streamingly parse CSV/text file. Yields rows one at a time.
    
    Args:
        file_path: Path to file
    Yields:
        First yield: headers list
        Subsequent yields: row_dict for each row
    Raises:
        ValueError: If file is empty
    """
    with open(file_path, "r", encoding="utf-8-sig") as f:
        # Detect delimiter
        sample = f.read(SAMPLE_SIZE_FOR_DELIMITER)
        f.seek(0)
        delimiter = "\t" if "\t" in sample else ","
        
        reader = csv.DictReader(f, delimiter=delimiter)
        headers = reader.fieldnames or []
        
        if not headers:
            raise ValueError(t('error_empty'))
        
        # Yield headers first
        yield headers
        
        # Then yield rows
        row_count = 0
        for row in reader:
            yield row
            row_count += 1
        
        if row_count == 0:
            raise ValueError(t('error_empty'))
        
        logger.info(f"Streaming parse completed: {file_path}, {row_count} rows")


# Column Auto-Detection

def _normalize_header(header: str) -> str:
    """Normalize header for comparison (lowercase, remove separators)."""
    return header.lower().replace(" ", "").replace("_", "").replace("-", "")


def _calculate_keyword_score(keyword: str, header: str) -> int:
    """
    Calculate keyword-header match score.
    
    Returns:
        SCORE_EXACT_MATCH / SCORE_PARTIAL_MATCH / 0
    """
    normalized_header = _normalize_header(header)
    normalized_keyword = _normalize_header(keyword)

    if normalized_header == normalized_keyword:
        return SCORE_EXACT_MATCH
    elif normalized_keyword in normalized_header:
        return SCORE_PARTIAL_MATCH
    return 0


def _check_agent_column_diversity(header: str, rows: List[Dict[str, str]]) -> int:
    """
    Check agent column diversity (should have multiple but not too many unique values).
    
    Returns:
        3 if appropriate diversity, 0 otherwise
    """
    if not rows:
        return 0

    unique_values = set(str(r.get(header, "")) for r in rows if r.get(header))
    num_unique = len(unique_values)
    max_expected = max(len(rows) // 5, 20)

    # Good diversity: >1 unique value but <= max_expected
    if 1 < num_unique <= max_expected:
        return 3
    return 0


def _check_role_column_contains_user(header: str, rows: List[Dict[str, str]]) -> int:
    """
    Check if column contains role indicators like 'user'.
    
    Returns:
        5 if 'user' found, 0 otherwise
    """
    if any("user" in str(r.get(header, "")).lower() for r in rows if r.get(header)):
        return 5
    return 0


def _check_content_column_length(header: str, rows: List[Dict[str, str]]) -> int:
    """
    Check if column has long enough content (content cols typically longer than metadata).
    
    Returns:
        3 if avg length > threshold, 0 otherwise
    """
    sample_rows = rows[:20]
    if not sample_rows:
        return 0

    total_length = sum(len(str(r.get(header, ""))) for r in sample_rows)
    avg_length = total_length / max(len(sample_rows), 1)

    if avg_length > CONTENT_LENGTH_THRESHOLD:
        return 3
    return 0


def _check_time_column_format(header: str, rows: List[Dict[str, str]]) -> int:
    """
    Check if column contains timestamp-like values (-/:年月).
    
    Returns:
        5 if timestamp pattern found, 0 otherwise
    """
    if not rows:
        return 0

    first_value = str(rows[0].get(header, ""))
    timestamp_indicators = "-/:年月"

    if any(c in first_value for c in timestamp_indicators):
        return 5
    return 0


def auto_detect_columns(result: ParseResult) -> DetectResult:
    """
    Auto-detect column types using keyword matching + heuristics.
    
    Detection criteria:
    - Agent: keywords ('agent', 'bot') + moderate diversity
    - Role: keywords ('role', 'speaker') + contains 'user'/'assistant'
    - Content: keywords ('content', 'message') + longer text
    - Time: keywords ('time', 'date') + timestamp format
    
    Args:
        result: ParseResult from file parsing
    Returns:
        DetectResult with detected column names
    """
    headers = result.headers
    rows = result.rows[:DETECTION_SAMPLE_ROWS]

    # Heuristic checks for each column type
    checks = {
        'agent_col': lambda h: _check_agent_column_diversity(h, rows),
        'role_col': lambda h: _check_role_column_contains_user(h, rows),
        'content_col': lambda h: _check_content_column_length(h, rows),
        'time_col': lambda h: _check_time_column_format(h, rows)
    }

    # Keywords for each column type
    keywords = {
        'agent_col': ["agent名称", "agent_name", "agentname", "agent", "智能体", "character", "bot"],
        'role_col': ["role", "角色", "身份", "user", "assistant", "speaker", "说话人", "sender"],
        'content_col': ["content", "内容", "message", "消息", "text", "文本", "dialogue", "对话", "chat"],
        'time_col': ["time", "时间", "timestamp", "date", "日期", "datetime", "created", "sent"]
    }

    # Find best matching column
    detected = {}
    for col_type in ['agent_col', 'role_col', 'content_col', 'time_col']:
        best_match = None
        best_score = 0

        for header in headers:
            # Keyword matching score
            keyword_score = sum(
                _calculate_keyword_score(kw, header)
                for kw in keywords[col_type]
            )

            # Add heuristic score
            heuristic_score = checks[col_type](header)

            total_score = keyword_score + heuristic_score

            if total_score > best_score:
                best_score = total_score
                best_match = header

        detected[col_type] = best_match if best_score > 0 else None

    logger.info(f"Auto-detection result: {detected}")
    return DetectResult(**detected)


# Token Counting

class TokenCounter:
    """Token counter using tiktoken (cl100k_base)."""

    def __init__(self):
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoder = None

    def count(self, text: str) -> int:
        """Count tokens. Falls back to char count if tiktoken unavailable."""
        if self.encoder:
            return len(self.encoder.encode(str(text)))
        return len(str(text))


# Processing Modes

def extract_agent(result: ParseResult, agent_col: str, target: str, save_path: str) -> ProcessResult:
    """
    Extract records matching specific Agent (case-insensitive substring).
    
    Args:
        result: Parsed file data
        agent_col: Agent column name
        target: Target agent name
        save_path: Output CSV path
    Returns:
        ProcessResult with extraction status
    """
    filtered = [r for r in result.rows if target.lower() in str(r.get(agent_col, "")).lower()]
    if not filtered:
        return ProcessResult(False, t('no_match'))

    with open(save_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=result.headers)
        w.writeheader()
        w.writerows(filtered)

    logger.info(f"Extraction completed: {save_path}, {len(filtered)} records")
    return ProcessResult(True, t('extracted').format(len(filtered)), [save_path])


def classify_agents(result: ParseResult, agent_col: str, out_dir: str) -> ProcessResult:
    """
    Split records by Agent into separate CSV files.
    Handles filename conflicts with numeric suffixes.
    
    Args:
        result: Parsed file data
        agent_col: Agent column name
        out_dir: Output directory
    Returns:
        ProcessResult with list of created filenames
    """
    groups = defaultdict(list)
    filename_map = {}

    # Group by Agent
    for r in result.rows:
        agent_name = str(r.get(agent_col, t('unknown_agent')))
        groups[agent_name].append(r)

    saved = []
    base = os.path.splitext(os.path.basename(result.file_path))[0]

    for agent, g_rows in groups.items():
        # Sanitize agent name for filesystem
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in agent)
        fname = f"{base}_{safe}.csv"

        # Handle filename conflicts
        if fname in filename_map:
            counter = 1
            original_fname = fname
            while fname in filename_map:
                fname = f"{base}_{safe}_{counter}.csv"
                counter += 1
            logger.warning(f"Filename conflict: {original_fname} renamed to {fname}")

        filename_map[fname] = agent
        path = os.path.join(out_dir, fname)

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=result.headers)
            w.writeheader()
            w.writerows(g_rows)
        saved.append(fname)

    logger.info(f"Classification completed: {len(groups)} agents, total {len(result.rows)} records")
    return ProcessResult(True, t('classified').format(len(groups), len(result.rows)), saved)


def convert_to_json(
        result: Optional[ParseResult],
        agent_col: str,
        role_col: str,
        content_col: str,
        time_col: Optional[str],
        mode: str,
        save_path: str,
        reverse: bool = False,
        file_path: Optional[str] = None
) -> ProcessResult:
    """
    Convert chat records to JSON (finetune, context, or openai mode).
    
    Finetune mode: includes message_id, turn_id, token_count (JSON Array)
    Context mode: simplified structure with timestamp (JSON Array)
    OpenAI mode: pure messages format for OpenAI fine-tuning (JSONL)
    
    Args:
        result: Parsed data (in-memory mode) or None (streaming mode)
        agent_col: Agent column name
        role_col: Role column name
        content_col: Content column name
        time_col: Timestamp column (optional)
        mode: 'finetune', 'context', or 'openai'
        save_path: Output JSON/JSONL path
        reverse: Reverse message order
        file_path: Input file path (for streaming mode)
    Returns:
        ProcessResult with conversion summary
    """
    counter = TokenCounter()
    groups = defaultdict(list)
    skipped = 0
    total_rows = 0

    # Mode 1: Streaming
    if result is None and file_path:
        stream_iter = parse_file_streaming(file_path)
        headers = next(stream_iter)  # Get headers first (discard, not needed for grouping)
        
        for row in stream_iter:
            total_rows += 1
            agent = str(row.get(agent_col, ""))
            
            if agent:
                groups[agent].append(row)
            else:
                skipped += 1
    # Mode 2: In-memory
    elif result:
        for r in result.rows:
            total_rows += 1
            if agent := str(r.get(agent_col, "")):
                groups[agent].append(r)
            else:
                skipped += 1
    else:
        raise ValueError("Either result or file_path must be provided")

    if skipped > 0:
        logger.warning(f"Skipped {skipped} records with missing agent name")

    # Build conversations and write JSON/JSONL
    conversations_count = 0
    total_msgs = 0
    conversations_data = []  # Collected for return value
    
    # OpenAI mode: use JSONL format (one conversation per line)
    if mode == "openai":
        with open(save_path, "w", encoding="utf-8") as f:
            for idx, (agent, g_rows) in enumerate(groups.items(), 1):
                if reverse:
                    g_rows = list(reversed(g_rows))
                
                messages = _build_messages_openai(g_rows, role_col, content_col, time_col)
                if messages:
                    # Write one conversation per line (JSONL format)
                    json.dump({"messages": messages}, f, ensure_ascii=False)
                    f.write("\n")
                    conversations_count += 1
                    total_msgs += len(messages)
                    conversations_data.append({"messages": messages})
        
        unit = t('session')
        summary = t('converted').format(conversations_count, unit, total_msgs)
        logger.info(f"OpenAI JSONL conversion completed: {save_path}, {conversations_count} conversations, {total_rows} rows")
        return ProcessResult(True, summary, [os.path.basename(save_path)], conversations_data if conversations_data else None)
    
    # Finetune/Context mode: use JSON Array format
    with open(save_path, "w", encoding="utf-8") as f:
        f.write("[\n")
        first_conv = True
        
        for idx, (agent, g_rows) in enumerate(groups.items(), 1):
            if reverse:
                g_rows = list(reversed(g_rows))
            
            messages = _build_messages(g_rows, role_col, content_col, time_col, mode, counter)
            if messages:
                conv = _build_conversation(agent, messages, idx, mode)
                
                if not first_conv:
                    f.write(",\n")
                
                json.dump(conv, f, ensure_ascii=False, indent=2)
                first_conv = False
                conversations_count += 1
                total_msgs += len(messages)
                conversations_data.append(conv)
        
        f.write("\n]")

    unit = t('session') if mode == 'finetune' else t('agent')
    summary = t('converted').format(conversations_count, unit, total_msgs)

    logger.info(f"JSON conversion completed: {save_path}, {conversations_count} conversations, {total_rows} rows")
    return ProcessResult(True, summary, [os.path.basename(save_path)], conversations_data if conversations_data else None)


def _build_messages_openai(
        g_rows: List[Dict[str, str]],
        role_col: str,
        content_col: str,
        time_col: Optional[str]
) -> List[Dict[str, str]]:
    """
    Build message list for OpenAI fine-tuning (pure format, no extra fields).
    
    Only includes role and content fields as required by OpenAI API.
    Filters out messages with empty role/content.
    
    Args:
        g_rows: Row dicts for one Agent
        role_col: Role column name
        content_col: Content column name
        time_col: Timestamp column (optional, not included in output)
    Returns:
        List of message dicts with only role and content
    """
    messages = []
    
    for r in g_rows:
        current_role = str(r.get(role_col, ""))
        current_content = str(r.get(content_col, ""))
        
        # Skip empty role or content
        if not current_role or not current_content:
            continue
        
        messages.append({
            "role": current_role,
            "content": current_content
        })
    
    return messages


def _build_messages(
        g_rows: List[Dict[str, str]],
        role_col: str,
        content_col: str,
        time_col: Optional[str],
        mode: str,
        counter: TokenCounter
) -> List[Dict[str, Any]]:
    """
    Build message list from grouped rows.
    
    Finetune mode: tracks turn_id based on complete user-assistant conversation pairs
    - A turn is defined as: user message(s) followed by assistant response(s)
    - Multiple consecutive user messages are part of the same turn (user追加)
    - Turn increments when we see user after assistant (new conversation round)
    Filters out messages with empty role/content.
    
    Args:
        g_rows: Row dicts for one Agent
        role_col: Role column name
        content_col: Content column name
        time_col: Timestamp column (optional)
        mode: 'finetune' or 'context'
        counter: TokenCounter instance
    Returns:
        List of message dicts
    """
    messages = []
    last_role = None
    current_turn = 0
    has_pending_user = False  # Track if we have unresponded user messages

    for r in g_rows:
        current_role = str(r.get(role_col, ""))

        if mode == "finetune":
            # Turn detection logic:
            # 1. First message starts turn 1
            # 2. Turn increments when user speaks after assistant (new round)
            # 3. Consecutive user messages stay in same turn (user追加)
            # 4. Assistant responses don't increment turn
            
            if last_role is None:
                # First message initializes turn 1
                current_turn = 1
                if current_role == 'user':
                    has_pending_user = True
            elif last_role == 'assistant' and current_role == 'user':
                # New conversation round: user follows assistant
                current_turn += 1
                has_pending_user = True
            elif current_role == 'user' and not has_pending_user:
                # User message without prior pending (edge case)
                has_pending_user = True
            elif current_role == 'assistant' and has_pending_user:
                # Assistant responding to user, keep same turn
                has_pending_user = False

            msg = {
                "message_id": f"msg_{len(messages) + 1:03d}",
                "turn_id": f"turn_{current_turn:03d}",
                "role": current_role,
                "content": str(r.get(content_col, "")),
                "timestamp": str(r.get(time_col, "")) if time_col and r.get(time_col) else "",
                "token_count": counter.count(str(r.get(content_col, "")))
            }
        else:
            msg = {"role": current_role, "content": str(r.get(content_col, ""))}
            if time_col and r.get(time_col):
                msg["timestamp"] = str(r.get(time_col))

        messages.append(msg)
        last_role = current_role

    # Filter empty role/content
    return [m for m in messages if m["role"] and m["content"]]


def _build_conversation(
        agent: str,
        messages: List[Dict[str, Any]],
        idx: int,
        mode: str
) -> Dict[str, Any]:
    """
    Build conversation object from messages.
    
    Finetune mode: includes conversation_id, user_id, agent_name, created_at
    Context mode: simplified (agent_name, messages)
    
    Args:
        agent: Agent name
        messages: Message list
        idx: Conversation index
        mode: 'finetune' or 'context'
    Returns:
        Conversation dict
    """
    if mode == "finetune":
        return {
            "conversation_id": f"conv_{agent}_{idx:03d}",
            "user_id": "",
            "agent_name": agent,
            "created_at": messages[0].get("timestamp", ""),
            "messages": messages
        }
    return {"agent_name": agent, "messages": messages}


# Preview Matching

def preview_match(result: ParseResult, agent_col: str, target: str) -> List[str]:
    """
    Find Agent names matching target (case-insensitive substring).
    Used for preview before extraction.
    
    Args:
        result: Parsed file data
        agent_col: Agent column name
        target: Target string
    Returns:
        Sorted list of matching agent names
    """
    agents = sorted(set(str(r.get(agent_col, "")) for r in result.rows if r.get(agent_col) is not None))
    return [a for a in agents if target.lower() in a.lower()]


# Batch Processing

def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB."""
    return os.path.getsize(file_path) / (1024 * 1024)


def batch_process(
        files: List[str],
        mode: str,
        agent_col: Optional[str] = None,
        content_col: Optional[str] = None,
        role_col: Optional[str] = None,
        time_col: Optional[str] = None,
        target: Optional[str] = None,
        out_dir: str = "./output",
        reverse: bool = False
) -> List[ProcessResult]:
    """
    Process multiple files with explicit column mappings.
    For auto-detection, use batch_process_auto().
    
    Supported modes: extract, classify, finetune, context
    
    Args:
        files: File paths to process
        mode: Processing mode
        agent_col: Agent column name
        content_col: Content column name
        role_col: Role column name
        time_col: Timestamp column (optional)
        target: Target agent (for extract mode)
        out_dir: Output directory
        reverse: Reverse message order
    Returns:
        List of ProcessResult objects
    """
    os.makedirs(out_dir, exist_ok=True)
    results: List[ProcessResult] = []

    for fp in files:
        try:
            base = os.path.splitext(os.path.basename(fp))[0]

            if mode == "extract":
                if not agent_col or target is None:
                    results.append(ProcessResult(False, t("error_missing_agent_or_target")))
                    continue
                save_path = os.path.join(out_dir, f"{base}_extracted.csv")
                result = parse_file(fp)
                results.append(extract_agent(result, agent_col, target, save_path))

            elif mode == "classify":
                if not agent_col:
                    results.append(ProcessResult(False, t("error_missing_agent_col")))
                    continue
                result = parse_file(fp)
                results.append(classify_agents(result, agent_col, out_dir))

            elif mode in ("finetune", "context", "openai"):
                if not all([agent_col, role_col, content_col]):
                    results.append(ProcessResult(False, t("error_missing_required_cols")))
                    continue
                # Determine file extension based on mode
                ext = "jsonl" if mode == "openai" else "json"
                save_path = os.path.join(out_dir, f"{base}_{mode}.{ext}")
                result = parse_file(fp)
                results.append(
                    convert_to_json(
                        result=result, agent_col=agent_col,
                        role_col=role_col, content_col=content_col,
                        time_col=time_col, mode=mode,
                        save_path=save_path, reverse=reverse
                    )
                )
            else:
                results.append(ProcessResult(False, t("error_unknown_mode").format(mode)))

        except Exception as e:
            logger.error(f"Processing failed [{fp}]: {e}")
            results.append(ProcessResult(False, str(e)))

    return results


def batch_process_auto(
        files: List[str],
        mode: str,
        target: Optional[str] = None,
        out_dir: str = "./output",
        reverse: bool = False,
        verify_headers: bool = False
) -> List[ProcessResult]:
    """
    Process multiple files with auto column detection.
    Detects from first file, applies to all. Optionally verifies headers.
    
    Args:
        files: File paths to process
        mode: Processing mode
        target: Target agent (for extract mode)
        out_dir: Output directory
        reverse: Reverse message order
        verify_headers: Verify header consistency
    Returns:
        List of ProcessResult objects
    Raises:
        ValueError: If no files provided
    """
    if not files:
        raise ValueError("No files provided for processing")

    # Parse first file and detect
    try:
        first_result = parse_file(files[0])
    except Exception as e:
        logger.error(f"Failed to parse first file {files[0]}: {e}")
        return [ProcessResult(False, str(e))]

    detected = auto_detect_columns(first_result)

    # Validate required columns
    required_columns = {
        "extract": ["agent_col"],
        "classify": ["agent_col"],
        "finetune": ["agent_col", "role_col", "content_col"],
        "context": ["agent_col", "role_col", "content_col"],
        "openai": ["agent_col", "role_col", "content_col"]
    }

    missing = [col for col in required_columns.get(mode, []) if getattr(detected, col) is None]
    if missing:
        msg = t("error_auto_detect_failed").format(", ".join(missing))
        logger.error(msg)
        return [ProcessResult(False, msg)]

    # Verify header consistency
    valid_files = [files[0]]
    if verify_headers and len(files) > 1:
        first_headers = set(first_result.headers)
        for fp in files[1:]:
            try:
                result = parse_file(fp)
                if set(result.headers) != first_headers:
                    logger.warning(f"Inconsistent headers, skipped: {fp}")
                else:
                    valid_files.append(fp)
            except Exception as e:
                logger.warning(f"Verification failed: {fp} - {e}")
    elif len(files) > 1:
        valid_files.extend(files[1:])

    return batch_process(
        files=valid_files,
        mode=mode,
        agent_col=detected.agent_col,
        content_col=detected.content_col,
        role_col=detected.role_col,
        time_col=detected.time_col,
        target=target,
        out_dir=out_dir,
        reverse=reverse
    )
