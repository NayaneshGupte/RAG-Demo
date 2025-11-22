"""
Telegram ingestion service for processing PDF uploads.
"""
import os
import logging
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import Config
from app.services.vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)

class IngestionService:
    """Service for ingesting documents via Telegram."""
    
    def __init__(self):
        self.vector_store_service = VectorStoreService()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP
        )
    
    def process_pdf(self, file_path, file_name):
        """Process a PDF file: load, split, and upsert to vector store."""
        try:
            # Load PDF
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            logger.info(f"Loaded {len(docs)} pages from {file_name}")

            # Split text
            splits = self.text_splitter.split_documents(docs)
            
            # Filter out empty chunks
            splits = [doc for doc in splits if doc.page_content and doc.page_content.strip()]
            
            logger.info(f"Created {len(splits)} non-empty chunks from {file_name}")

            if not splits:
                logger.warning(f"No valid text chunks found in {file_name}")
                return 0

            # Embed and upsert to Pinecone
            vector_store = self.vector_store_service.get_vector_store()
            vector_store.add_documents(documents=splits)
            
            logger.info(f"Successfully ingested {file_name}")
            return len(splits)
            
        except Exception as e:
            logger.error(f"Error processing file {file_name}: {e}", exc_info=True)
            raise e

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads from Telegram."""
        document = update.message.document
        file_name = document.file_name
        
        if not file_name.lower().endswith('.pdf'):
            await update.message.reply_text("⚠️ Please upload a PDF file.")
            return

        await update.message.reply_text(f"📄 Processing {file_name}...")
        logger.info(f"Received PDF: {file_name}")

        try:
            # Download the file
            file = await context.bot.get_file(document.file_id)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_path = temp_file.name
                await file.download_to_drive(temp_path)
                
            try:
                num_chunks = self.process_pdf(temp_path, file_name)
                
                await update.message.reply_text(
                    f"✅ Successfully ingested {file_name}!\n"
                    f"📊 Created {num_chunks} knowledge chunks."
                )
                
            except Exception as e:
                await update.message.reply_text(f"❌ Error processing file: {str(e)}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            logger.error(f"Error handling document: {e}", exc_info=True)
            await update.message.reply_text("❌ An error occurred while handling the file.")
    
    def run(self):
        """Start the Telegram bot."""
        if not Config.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN not set.")

        application = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        document_handler = MessageHandler(filters.Document.ALL, self.handle_document)
        application.add_handler(document_handler)

        logger.info("🤖 Telegram ingestion bot started")
        print("🤖 Telegram bot is running. Send PDF files to ingest them into the knowledge base.")
        application.run_polling()
