"""
Main entry point for the RAG Customer Support System.
"""
import argparse
import sys
from app.config import Config
from app.utils.logger import setup_logging
from app.services.ingestion_service import IngestionService
from app.services.agent_service import AgentService

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Intelligent RAG Customer Support System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py ingest    # Start Telegram bot for PDF ingestion
  python run.py agent     # Start email support agent
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Ingestion command
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Start the Telegram bot for document ingestion"
    )
    
    # Agent command
    agent_parser = subparsers.add_parser(
        "agent",
        help="Start the AI email support agent"
    )
    agent_parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Email polling interval in seconds (default: 60)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    
    # Execute command
    if args.command == "ingest":
        service = IngestionService()
        service.run()
    elif args.command == "agent":
        service = AgentService()
        service.run(poll_interval=args.poll_interval)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
