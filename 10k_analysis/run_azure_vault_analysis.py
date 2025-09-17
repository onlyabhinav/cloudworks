import os
from dotenv import load_dotenv
from AzureVault10KIngestionTool import AzureVault10KIngestionTool, FinancialAnalysisReports

# Load environment variables
load_dotenv()

def main():
    """Main execution function with Azure Key Vault authentication"""
    
    # Configuration using Azure Key Vault
    config = {
        "tenant_id": os.getenv("AZURE_TENANT_ID"),
        "client_id": os.getenv("AZURE_CLIENT_ID"), 
        "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
        "key_vault_url": os.getenv("AZURE_KEY_VAULT_URL"),  # e.g., "https://your-keyvault.vault.azure.net/"
        "azure_search_endpoint": os.getenv("AZURE_SEARCH_ENDPOINT")  # e.g., "https://your-search.search.windows.net"
    }
    
    # Validate configuration
    missing_configs = [k for k, v in config.items() if not v]
    if missing_configs:
        print(f"Missing required environment variables: {missing_configs}")
        print("Please set the following in your .env file:")
        print("AZURE_TENANT_ID=your-tenant-id")
        print("AZURE_CLIENT_ID=your-client-id")
        print("AZURE_CLIENT_SECRET=your-client-secret")
        print("AZURE_KEY_VAULT_URL=https://your-keyvault.vault.azure.net/")
        print("AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net")
        return
    
    try:
        # Initialize tool with Key Vault authentication
        print("Initializing Azure services with Key Vault authentication...")
        tool = AzureVault10KIngestionTool(**config)
        
        # Create enhanced search index
        print("Creating enhanced search index...")
        tool.create_enhanced_search_index()
        
        # Process 10-K PDFs
        pdf_files = [
            "10K_SEC_AMAZON.pdf",  # Add your PDF files here
            # "10K_SEC_GOOGLE.pdf",
            # "10K_SEC_MICROSOFT.pdf"
        ]
        
        print("\nProcessing 10-K documents...")
        for pdf_file in pdf_files:
            if os.path.exists(pdf_file):
                print(f"\nProcessing {pdf_file}...")
                success = tool.ingest_10k_pdf(pdf_file)
                if success:
                    print(f"✓ Successfully ingested {pdf_file}")
                else:
                    print(f"✗ Failed to ingest {pdf_file}")
            else:
                print(f"File not found: {pdf_file}")
        
        # Example analysis: Find companies comparable to Amazon
        print("\n" + "="*80)
        print("VALUATION ANALYSIS: COMPANIES COMPARABLE TO AMAZON")
        print("="*80)
        
        comparable_df = tool.find_comparable_companies("Amazon", top_companies=10)
        
        if not comparable_df.empty:
            print("\nValuation Metrics for Companies Comparable to Amazon:")
            print(comparable_df.to_string(index=False))
            
            # Save results
            output_file = "amazon_comparable_companies_valuation.csv"
            comparable_df.to_csv(output_file, index=False)
            print(f"\nResults saved to: {output_file}")
            
            # Generate additional analysis
            analyzer = FinancialAnalysisReports(tool)
            
            # Export comprehensive report
            analyzer.export_analysis_report("Amazon", "amazon_comprehensive_analysis.csv")
            
        else:
            print("No comparable companies found. Please ingest more 10-K documents first.")
        
    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()