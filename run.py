"""
Main entry point for the RAG Customer Support System.
"""
import argparse
import sys
from app.config import Config
from app.utils.logger import setup_logging
from app.services.agent_service import AgentService

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Intelligent RAG Customer Support System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py agent     # Start email support agent
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
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
    if args.command == "agent":
        # Email Support Agent
        # Create app context to ensure services are initialized correctly if they depend on app config
        from app import create_app
        app = create_app()
        
        with app.app_context():
            agent = AgentService()
            print(f"Starting AI Support Agent (Poll Interval: {args.poll_interval}s)...")
            agent.run(poll_interval=args.poll_interval)
            
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
