import os
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
    
    # Create index
    print("Creating search index...")
    tool.create_search_index()
    
    # Ingest files
    pdf_files = ["10K_SEC_GOOGLE.pdf"]  # Add more as you get them
    
    for pdf_file in pdf_files:
        if os.path.exists(pdf_file):
            success = tool.ingest_10k_pdf(pdf_file)
            print(f"{'✓' if success else '✗'} {pdf_file}")
    
    # Find comparable companies
    results = tool.find_comparable_companies("Google", top_companies=10)
    if not results.empty:
        print("\nComparable Companies to Google:")
        print(results.to_string(index=False))
        results.to_csv("google_comparables.csv", index=False)

if __name__ == "__main__":
    main()