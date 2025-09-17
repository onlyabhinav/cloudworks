import os
import sys
from dotenv import load_dotenv
from Generic10KIngestionTool import Generic10KIngestionTool

load_dotenv()

def main():
    config = {
        "azure_search_endpoint": os.getenv("AZURE_SEARCH_ENDPOINT"),
        "azure_search_key": os.getenv("AZURE_SEARCH_KEY"),
        "azure_openai_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "azure_openai_key": os.getenv("AZURE_OPENAI_KEY")
    }
    
    tool = Generic10KIngestionTool(**config)
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        print(f"Ingesting {pdf_file}...")
        success = tool.ingest_10k_pdf(pdf_file)
        print(f"Result: {'Success' if success else 'Failed'}")
    else:
        print("Usage: python quick_ingest.py <pdf_filename>")

if __name__ == "__main__":
    main()