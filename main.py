"""
AI Chat Log Converter - Main Entry Point
License: MIT

Unified entry point for AI Chat Log Converter.
Provides options to launch either the web interface or command-line interface.

Usage:
    python main.py              # Launch web interface (default)
    python main.py --web        # Launch web interface explicitly
    python main.py --cli        # Launch command-line interface
    python main.py --help       # Show help information
"""

import argparse
import sys


def print_banner():
    """Print application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║          🤖  AI Chat Log Converter v1.0.0                ║
║                                                           ║
║     Process and transform AI chat logs                    ║
║     Group by Agent · Local Processing · Privacy Safe      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)





def launch_web(port: int = 8010):
    """Launch the web interface using FastAPI + Uvicorn."""
    print("🚀 Launching Web Interface...")
    print(f"📍 URL: http://127.0.0.1:{port}")
    print(f"📖 API Docs: http://127.0.0.1:{port}/api/docs")
    print("⏹️  Press Ctrl+C to stop\n")

    try:
        import uvicorn
        from api import app

        uvicorn.run(
            app,
            host="127.0.0.1",
            port=port,
            log_level="info"
        )
    except ImportError:
        print("❌ Error: Required packages not installed.")
        print("💡 Please run: pip install fastapi uvicorn python-multipart")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Web interface stopped.")
        sys.exit(0)


def launch_cli():
    """Launch the command-line interface."""
    print("💻 Launching Command-Line Interface...\n")

    try:
        from cli import main as cli_main
        cli_main()
    except ImportError:
        print("❌ Error: CLI module not found.")
        sys.exit(1)
    except SystemExit as e:
        sys.exit(e.code if e.code else 0)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for main entry point."""
    parser = argparse.ArgumentParser(
        prog='chatlog-converter',
        description='🤖 AI Chat Log Converter - Choose your interface\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              Launch web interface (default)
  python main.py --web        Launch web interface explicitly
  python main.py --cli        Launch command-line interface
  python main.py --port 9000  Launch web on custom port
        """,
        add_help=True
    )

    parser.add_argument(
        '--web', '-w',
        action='store_true',
        default=False,
        help='Launch web interface (default)'
    )

    parser.add_argument(
        '--cli', '-c',
        action='store_true',
        default=False,
        help='Launch command-line interface'
    )

    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8010,
        help='Port for web interface (default: 8010)'
    )

    return parser


def main():
    """Main entry point with interface selection."""
    print_banner()

    parser = create_parser()
    args = parser.parse_args()

    # If no arguments provided, default to web interface
    if not args.web and not args.cli:
        print("ℹ️  No mode specified, launching web interface by default.\n")
        launch_web(args.port)
        return

    # Launch selected interface
    if args.cli:
        launch_cli()
    else:
        launch_web(args.port)


if __name__ == '__main__':
    main()
