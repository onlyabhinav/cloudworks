import os
import re
import json
import hashlib
import PyPDF2
import pdfplumber
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import numpy as np
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, VectorSearch, 
    VectorSearchProfile, HnswAlgorithmConfiguration, SearchField, SearchFieldDataType
)
from openai import AzureOpenAI

@dataclass
class FinancialMetrics:
    """Generic data class for financial metrics from any company's 10-K"""
    company_name: str
    ticker: str
    filing_year: Optional[int] = None
    revenue: Optional[float] = None
    revenue_growth: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    shareholders_equity: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    employees: Optional[int] = None
    industry: Optional[str] = None
    sector: Optional[str] = None
    
    # Calculated ratios
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None  # Return on Equity
    roa: Optional[float] = None  # Return on Assets
    revenue_per_employee: Optional[float] = None
    
    def calculate_ratios(self):
        """Calculate financial ratios from raw metrics"""
        if self.revenue and self.revenue > 0:
            if self.gross_profit:
                self.gross_margin = (self.gross_profit / self.revenue) * 100
            if self.operating_income:
                self.operating_margin = (self.operating_income / self.revenue) * 100
            if self.net_income:
                self.net_margin = (self.net_income / self.revenue) * 100
            if self.employees and self.employees > 0:
                self.revenue_per_employee = self.revenue / self.employees
        
        if self.net_income and self.shareholders_equity and self.shareholders_equity > 0:
            self.roe = (self.net_income / self.shareholders_equity) * 100
            
        if self.net_income and self.total_assets and self.total_assets > 0:
            self.roa = (self.net_income / self.total_assets) * 100
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

class Generic10KIngestionTool:
    def __init__(self, 
                 azure_search_endpoint: str,
                 azure_search_key: str,
                 azure_openai_endpoint: str,
                 azure_openai_key: str,
                 embedding_model: str = "text-embedding-ada-002"):
        
        self.search_client = SearchIndexClient(
            endpoint=azure_search_endpoint,
            credential=AzureKeyCredential(azure_search_key)
        )
        
        self.openai_client = AzureOpenAI(
            azure_endpoint=azure_openai_endpoint,
            api_key=azure_openai_key,
            api_version="2024-02-01"
        )
        
        self.embedding_model = embedding_model
        self.index_name = "financial-reports-index"
        
        # Industry classification keywords
        self.industry_keywords = {
            "Technology": ["software", "cloud", "ai", "artificial intelligence", "digital", "platform"],
            "E-commerce": ["online retail", "marketplace", "e-commerce", "digital commerce"],
            "Financial Services": ["banking", "insurance", "financial services", "investment"],
            "Healthcare": ["pharmaceutical", "medical", "healthcare", "biotech"],
            "Energy": ["oil", "gas", "energy", "renewable", "utilities"],
            "Manufacturing": ["manufacturing", "automotive", "industrial"],
            "Consumer": ["retail", "consumer goods", "food", "beverage"]
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using PyPDF2 and pdfplumber as fallback"""
        
        text = ""
        
        # Try PyPDF2 first
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except:
                        continue
        except Exception as e:
            print(f"PyPDF2 extraction failed: {e}")
        
        # If PyPDF2 fails or produces little text, try pdfplumber
        if len(text.strip()) < 1000:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                        except:
                            continue
            except Exception as e:
                print(f"pdfplumber extraction failed: {e}")
        
        return text
    
    def extract_company_info(self, text: str) -> Tuple[str, str]:
        """Extract company name and ticker from 10-K document"""
        
        # Common patterns for company identification
        company_patterns = [
            r'(.*?)\s*(?:inc\.?|corp\.?|corporation|company|ltd\.?)',
            r'registrant[:\s]+(.*?)(?:\n|$)',
            r'company[:\s]+(.*?)(?:\n|$)'
        ]
        
        ticker_patterns = [
            r'trading symbol[:\s]*([A-Z]{1,5})',
            r'ticker[:\s]*([A-Z]{1,5})',
            r'nasdaq[:\s]*([A-Z]{1,5})',
            r'nyse[:\s]*([A-Z]{1,5})'
        ]
        
        company_name = "Unknown Company"
        ticker = "UNK"
        
        # Extract company name
        for pattern in company_patterns:
            match = re.search(pattern, text[:2000], re.IGNORECASE)
            if match:
                company_name = match.group(1).strip()
                break
        
        # Extract ticker
        for pattern in ticker_patterns:
            match = re.search(pattern, text[:5000], re.IGNORECASE)
            if match:
                ticker = match.group(1).strip()
                break
        
        return company_name, ticker
    
    def classify_industry(self, text: str) -> Tuple[str, str]:
        """Classify company industry based on business description"""
        
        text_lower = text.lower()
        scores = {}
        
        for industry, keywords in self.industry_keywords.items():
            score = sum(text_lower.count(keyword) for keyword in keywords)
            scores[industry] = score
        
        # Get industry with highest score
        industry = max(scores, key=scores.get) if max(scores.values()) > 0 else "Other"
        
        # For sector, use simplified mapping
        sector_mapping = {
            "Technology": "Technology",
            "E-commerce": "Consumer Discretionary",
            "Financial Services": "Financial Services",
            "Healthcare": "Healthcare",
            "Energy": "Energy",
            "Manufacturing": "Industrials",
            "Consumer": "Consumer Staples"
        }
        
        sector = sector_mapping.get(industry, "Other")
        
        return industry, sector
    
    def extract_financial_metrics(self, text: str, company_name: str, ticker: str) -> FinancialMetrics:
        """Extract financial metrics from any company's 10-K"""
        
        metrics = FinancialMetrics(company_name=company_name, ticker=ticker)
        
        # Extract industry classification
        industry, sector = self.classify_industry(text)
        metrics.industry = industry
        metrics.sector = sector
        
        # Extract filing year
        year_patterns = [
            r'(?:fiscal year|year ended).*?december 31,?\s*(\d{4})',
            r'for the year ended.*?(\d{4})',
            r'annual report.*?(\d{4})',
            r'form 10-k.*?(\d{4})'
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics.filing_year = int(match.group(1))
                break
        
        # Revenue extraction patterns
        revenue_patterns = [
            r'(?:total\s+)?(?:net\s+)?revenues?\s*[:\$]*\s*([\d,]+\.?\d*)\s*(million|billion|thousand)?',
            r'(?:net\s+)?sales\s*[:\$]*\s*([\d,]+\.?\d*)\s*(million|billion|thousand)?',
            r'consolidated revenues?\s*[:\$]*\s*([\d,]+\.?\d*)\s*(million|billion|thousand)?'
        ]
        
        metrics.revenue = self._extract_financial_value(text, revenue_patterns)
        
        # Operating income patterns
        operating_patterns = [
            r'(?:income from|operating income)\s*[:\$]*\s*([\d,]+\.?\d*)\s*(million|billion|thousand)?',
            r'operating earnings\s*[:\$]*\s*([\d,]+\.?\d*)\s*(million|billion|thousand)?'
        ]
        
        metrics.operating_income = self._extract_financial_value(text, operating_patterns)
        
        # Net income patterns
        net_income_patterns = [
            r'net (?:income|earnings)\s*[:\$]*\s*([\d,]+\.?\d*)\s*(million|billion|thousand)?'
        ]
        
        metrics.net_income = self._extract_financial_value(text, net_income_patterns)
        
        # Total assets patterns
        assets_patterns = [
            r'total assets\s*[:\$]*\s*([\d,]+\.?\d*)\s*(million|billion|thousand)?'
        ]
        
        metrics.total_assets = self._extract_financial_value(text, assets_patterns)
        
        # Cash patterns
        cash_patterns = [
            r'cash and (?:cash equivalents|equivalents)\s*[:\$]*\s*([\d,]+\.?\d*)\s*(million|billion|thousand)?'
        ]
        
        metrics.cash_and_equivalents = self._extract_financial_value(text, cash_patterns)
        
        # Employee count patterns
        employee_patterns = [
            r'(?:approximately\s+)?(\d{1,3}(?:,\d{3})*)\s+(?:full-time\s+)?employees',
            r'employees?[:\s]*(?:approximately\s+)?(\d{1,3}(?:,\d{3})*)',
            r'workforce\s+of\s+(?:approximately\s+)?(\d{1,3}(?:,\d{3})*)'
        ]
        
        for pattern in employee_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics.employees = int(match.group(1).replace(',', ''))
                break
        
        # Calculate derived metrics
        metrics.calculate_ratios()
        
        return metrics
    
    def _extract_financial_value(self, text: str, patterns: List[str]) -> Optional[float]:
        """Extract financial value using multiple patterns"""
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            for match in matches:
                if isinstance(match, tuple):
                    number_str, scale = match
                else:
                    number_str = match
                    scale = ""
                
                try:
                    value = float(number_str.replace(',', ''))
                    
                    # Apply scale
                    if 'billion' in scale.lower():
                        value *= 1_000_000_000
                    elif 'million' in scale.lower():
                        value *= 1_000_000
                    elif 'thousand' in scale.lower():
                        value *= 1_000
                    
                    # Validation: reasonable business values
                    if 1_000 <= value <= 10_000_000_000_000:  # $1K to $10T
                        return value
                        
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def chunk_document_by_sections(self, text: str, company_name: str, ticker: str, 
                                 chunk_size: int = 1500, overlap: int = 200) -> List[Dict]:
        """Chunk 10-K document by logical sections"""
        
        section_patterns = [
            (r'ITEM\s+1\.\s+BUSINESS', 'business_overview'),
            (r'ITEM\s+1A\.\s+RISK\s+FACTORS', 'risk_factors'),
            (r'ITEM\s+7\.\s+MANAGEMENT.S\s+DISCUSSION', 'financial_analysis'),
            (r'ITEM\s+8\.\s+FINANCIAL\s+STATEMENTS', 'financial_statements'),
            (r'consolidated\s+balance\s+sheets', 'balance_sheet'),
            (r'consolidated\s+statements\s+of\s+income', 'income_statement'),
            (r'(?:revenues?\s+by|segment)', 'revenue_breakdown'),
            (r'(?:competition|competitive)', 'competitive_analysis')
        ]
        
        chunks = []
        current_section = 'general'
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        current_chunk = ""
        chunk_id = 0
        
        for paragraph in paragraphs:
            # Check for section changes
            for pattern, section_name in section_patterns:
                if re.search(pattern, paragraph, re.IGNORECASE):
                    current_section = section_name
                    break
            
            # Manage chunk size
            if len(current_chunk) + len(paragraph) > chunk_size:
                if current_chunk:
                    chunks.append({
                        'id': f"{ticker.lower()}_{chunk_id}",
                        'content': current_chunk.strip(),
                        'section_type': current_section,
                        'chunk_index': chunk_id,
                        'company_name': company_name,
                        'ticker': ticker
                    })
                    chunk_id += 1
                
                # Start new chunk with overlap
                if overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-overlap:]
                    current_chunk = overlap_text + "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                'id': f"{ticker.lower()}_{chunk_id}",
                'content': current_chunk.strip(),
                'section_type': current_section,
                'chunk_index': chunk_id,
                'company_name': company_name,
                'ticker': ticker
            })
        
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings with error handling and batching"""
        
        embeddings = []
        batch_size = 16
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = self.openai_client.embeddings.create(
                    input=batch,
                    model=self.embedding_model
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                print(f"Error generating embeddings for batch {i//batch_size}: {e}")
                embeddings.extend([[0.0] * 1536] * len(batch))
        
        return embeddings
    
    def create_search_index(self):
        """Create comprehensive search index for multiple companies"""
        
        fields = [
            # Core document fields
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="company_name", type=SearchFieldDataType.String, 
                          filterable=True, facetable=True),
            SearchableField(name="ticker", type=SearchFieldDataType.String, 
                          filterable=True, facetable=True),
            SimpleField(name="filing_year", type=SearchFieldDataType.Int32, 
                       filterable=True, sortable=True, facetable=True),
            SearchableField(name="section_type", type=SearchFieldDataType.String, 
                          filterable=True, facetable=True),
            SearchableField(name="industry", type=SearchFieldDataType.String, 
                          filterable=True, facetable=True),
            SearchableField(name="sector", type=SearchFieldDataType.String, 
                          filterable=True, facetable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            
            # Vector field
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="vector-profile"
            ),
            
            # Financial metrics
            SimpleField(name="revenue", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="revenue_growth", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="operating_income", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="net_income", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="total_assets", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="employees", type=SearchFieldDataType.Int64, 
                       filterable=True, sortable=True),
            
            # Financial ratios
            SimpleField(name="gross_margin", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="operating_margin", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="net_margin", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="revenue_per_employee", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            
            # Metadata
            SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, 
                       filterable=True, sortable=True),
            SimpleField(name="ingestion_timestamp", type=SearchFieldDataType.DateTimeOffset, 
                       filterable=True, sortable=True)
        ]
        
        # Vector search configuration
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="vector-profile",
                    algorithm_configuration_name="hnsw-config"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-config",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                )
            ]
        )
        
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search
        )
        
        try:
            # Delete existing index
            try:
                self.search_client.delete_index(self.index_name)
                print(f"Deleted existing index: {self.index_name}")
            except:
                pass
            
            result = self.search_client.create_index(index)
            print(f"Created index: {result.name}")
            return result
            
        except Exception as e:
            print(f"Error creating index: {e}")
            return None
    
    def ingest_10k_pdf(self, pdf_path: str) -> bool:
        """Generic pipeline to ingest any company's 10-K PDF"""
        
        print(f"Processing 10-K PDF: {pdf_path}")
        
        try:
            # Step 1: Extract text from PDF
            print("Extracting text from PDF...")
            text = self.extract_text_from_pdf(pdf_path)
            
            if len(text.strip()) < 1000:
                print("Warning: Extracted text is very short. PDF may be image-based or corrupted.")
                return False
            
            # Step 2: Extract company information
            print("Extracting company information...")
            company_name, ticker = self.extract_company_info(text)
            print(f"Company: {company_name} ({ticker})")
            
            # Step 3: Extract financial metrics
            print("Extracting financial metrics...")
            metrics = self.extract_financial_metrics(text, company_name, ticker)
            print(f"Extracted metrics for {metrics.company_name}")
            print(f"  Revenue: ${metrics.revenue:,.0f}" if metrics.revenue else "  Revenue: Not found")
            print(f"  Employees: {metrics.employees:,}" if metrics.employees else "  Employees: Not found")
            
            # Step 4: Chunk document
            print("Chunking document...")
            chunks = self.chunk_document_by_sections(text, company_name, ticker)
            print(f"Created {len(chunks)} chunks")
            
            # Step 5: Generate embeddings
            print("Generating embeddings...")
            chunk_texts = [chunk['content'] for chunk in chunks]
            embeddings = self.generate_embeddings(chunk_texts)
            
            # Step 6: Prepare documents for indexing
            print("Preparing documents for indexing...")
            documents = []
            ingestion_time = datetime.utcnow().isoformat() + "Z"
            
            for chunk, embedding in zip(chunks, embeddings):
                document = {
                    "id": chunk['id'],
                    "company_name": chunk['company_name'],
                    "ticker": chunk['ticker'],
                    "section_type": chunk['section_type'],
                    "content": chunk['content'],
                    "content_vector": embedding,
                    "chunk_index": chunk['chunk_index'],
                    "ingestion_timestamp": ingestion_time
                }
                
                # Add financial metrics
                metrics_dict = metrics.to_dict()
                for key, value in metrics_dict.items():
                    if key not in document and value is not None:
                        document[key] = value
                
                documents.append(document)
            
            # Step 7: Upload to Azure Search
            print("Uploading to Azure Search...")
            search_client = SearchClient(
                endpoint=self.search_client._endpoint,
                index_name=self.index_name,
                credential=self.search_client._credential
            )
            
            batch_size = 50
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                try:
                    search_client.upload_documents(batch)
                    print(f"Uploaded batch {i//batch_size + 1}")
                except Exception as e:
                    print(f"Error uploading batch: {e}")
                    return False
            
            print(f"Successfully ingested {company_name}: {len(documents)} chunks indexed")
            return True
            
        except Exception as e:
            print(f"Error in ingestion pipeline: {e}")
            return False
    
    def find_comparable_companies(self, reference_company: str, top_companies: int = 10) -> pd.DataFrame:
        """Find companies comparable to the reference company and return valuation metrics"""
        
        search_client = SearchClient(
            endpoint=self.search_client._endpoint,
            index_name=self.index_name,
            credential=self.search_client._credential
        )
        
        try:
            # Step 1: Get reference company info
            ref_query = f"company_name:{reference_company} OR ticker:{reference_company}"
            ref_results = list(search_client.search(
                search_text=ref_query,
                select="company_name,ticker,sector,industry,revenue,employees",
                top=5
            ))
            
            if not ref_results:
                print(f"Reference company '{reference_company}' not found in index")
                return pd.DataFrame()
            
            ref_company = ref_results[0]
            ref_sector = ref_company.get('sector')
            ref_revenue = ref_company.get('revenue', 0)
            ref_employees = ref_company.get('employees', 0)
            
            print(f"Reference company: {ref_company['company_name']} ({ref_company['ticker']})")
            print(f"Sector: {ref_sector}, Revenue: ${ref_revenue:,.0f}")
            
            # Step 2: Build similarity filters
            filters = []
            
            # Same sector companies
            if ref_sector:
                filters.append(f"sector eq '{ref_sector}'")
            
            # Similar revenue range (50% to 200% of reference)
            if ref_revenue > 0:
                min_revenue = ref_revenue * 0.5
                max_revenue = ref_revenue * 2.0
                filters.append(f"revenue ge {min_revenue} and revenue le {max_revenue}")
            
            # Exclude reference company
            filters.append(f"ticker ne '{ref_company['ticker']}'")
            
            filter_expr = " and ".join(filters)
            
            # Step 3: Search for comparable companies
            query = f"valuation metrics financial performance {ref_sector} companies"
            
            # Generate query embedding for semantic similarity
            query_embedding = self.generate_embeddings([query])[0]
            
            results = search_client.search(
                search_text=query,
                vector_queries=[
                    VectorizedQuery(
                        vector=query_embedding,
                        k_nearest_neighbors=50,
                        fields="content_vector"
                    )
                ],
                filter=filter_expr,
                select="company_name,ticker,revenue,employees,operating_income,net_income,total_assets,gross_margin,operating_margin,net_margin,revenue_per_employee,industry,sector",
                top=100
            )
            
            # Step 4: Aggregate by company and create comparison table
            company_data = {}
            
            for result in results:
                ticker = result.get('ticker')
                if ticker and ticker not in company_data:
                    company_data[ticker] = {
                        'Company Name': result.get('company_name', 'N/A'),
                        'Ticker': ticker,
                        'Industry': result.get('industry', 'N/A'),
                        'Sector': result.get('sector', 'N/A'),
                        'Revenue ($B)': round(result.get('revenue', 0) / 1_000_000_000, 2) if result.get('revenue') else 0,
                        'Employees': f"{result.get('employees', 0):,}" if result.get('employees') else '0',
                        'Operating Income ($B)': round(result.get('operating_income', 0) / 1_000_000_000, 2) if result.get('operating_income') else 0,
                        'Net Income ($B)': round(result.get('net_income', 0) / 1_000_000_000, 2) if result.get('net_income') else 0,
                        'Gross Margin (%)': round(result.get('gross_margin', 0), 1) if result.get('gross_margin') else 0,
                        'Operating Margin (%)': round(result.get('operating_margin', 0), 1) if result.get('operating_margin') else 0,
                        'Net Margin (%)': round(result.get('net_margin', 0), 1) if result.get('net_margin') else 0,
                        'Revenue/Employee ($K)': round(result.get('revenue_per_employee', 0) / 1000, 0) if result.get('revenue_per_employee') else 0
                    }
            
            # Convert to DataFrame and sort by revenue
            df = pd.DataFrame.from_dict(company_data, orient='index')
            df = df.sort_values('Revenue ($B)', ascending=False).head(top_companies)
            
            return df
            
        except Exception as e:
            print(f"Error finding comparable companies: {e}")
            return pd.DataFrame()

# Usage Example and Demo
def main():
    """Demo of the generic 10-K ingestion tool"""
    
    # Configuration
    config = {
        "azure_search_endpoint": "https://your-search-service.search.windows.net",
        "azure_search_key": "your-search-admin-key",
        "azure_openai_endpoint": "https://your-openai.openai.azure.com",
        "azure_openai_key": "your-openai-key"
    }
    
    # Initialize the tool
    tool = Generic10KIngestionTool(**config)
    
    # Create search index
    print("Creating search index...")
    tool.create_search_index()
    
    # Ingest multiple 10-K PDFs
    pdf_files = [
        "10K_SEC_GOOGLE.pdf",
        "10K_SEC_MICROSOFT.pdf", 
        "10K_SEC_AMAZON.pdf",
        # Add more PDF files as needed
    ]
    
    print("\nIngesting 10-K documents...")
    for pdf_file in pdf_files:
        if os.path.exists(pdf_file):
            success = tool.ingest_10k_pdf(pdf_file)
            if success:
                print(f"✓ Successfully ingested {pdf_file}")
            else:
                print(f"✗ Failed to ingest {pdf_file}")
        else:
            print(f"File not found: {pdf_file}")
    
    # Demo: Find companies comparable to Google
    print("\n" + "="*80)
    print("FINDING COMPANIES COMPARABLE TO GOOGLE")
    print("="*80)
    
    comparable_df = tool.find_comparable_companies("Google", top_companies=10)
    
    if not comparable_df.empty:
        print("\nValuation Metrics for Companies Comparable to Google:")
        print(comparable_df.to_string(index=False))
        
        # Save to CSV
        comparable_df.to_csv("google_comparable_companies.csv", index=False)
        print(f"\nResults saved to: google_comparable_companies.csv")
    else:
        print("No comparable companies found.")

class FinancialAnalysisReports:
    """Additional utility class for generating analysis reports"""
    
    def __init__(self, search_tool: Generic10KIngestionTool):
        self.tool = search_tool
    
    def generate_company_analysis(self, company_name: str) -> Dict[str, Any]:
        """Generate comprehensive analysis for a specific company"""
        
        search_client = SearchClient(
            endpoint=self.tool.search_client._endpoint,
            index_name=self.tool.index_name,
            credential=self.tool.search_client._credential
        )
        
        # Search for company data
        query = f"company_name:{company_name}"
        results = list(search_client.search(
            search_text=query,
            select="*",
            top=50
        ))
        
        if not results:
            return {"error": f"Company '{company_name}' not found"}
        
        # Aggregate company data
        company_data = results[0]  # Get first result for basic info
        
        # Find key business insights
        business_sections = [r for r in results if r.get('section_type') == 'business_overview']
        risk_sections = [r for r in results if r.get('section_type') == 'risk_factors']
        financial_sections = [r for r in results if r.get('section_type') == 'financial_analysis']
        
        analysis = {
            "company_overview": {
                "name": company_data.get('company_name'),
                "ticker": company_data.get('ticker'),
                "industry": company_data.get('industry'),
                "sector": company_data.get('sector'),
                "filing_year": company_data.get('filing_year')
            },
            "financial_metrics": {
                "revenue_billions": round(company_data.get('revenue', 0) / 1_000_000_000, 2),
                "operating_income_billions": round(company_data.get('operating_income', 0) / 1_000_000_000, 2),
                "net_income_billions": round(company_data.get('net_income', 0) / 1_000_000_000, 2),
                "employees": company_data.get('employees'),
                "gross_margin_percent": company_data.get('gross_margin'),
                "operating_margin_percent": company_data.get('operating_margin'),
                "net_margin_percent": company_data.get('net_margin'),
                "revenue_per_employee": company_data.get('revenue_per_employee')
            },
            "business_highlights": [section.get('content', '')[:200] + "..." for section in business_sections[:3]],
            "key_risks": [section.get('content', '')[:200] + "..." for section in risk_sections[:3]],
            "financial_analysis": [section.get('content', '')[:200] + "..." for section in financial_sections[:2]]
        }
        
        return analysis
    
    def compare_financial_metrics(self, companies: List[str]) -> pd.DataFrame:
        """Compare key financial metrics across multiple companies"""
        
        search_client = SearchClient(
            endpoint=self.tool.search_client._endpoint,
            index_name=self.tool.index_name,
            credential=self.tool.search_client._credential
        )
        
        comparison_data = []
        
        for company in companies:
            query = f"company_name:{company} OR ticker:{company}"
            results = list(search_client.search(
                search_text=query,
                select="company_name,ticker,revenue,employees,operating_income,net_income,gross_margin,operating_margin,net_margin",
                top=1
            ))
            
            if results:
                result = results[0]
                comparison_data.append({
                    "Company": result.get('company_name', 'N/A'),
                    "Ticker": result.get('ticker', 'N/A'),
                    "Revenue ($B)": round(result.get('revenue', 0) / 1_000_000_000, 2),
                    "Operating Income ($B)": round(result.get('operating_income', 0) / 1_000_000_000, 2),
                    "Net Income ($B)": round(result.get('net_income', 0) / 1_000_000_000, 2),
                    "Employees": f"{result.get('employees', 0):,}",
                    "Gross Margin (%)": round(result.get('gross_margin', 0), 1),
                    "Operating Margin (%)": round(result.get('operating_margin', 0), 1),
                    "Net Margin (%)": round(result.get('net_margin', 0), 1)
                })
        
        return pd.DataFrame(comparison_data)

# Enhanced usage example with batch processing
def batch_process_10k_documents(tool: Generic10KIngestionTool, pdf_directory: str):
    """Process all 10-K PDFs in a directory"""
    
    if not os.path.exists(pdf_directory):
        print(f"Directory not found: {pdf_directory}")
        return
    
    pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_directory}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    success_count = 0
    failed_files = []
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_directory, pdf_file)
        print(f"\nProcessing: {pdf_file}")
        
        try:
            success = tool.ingest_10k_pdf(pdf_path)
            if success:
                success_count += 1
                print(f"✓ Successfully processed {pdf_file}")
            else:
                failed_files.append(pdf_file)
                print(f"✗ Failed to process {pdf_file}")
        except Exception as e:
            failed_files.append(pdf_file)
            print(f"✗ Error processing {pdf_file}: {e}")
    
    print(f"\n" + "="*60)
    print(f"BATCH PROCESSING SUMMARY")
    print(f"="*60)
    print(f"Total files: {len(pdf_files)}")
    print(f"Successfully processed: {success_count}")
    print(f"Failed: {len(failed_files)}")
    
    if failed_files:
        print(f"\nFailed files:")
        for file in failed_files:
            print(f"  - {file}")

def interactive_search_demo(tool: Generic10KIngestionTool):
    """Interactive demo for searching comparable companies"""
    
    print("\n" + "="*80)
    print("INTERACTIVE COMPARABLE COMPANY SEARCH")
    print("="*80)
    
    while True:
        reference_company = input("\nEnter company name or ticker (or 'quit' to exit): ").strip()
        
        if reference_company.lower() in ['quit', 'exit', 'q']:
            break
        
        if not reference_company:
            continue
        
        try:
            print(f"\nSearching for companies comparable to {reference_company}...")
            comparable_df = tool.find_comparable_companies(reference_company, top_companies=8)
            
            if not comparable_df.empty:
                print(f"\nValuation Metrics - Companies Comparable to {reference_company}:")
                print("-" * 120)
                print(comparable_df.to_string(index=False))
                
                # Option to save results
                save = input(f"\nSave results to CSV? (y/n): ").strip().lower()
                if save == 'y':
                    filename = f"{reference_company.lower().replace(' ', '_')}_comparable_companies.csv"
                    comparable_df.to_csv(filename, index=False)
                    print(f"Results saved to: {filename}")
            else:
                print(f"No comparable companies found for '{reference_company}'")
                print("Make sure the company has been ingested into the system.")
        
        except Exception as e:
            print(f"Error during search: {e}")

# Complete example with all features
if __name__ == "__main__":
    main()
    
    # Additional examples
    config = {
        "azure_search_endpoint": "https://your-search-service.search.windows.net",
        "azure_search_key": "your-search-admin-key",
        "azure_openai_endpoint": "https://your-openai.openai.azure.com",
        "azure_openai_key": "your-openai-key"
    }
    
    tool = Generic10KIngestionTool(**config)
    
    # Example 1: Batch process PDFs from a directory
    # batch_process_10k_documents(tool, "./10k_pdfs")
    
    # Example 2: Interactive search
    # interactive_search_demo(tool)
    
    # Example 3: Generate detailed company analysis
    # analysis = FinancialAnalysisReports(tool)
    # google_analysis = analysis.generate_company_analysis("Alphabet")
    # print(json.dumps(google_analysis, indent=2))
    
    # Example 4: Direct comparison of specific companies
    # comparison_df = analysis.compare_financial_metrics(["Google", "Microsoft", "Amazon"])
    # print(comparison_df.to_string(index=False))