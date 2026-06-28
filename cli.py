"""
AI Chat Log Converter - Command Line Interface
License: MIT

A lightweight CLI tool for converting AI chat logs to various formats.
Designed for individual developers who need quick log processing from the terminal.

Usage Examples:
    # Auto-detect columns and convert to JSON (finetune mode)
    chatlog convert chat.csv --mode finetune

    # Extract specific agent records
    chatlog extract chat.csv --agent "Assistant" --output ./extracted

    # Classify all agents into separate files
    chatlog classify chat.csv --output ./classified

    # Convert with manual column specification
    chatlog convert chat.csv --mode context --agent-col bot --role-col speaker --content-col text
"""

import argparse
import sys
import os
from typing import List

# Import core module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import (
    parse_file,
    auto_detect_columns,
    batch_process_auto,
    convert_to_json,
    extract_agent,
    classify_agents,
    ProcessResult,
    set_language,
    t,
    get_file_size_mb
)


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser with user-friendly help text.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog='chatlog',
        description='🤖 AI Chat Log Converter - Process and transform AI chat logs\n'
                    '\n'
                    'Quick Start:\n'
                    '  chatlog convert chat.csv                  Auto-detect & convert to JSON\n'
                    '  chatlog extract chat.csv --agent Bot1    Extract specific agent\n'
                    '  chatlog classify chat.csv                Split by agent\n'
                    '\n'
                    'For more information, use: chatlog <command> --help',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Examples:\n'
               '  %(prog)s convert chat.csv --mode finetune\n'
               '  %(prog)s convert chat.csv --mode context --reverse\n'
               '  %(prog)s extract chat.csv --agent "GPT-4"\n'
               '  %(prog)s classify chat.csv --output ./output\n'
               '  %(prog)s preview chat.csv\n'
               '  %(prog)s lang en\n',
        add_help=True
    )

    # Global options
    parser.add_argument(
        '--lang',
        choices=['zh', 'en'],
        default='zh',
        help='Set language (default: zh)'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0',
        help='Show version information'
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        dest='command',
        title='Available Commands',
        description='Choose a processing mode',
        metavar='<command>'
    )

    # === convert command ===
    convert_parser = subparsers.add_parser(
        'convert',
        help='Convert chat logs to JSON format',
        description='Convert CSV chat logs to JSON format (finetune or context mode)\n'
                    '\n'
                    'Modes:\n'
                    '  finetune  - Full metadata (message_id, turn_id, token_count)\n'
                    '  context   - Simplified format (role, content, timestamp)\n'
                    '\n'
                    'Columns are auto-detected. Use --manual to specify manually.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    convert_parser.add_argument(
        'files',
        nargs='+',
        help='Input CSV/TXT file(s)'
    )
    convert_parser.add_argument(
        '--mode', '-m',
        choices=['finetune', 'context', 'openai'],
        default='finetune',
        help='Output format mode (default: finetune)\n'
             '  finetune  - Full metadata (message_id, turn_id, token_count)\n'
             '  context   - Simplified format (role, content, timestamp)\n'
             '  openai    - OpenAI fine-tuning format (JSONL, pure messages)'
    )
    convert_parser.add_argument(
        '--output', '-o',
        default='./output',
        help='Output directory (default: ./output)'
    )
    convert_parser.add_argument(
        '--reverse', '-r',
        action='store_true',
        help='Reverse message order in output'
    )
    convert_parser.add_argument(
        '--manual',
        action='store_true',
        help='Manually specify column mappings'
    )
    convert_parser.add_argument(
        '--agent-col',
        help='Agent name column (used with --manual)'
    )
    convert_parser.add_argument(
        '--role-col',
        help='Role column (used with --manual)'
    )
    convert_parser.add_argument(
        '--content-col',
        help='Content/message column (used with --manual)'
    )
    convert_parser.add_argument(
        '--time-col',
        help='Timestamp column (optional, used with --manual)'
    )

    # === extract command ===
    extract_parser = subparsers.add_parser(
        'extract',
        help='Extract records for a specific agent',
        description='Extract all conversation records matching a specific agent name\n'
                    '\n'
                    'Example:\n'
                    '  chatlog extract chat.csv --agent "GPT-4" --output ./extracted',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    extract_parser.add_argument(
        'files',
        nargs='+',
        help='Input CSV/TXT file(s)'
    )
    extract_parser.add_argument(
        '--agent', '-a',
        required=True,
        help='Target agent name (case-insensitive substring match)'
    )
    extract_parser.add_argument(
        '--output', '-o',
        default='./output',
        help='Output directory (default: ./output)'
    )
    extract_parser.add_argument(
        '--agent-col',
        help='Agent name column (optional, auto-detected if not specified)'
    )

    # === classify command ===
    classify_parser = subparsers.add_parser(
        'classify',
        help='Classify and split records by agent',
        description='Split chat logs into separate files, one per agent\n'
                    '\n'
                    'Each output file is named: {original}_{agent_name}.csv',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    classify_parser.add_argument(
        'files',
        nargs='+',
        help='Input CSV/TXT file(s)'
    )
    classify_parser.add_argument(
        '--output', '-o',
        default='./output',
        help='Output directory (default: ./output)'
    )
    classify_parser.add_argument(
        '--agent-col',
        help='Agent name column (optional, auto-detected if not specified)'
    )

    # === preview command ===
    preview_parser = subparsers.add_parser(
        'preview',
        help='Preview file structure and auto-detected columns',
        description='Display file headers, sample data, and detected column mappings\n'
                    '\n'
                    'Useful for verifying column detection before processing.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    preview_parser.add_argument(
        'file',
        help='Input CSV/TXT file to preview'
    )
    preview_parser.add_argument(
        '--rows', '-n',
        type=int,
        default=5,
        help='Number of rows to preview (default: 5)'
    )

    # === lang command ===
    lang_parser = subparsers.add_parser(
        'lang',
        help='Set display language',
        description='Change the language for messages and output\n'
                    '\n'
                    'Supported languages: zh (Chinese), en (English)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    lang_parser.add_argument(
        'language',
        choices=['zh', 'en'],
        help='Language code (zh or en)'
    )

    return parser


def cmd_convert(args) -> int:
    """
    Handle the 'convert' command.

    Args:
        args: Parsed arguments namespace

    Returns:
        Exit code (0 for success, 1 for error)
    """
    print(t('cli_converting').format(len(args.files), args.mode))
    print(t('cli_output_dir').format(args.output))
    
    # Show file sizes
    for fp in args.files:
        size_mb = get_file_size_mb(fp)
        print(f"📄 {os.path.basename(fp)}: {size_mb:.2f} MB")
    print()

    try:
        if args.manual:
            # Manual column specification
            if not all([args.agent_col, args.role_col, args.content_col]):
                print(t('cli_manual_error'))
                print(t('cli_manual_cols'))
                return 1

            results = []
            for fp in args.files:
                base = os.path.splitext(os.path.basename(fp))[0]
                save_path = os.path.join(args.output, f"{base}_{args.mode}.json")

                result = parse_file(fp)
                res = convert_to_json(
                    result=result,
                    agent_col=args.agent_col,
                    role_col=args.role_col,
                    content_col=args.content_col,
                    time_col=args.time_col,
                    mode=args.mode,
                    save_path=save_path,
                    reverse=args.reverse
                )
                results.append(res)
        else:
            # Auto-detect columns with streaming support
            results = batch_process_auto(
                files=args.files,
                mode=args.mode,
                out_dir=args.output,
                reverse=args.reverse
            )

        # Display results
        _display_results(results)
        return 0

    except Exception as e:
        print(t('cli_conversion_failed').format(e))
        return 1


def cmd_extract(args) -> int:
    """
    Handle the 'extract' command.

    Args:
        args: Parsed arguments namespace

    Returns:
        Exit code (0 for success, 1 for error)
    """
    print(t('cli_extracting').format(args.agent, len(args.files)))
    print(t('cli_output_dir').format(args.output))
    print()

    try:
        results = []
        for fp in args.files:
            result = parse_file(fp)

            # Use provided agent_col or auto-detect
            if args.agent_col:
                agent_col = args.agent_col
            else:
                detected = auto_detect_columns(result)
                agent_col = detected.agent_col
                if not agent_col:
                    print(t('cli_warning_no_agent').format(fp))
                    print(t('cli_specify_manual'))
                    continue

            base = os.path.splitext(os.path.basename(fp))[0]
            save_path = os.path.join(args.output, f"{base}_extracted.csv")

            res = extract_agent(result, agent_col, args.agent, save_path)
            results.append(res)

        _display_results(results)
        return 0

    except Exception as e:
        print(t('cli_extraction_failed').format(e))
        return 1


def cmd_classify(args) -> int:
    """
    Handle the 'classify' command.

    Args:
        args: Parsed arguments namespace

    Returns:
        Exit code (0 for success, 1 for error)
    """
    print(t('cli_classifying').format(len(args.files)))
    print(t('cli_output_dir').format(args.output))
    print()

    try:
        results = []
        for fp in args.files:
            result = parse_file(fp)

            # Use provided agent_col or auto-detect
            if args.agent_col:
                agent_col = args.agent_col
            else:
                detected = auto_detect_columns(result)
                agent_col = detected.agent_col
                if not agent_col:
                    print(t('cli_warning_no_agent').format(fp))
                    print(t('cli_specify_manual'))
                    continue

            res = classify_agents(result, agent_col, args.output)
            results.append(res)

        _display_results(results)
        return 0

    except Exception as e:
        print(t('cli_classification_failed').format(e))
        return 1


def cmd_preview(args) -> int:
    """
    Handle the 'preview' command.

    Args:
        args: Parsed arguments namespace

    Returns:
        Exit code (0 for success, 1 for error)
    """
    print(t('cli_previewing').format(args.file))
    print()

    try:
        result = parse_file(args.file)
        detected = auto_detect_columns(result)

        # Display file info
        print("=" * 60)
        print(t('cli_file_info'))
        print("=" * 60)
        print(t('cli_rows').format(len(result.rows)))
        print(t('cli_cols').format(len(result.headers)))
        print(t('cli_delimiter').format(repr(result.delimiter)))
        print()

        # Display headers
        print("=" * 60)
        print(t('cli_col_headers'))
        print("=" * 60)
        for i, header in enumerate(result.headers, 1):
            indicator = ""
            if header == detected.agent_col:
                indicator = t('cli_agent_indicator')
            elif header == detected.role_col:
                indicator = t('cli_role_indicator')
            elif header == detected.content_col:
                indicator = t('cli_content_indicator')
            elif header == detected.time_col:
                indicator = t('cli_time_indicator')
            print(f"   {i:2d}. {header}{indicator}")
        print()

        # Display detected columns
        print("=" * 60)
        print(t('cli_detected_cols'))
        print("=" * 60)
        print(f"   Agent:   {detected.agent_col or t('cli_not_detected')}")
        print(f"   Role:    {detected.role_col or t('cli_not_detected')}")
        print(f"   Content: {detected.content_col or t('cli_not_detected')}")
        print(f"   Time:    {detected.time_col or t('cli_not_detected')}")
        print()

        # Display sample data
        print("=" * 60)
        print(t('cli_sample_data').format(args.rows))
        print("=" * 60)

        preview_rows = result.rows[:args.rows]
        for idx, row in enumerate(preview_rows, 1):
            print(f"\n{t('cli_row_n').format(idx)}")
            for header in result.headers:
                value = row.get(header, "")
                # Truncate long values for display
                if len(value) > 80:
                    value = value[:77] + "..."
                print(f"   {header}: {value}")

        print("\n" + "=" * 60)
        print(t('cli_preview_complete'))
        print("=" * 60)

        return 0

    except Exception as e:
        print(t('cli_preview_failed').format(e))
        return 1


def cmd_lang(args) -> int:
    """
    Handle the 'lang' command.

    Args:
        args: Parsed arguments namespace

    Returns:
        Exit code (always 0)
    """
    set_language(args.language)
    lang_name = "中文" if args.language == 'zh' else "English"
    print(t('cli_lang_set').format(lang_name))
    return 0


def _display_results(results: List[ProcessResult]):
    """
    Display processing results in a user-friendly format.

    Args:
        results: List of ProcessResult objects from processing
    """
    print("\n" + "=" * 60)
    print(t('cli_processing_results'))
    print("=" * 60)

    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count

    for idx, result in enumerate(results, 1):
        status = t('cli_success') if result.success else t('cli_failed')
        print(f"\n[{idx}] {status}")
        print(t('cli_message').format(result.message))

        if result.success and result.files:
            print(t('cli_files').format(len(result.files)))
            for fname in result.files:
                print(f"      • {fname}")

    print("\n" + "-" * 60)
    print(t('cli_summary').format(success_count, fail_count))
    print("=" * 60)

    if fail_count > 0:
        print(t('cli_some_failed'))
    else:
        print(t('cli_all_success'))


def main():
    """
    Main entry point for the CLI tool.

    Parses arguments, sets language, and dispatches to the appropriate command handler.
    """
    parser = create_parser()
    args = parser.parse_args()

    # Set language
    set_language(args.lang)

    # Dispatch to command handler
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    command_handlers = {
        'convert': cmd_convert,
        'extract': cmd_extract,
        'classify': cmd_classify,
        'preview': cmd_preview,
        'lang': cmd_lang,
    }

    handler = command_handlers.get(args.command)
    if handler:
        exit_code = handler(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
