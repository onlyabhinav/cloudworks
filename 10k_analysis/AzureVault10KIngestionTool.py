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

# Azure authentication and services
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, VectorSearch, 
    VectorSearchProfile, HnswAlgorithmConfiguration, SearchField, SearchFieldDataType
)
import openai

@dataclass
class FinancialMetrics:
    """Enhanced data class for financial metrics from 10-K reports"""
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
    
    # Enhanced financial ratios for valuation
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None  # Return on Equity
    roa: Optional[float] = None  # Return on Assets
    revenue_per_employee: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    
    # Valuation metrics (will be calculated based on market data if available)
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    ev_revenue: Optional[float] = None
    ev_ebitda: Optional[float] = None
    price_to_earnings: Optional[float] = None
    price_to_book: Optional[float] = None
    
    def calculate_ratios(self):
        """Calculate financial ratios and valuation metrics from raw data"""
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
            
        if self.total_liabilities and self.shareholders_equity and self.shareholders_equity > 0:
            self.debt_to_equity = self.total_liabilities / self.shareholders_equity
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

class AzureVault10KIngestionTool:
    def __init__(self, 
                 tenant_id: str,
                 client_id: str,
                 client_secret: str,
                 key_vault_url: str,
                 azure_search_endpoint: str,
                 embedding_model: str = "text-embedding-ada-002"):
        
        # Initialize Azure credentials
        self.credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Initialize Key Vault client
        self.key_vault_client = SecretClient(
            vault_url=key_vault_url,
            credential=self.credential
        )
        
        # Retrieve secrets from Key Vault
        self._initialize_services(azure_search_endpoint)
        self.embedding_model = embedding_model
        self.index_name = "financial-reports-index"
        
        # Enhanced industry classification for better comparability
        self.industry_keywords = {
            "Cloud Computing": ["cloud", "saas", "infrastructure", "platform", "serverless"],
            "E-commerce": ["online retail", "marketplace", "e-commerce", "digital commerce", "fulfillment"],
            "Social Media": ["social", "networking", "platform", "user-generated", "advertising"],
            "Streaming/Entertainment": ["streaming", "content", "entertainment", "subscription", "media"],
            "Financial Technology": ["fintech", "payments", "banking", "financial services", "investment"],
            "Healthcare Technology": ["healthcare", "medical", "telemedicine", "pharmaceutical", "biotech"],
            "Energy": ["oil", "gas", "energy", "renewable", "utilities", "solar", "wind"],
            "Automotive": ["automotive", "vehicles", "transportation", "mobility", "electric vehicles"],
            "Retail": ["retail", "consumer goods", "food", "beverage", "apparel"],
            "Aerospace": ["aerospace", "defense", "aviation", "space", "satellite"]
        }
    
    def _initialize_services(self, azure_search_endpoint: str):
        """Initialize Azure services using Key Vault secrets"""
        try:
            # Retrieve secrets from Key Vault
            search_key = self.key_vault_client.get_secret("azure-search-key").value
            openai_endpoint = self.key_vault_client.get_secret("azure-openai-endpoint").value
            openai_key = self.key_vault_client.get_secret("azure-openai-key").value
            
            # Initialize Azure Search
            self.search_client = SearchIndexClient(
                endpoint=azure_search_endpoint,
                credential=AzureKeyCredential(search_key)
            )
            
            # Configure OpenAI
            openai.api_type = "azure"
            openai.api_base = openai_endpoint
            openai.api_key = openai_key
            openai.api_version = "2023-05-15"
            
            print("Successfully initialized Azure services with Key Vault authentication")
            
        except Exception as e:
            print(f"Error initializing services from Key Vault: {e}")
            raise
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Enhanced PDF text extraction with better error handling"""
        text = ""
        
        # Try PyPDF2 first
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as page_error:
                        print(f"Error extracting page {page_num}: {page_error}")
                        continue
        except Exception as e:
            print(f"PyPDF2 extraction failed: {e}")
        
        # Fallback to pdfplumber if needed
        if len(text.strip()) < 1000:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                        except Exception as page_error:
                            print(f"Error extracting page {page_num} with pdfplumber: {page_error}")
                            continue
            except Exception as e:
                print(f"pdfplumber extraction failed: {e}")
        
        return text
    
    def extract_company_info(self, text: str) -> Tuple[str, str]:
        """Enhanced company information extraction"""
        # Improved patterns for company identification
        company_patterns = [
            r'(?:company name|registrant)[:\s]+(.*?)(?:\n|$)',
            r'^(.*?)\s*(?:inc\.?|corp\.?|corporation|company|ltd\.?|llc)',
            r'(?:^|\n)(.*?)\s+form 10-k',
            r'(?:^|\n)(.*?)\s+annual report'
        ]
        
        ticker_patterns = [
            r'(?:trading symbol|ticker symbol|nasdaq|nyse)[:\s]*([A-Z]{1,5})',
            r'common stock.*?symbol[:\s]*([A-Z]{1,5})',
            r'\(([A-Z]{2,5})\)\s*common stock'
        ]
        
        company_name = "Unknown Company"
        ticker = "UNK"
        
        # Extract company name with better cleaning
        text_start = text[:3000]  # Focus on document header
        for pattern in company_patterns:
            matches = re.findall(pattern, text_start, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                clean_name = re.sub(r'[^\w\s&.-]', '', match.strip())
                if len(clean_name) > 3 and not clean_name.isdigit():
                    company_name = clean_name
                    break
            if company_name != "Unknown Company":
                break
        
        # Extract ticker
        for pattern in ticker_patterns:
            match = re.search(pattern, text_start, re.IGNORECASE)
            if match:
                ticker = match.group(1).strip().upper()
                break
        
        return company_name, ticker
    
    def extract_enhanced_financial_metrics(self, text: str, company_name: str, ticker: str) -> FinancialMetrics:
        """Enhanced financial metrics extraction with better patterns"""
        metrics = FinancialMetrics(company_name=company_name, ticker=ticker)
        
        # Industry classification
        industry, sector = self.classify_industry(text)
        metrics.industry = industry
        metrics.sector = sector
        
        # Filing year extraction
        year_patterns = [
            r'(?:fiscal year|year ended).*?december 31,?\s*(\d{4})',
            r'for the year ended.*?(\d{4})',
            r'annual report.*?(\d{4})'
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics.filing_year = int(match.group(1))
                break
        
        # Enhanced financial data extraction
        financial_patterns = {
            'revenue': [
                r'(?:total\s+)?(?:net\s+)?revenues?\s*(?:\(in millions\))?\s*[\$\s]*([\d,]+\.?\d*)',
                r'(?:net\s+)?sales\s*(?:\(in millions\))?\s*[\$\s]*([\d,]+\.?\d*)',
                r'consolidated revenues?\s*[\$\s]*([\d,]+\.?\d*)'
            ],
            'gross_profit': [
                r'gross profit\s*[\$\s]*([\d,]+\.?\d*)',
                r'cost of revenues?\s*[\$\s]*([\d,]+\.?\d*)'  # Will subtract from revenue
            ],
            'operating_income': [
                r'(?:income from operations|operating income)\s*[\$\s]*([\d,]+\.?\d*)',
                r'operating earnings\s*[\$\s]*([\d,]+\.?\d*)'
            ],
            'net_income': [
                r'net (?:income|earnings)\s*[\$\s]*([\d,]+\.?\d*)'
            ],
            'total_assets': [
                r'total assets\s*[\$\s]*([\d,]+\.?\d*)'
            ],
            'total_liabilities': [
                r'total liabilities\s*[\$\s]*([\d,]+\.?\d*)'
            ],
            'shareholders_equity': [
                r'(?:shareholders\'?\s*equity|stockholders\'?\s*equity)\s*[\$\s]*([\d,]+\.?\d*)'
            ],
            'cash_and_equivalents': [
                r'cash and (?:cash equivalents|equivalents)\s*[\$\s]*([\d,]+\.?\d*)'
            ]
        }
        
        # Extract all financial metrics
        for metric_name, patterns in financial_patterns.items():
            value = self._extract_financial_value(text, patterns)
            if value:
                setattr(metrics, metric_name, value)
        
        # Employee count with better patterns
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
        
        # Calculate all ratios and derived metrics
        metrics.calculate_ratios()
        
        return metrics
    
    def _extract_financial_value(self, text: str, patterns: List[str]) -> Optional[float]:
        """Enhanced financial value extraction with better validation"""
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            for match in matches:
                if isinstance(match, tuple):
                    number_str = match[0]
                else:
                    number_str = match
                
                try:
                    # Clean and convert number
                    clean_number = re.sub(r'[^\d.,]', '', number_str)
                    value = float(clean_number.replace(',', ''))
                    
                    # Check if value appears to be in millions (common in 10-K)
                    if 'million' in text[max(0, text.find(number_str) - 100):text.find(number_str) + 100].lower():
                        value *= 1_000_000
                    elif 'billion' in text[max(0, text.find(number_str) - 100):text.find(number_str) + 100].lower():
                        value *= 1_000_000_000
                    
                    # Validate reasonable business values
                    if 1_000 <= value <= 10_000_000_000_000:  # $1K to $10T
                        return value
                        
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def classify_industry(self, text: str) -> Tuple[str, str]:
        """Enhanced industry classification"""
        text_lower = text.lower()
        scores = {}
        
        for industry, keywords in self.industry_keywords.items():
            score = sum(text_lower.count(keyword) for keyword in keywords)
            scores[industry] = score
        
        industry = max(scores, key=scores.get) if max(scores.values()) > 0 else "Other"
        
        # Enhanced sector mapping
        sector_mapping = {
            "Cloud Computing": "Technology",
            "E-commerce": "Consumer Discretionary", 
            "Social Media": "Communication Services",
            "Streaming/Entertainment": "Communication Services",
            "Financial Technology": "Financial Services",
            "Healthcare Technology": "Healthcare",
            "Energy": "Energy",
            "Automotive": "Consumer Discretionary",
            "Retail": "Consumer Staples",
            "Aerospace": "Industrials"
        }
        
        sector = sector_mapping.get(industry, "Other")
        return industry, sector
    
    def create_enhanced_search_index(self):
        """Create enhanced search index with valuation metrics fields"""
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
            
            # Vector field for semantic search
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="vector-profile"
            ),
            
            # Core financial metrics
            SimpleField(name="revenue", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="operating_income", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="net_income", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="total_assets", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="total_liabilities", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="shareholders_equity", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="cash_and_equivalents", type=SearchFieldDataType.Double, 
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
            SimpleField(name="roe", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="roa", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="revenue_per_employee", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="debt_to_equity", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            
            # Valuation metrics (will be populated if market data available)
            SimpleField(name="market_cap", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="enterprise_value", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="ev_revenue", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="ev_ebitda", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            SimpleField(name="price_to_earnings", type=SearchFieldDataType.Double, 
                       filterable=True, sortable=True),
            
            # Metadata
            SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, 
                       filterable=True, sortable=True),
            SimpleField(name="ingestion_timestamp", type=SearchFieldDataType.DateTimeOffset, 
                       filterable=True, sortable=True)
        ]
        
        # Enhanced vector search configuration
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
            # Delete existing index if it exists
            try:
                self.search_client.delete_index(self.index_name)
                print(f"Deleted existing index: {self.index_name}")
            except:
                pass
            
            result = self.search_client.create_index(index)
            print(f"Created enhanced search index: {result.name}")
            return result
            
        except Exception as e:
            print(f"Error creating search index: {e}")
            return None
    
    def chunk_document_by_sections(self, text: str, company_name: str, ticker: str, 
                                 chunk_size: int = 1500, overlap: int = 200) -> List[Dict]:
        """Enhanced document chunking with better section detection"""
        
        section_patterns = [
            (r'ITEM\s+1\.\s+BUSINESS', 'business_overview'),
            (r'ITEM\s+1A\.\s+RISK\s+FACTORS', 'risk_factors'),
            (r'ITEM\s+7\.\s+MANAGEMENT.S\s+DISCUSSION', 'financial_analysis'),
            (r'ITEM\s+8\.\s+FINANCIAL\s+STATEMENTS', 'financial_statements'),
            (r'consolidated\s+balance\s+sheets', 'balance_sheet'),
            (r'consolidated\s+statements\s+of\s+income', 'income_statement'),
            (r'consolidated\s+statements\s+of\s+cash\s+flows', 'cash_flow'),
            (r'(?:revenues?\s+by|segment\s+information)', 'revenue_breakdown'),
            (r'(?:competition|competitive\s+environment)', 'competitive_analysis'),
            (r'(?:products\s+and\s+services)', 'products_services')
        ]
        
        chunks = []
        current_section = 'general'
        
        # Better paragraph splitting
        paragraphs = []
        for paragraph in text.split('\n\n'):
            cleaned = paragraph.strip()
            if cleaned and len(cleaned) > 20:  # Filter out very short paragraphs
                paragraphs.append(cleaned)
        
        current_chunk = ""
        chunk_id = 0
        
        for paragraph in paragraphs:
            # Detect section changes
            for pattern, section_name in section_patterns:
                if re.search(pattern, paragraph, re.IGNORECASE):
                    current_section = section_name
                    break
            
            # Chunk size management
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
                
                # Handle overlap
                if overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-overlap:]
                    current_chunk = overlap_text + "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph
        
        # Final chunk
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
        """Generate embeddings using Azure OpenAI"""
        embeddings = []
        batch_size = 16
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = openai.Embedding.create(
                    input=batch,
                    engine=self.embedding_model
                )
                
                batch_embeddings = [data['embedding'] for data in response['data']]
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                print(f"Error generating embeddings for batch {i//batch_size}: {e}")
                # Fallback: zero embeddings
                embeddings.extend([[0.0] * 1536] * len(batch))
        
        return embeddings
    
    def ingest_10k_pdf(self, pdf_path: str) -> bool:
        """Main ingestion pipeline for 10-K PDF"""
        print(f"Processing 10-K PDF: {pdf_path}")
        
        try:
            # Extract text
            print("Extracting text from PDF...")
            text = self.extract_text_from_pdf(pdf_path)
            
            if len(text.strip()) < 1000:
                print("Warning: Extracted text is very short")
                return False
            
            # Extract company info
            print("Extracting company information...")
            company_name, ticker = self.extract_company_info(text)
            print(f"Company: {company_name} ({ticker})")
            
            # Extract financial metrics
            print("Extracting financial metrics...")
            metrics = self.extract_enhanced_financial_metrics(text, company_name, ticker)
            
            # Display key metrics
            print(f"Key Financial Metrics for {metrics.company_name}:")
            if metrics.revenue:
                print(f"  Revenue: ${metrics.revenue/1_000_000:,.0f}M")
            if metrics.net_income:
                print(f"  Net Income: ${metrics.net_income/1_000_000:,.0f}M")
            if metrics.employees:
                print(f"  Employees: {metrics.employees:,}")
            if metrics.operating_margin:
                print(f"  Operating Margin: {metrics.operating_margin:.1f}%")
            
            # Chunk document
            print("Chunking document...")
            chunks = self.chunk_document_by_sections(text, company_name, ticker)
            print(f"Created {len(chunks)} chunks")
            
            # Generate embeddings
            print("Generating embeddings...")
            chunk_texts = [chunk['content'] for chunk in chunks]
            embeddings = self.generate_embeddings(chunk_texts)
            
            # Prepare documents
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
                
                # Add all financial metrics
                metrics_dict = metrics.to_dict()
                for key, value in metrics_dict.items():
                    if key not in document and value is not None:
                        document[key] = value
                
                documents.append(document)
            
            # Upload to Azure Search
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
                    print(f"Uploaded batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")
                except Exception as e:
                    print(f"Error uploading batch: {e}")
                    return False
            
            print(f"Successfully ingested {company_name}: {len(documents)} chunks indexed")
            return True
            
        except Exception as e:
            print(f"Error in ingestion pipeline: {e}")
            return False
    
    def find_comparable_companies(self, reference_company: str, top_companies: int = 10) -> pd.DataFrame:
        """Enhanced comparable company analysis with valuation metrics"""
        
        search_client = SearchClient(
            endpoint=self.search_client._endpoint,
            index_name=self.index_name,
            credential=self.search_client._credential
        )
        
        try:
            # Get reference company data
            ref_query = f"company_name:{reference_company} OR ticker:{reference_company}"
            ref_results = list(search_client.search(
                search_text=ref_query,
                select="*",
                top=5
            ))
            
            if not ref_results:
                print(f"Reference company '{reference_company}' not found")
                return pd.DataFrame()
            
            ref_company = ref_results[0]
            ref_sector = ref_company.get('sector')
            ref_revenue = ref_company.get('revenue', 0)
            
            print(f"Reference: {ref_company['company_name']} ({ref_company['ticker']})")
            print(f"Sector: {ref_sector}, Revenue: ${ref_revenue/1_000_000:,.0f}M")
            
            # Build filters for comparable companies
            filters = []
            
            if ref_sector:
                filters.append(f"sector eq '{ref_sector}'")
            
            # Similar revenue range (25% to 400% of reference for better comparability)
            if ref_revenue > 0:
                min_revenue = ref_revenue * 0.25
                max_revenue = ref_revenue * 4.0
                filters.append(f"revenue ge {min_revenue} and revenue le {max_revenue}")
            
            # Exclude reference company
            filters.append(f"ticker ne '{ref_company['ticker']}'")
            
            filter_expr = " and ".join(filters)
            
            # Semantic search for comparable companies
            query = f"financial performance metrics valuation {ref_sector} industry analysis"
            
            try:
                query_response = openai.Embedding.create(
                    input=[query],
                    engine=self.embedding_model
                )
                query_embedding = query_response['data'][0]['embedding']
            except Exception as e:
                print(f"Error generating query embedding: {e}")
                query_embedding = [0.0] * 1536
            
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
                select="company_name,ticker,revenue,employees,operating_income,net_income,total_assets,shareholders_equity,gross_margin,operating_margin,net_margin,revenue_per_employee,roe,roa,market_cap,enterprise_value,ev_revenue,ev_ebitda,industry,sector",
                top=100
            )
            
            # Aggregate company data with enhanced valuation metrics
            company_data = {}
            
            for result in results:
                ticker = result.get('ticker')
                if ticker and ticker not in company_data:
                    # Calculate additional valuation metrics
                    revenue = result.get('revenue', 0)
                    net_income = result.get('net_income', 0)
                    market_cap = result.get('market_cap', 0)
                    enterprise_value = result.get('enterprise_value', 0)
                    
                    # Calculate EBITDA approximation (Operating Income + Depreciation estimate)
                    operating_income = result.get('operating_income', 0)
                    ebitda_approx = operating_income * 1.15 if operating_income else 0  # Rough estimate
                    
                    company_data[ticker] = {
                        'Company Name': result.get('company_name', 'N/A'),
                        'Ticker': ticker,
                        'Industry': result.get('industry', 'N/A'),
                        'Revenue ($B)': round(revenue / 1_000_000_000, 2) if revenue else 0,
                        'Employees': f"{result.get('employees', 0):,}" if result.get('employees') else 'N/A',
                        'Market Cap ($B)': round(market_cap / 1_000_000_000, 2) if market_cap else 'N/A',
                        'Enterprise Value ($B)': round(enterprise_value / 1_000_000_000, 2) if enterprise_value else 'N/A',
                        'EV/Revenue': round(enterprise_value / revenue, 1) if enterprise_value and revenue > 0 else 'N/A',
                        'EV/EBITDA': round(enterprise_value / ebitda_approx, 1) if enterprise_value and ebitda_approx > 0 else 'N/A',
                        'Operating Margin (%)': round(result.get('operating_margin', 0), 1) if result.get('operating_margin') else 'N/A',
                        'Net Margin (%)': round(result.get('net_margin', 0), 1) if result.get('net_margin') else 'N/A',
                        'ROE (%)': round(result.get('roe', 0), 1) if result.get('roe') else 'N/A',
                        'Revenue/Employee ($K)': round(result.get('revenue_per_employee', 0) / 1000, 0) if result.get('revenue_per_employee') else 'N/A'
                    }
            
            # Convert to DataFrame and sort by revenue
            df = pd.DataFrame.from_dict(company_data, orient='index')
            if not df.empty:
                df = df.sort_values('Revenue ($B)', ascending=False).head(top_companies)
            
            return df
            
        except Exception as e:
            print(f"Error finding comparable companies: {e}")
            return pd.DataFrame()

# Enhanced configuration and utility classes

class FinancialAnalysisReports:
    """Enhanced analysis and reporting utilities"""
    
    def __init__(self, search_tool: AzureVault10KIngestionTool):
        self.tool = search_tool
    
    def generate_valuation_comparison_table(self, companies: List[str]) -> pd.DataFrame:
        """Generate comprehensive valuation comparison table"""
        
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
                select="*",
                top=1
            ))
            
            if results:
                result = results[0]
                
                # Extract all financial data
                revenue = result.get('revenue', 0)
                net_income = result.get('net_income', 0)
                operating_income = result.get('operating_income', 0)
                total_assets = result.get('total_assets', 0)
                shareholders_equity = result.get('shareholders_equity', 0)
                employees = result.get('employees', 0)
                market_cap = result.get('market_cap', 0)
                enterprise_value = result.get('enterprise_value', 0)
                
                # Calculate derived metrics
                ebitda_approx = operating_income * 1.15 if operating_income else 0
                
                comparison_data.append({
                    'Company Name': result.get('company_name', 'N/A'),
                    'Ticker': result.get('ticker', 'N/A'),
                    'Revenue ($B)': round(revenue / 1_000_000_000, 2) if revenue else 0,
                    'Employees': employees if employees else 0,
                    'Market Cap ($B)': round(market_cap / 1_000_000_000, 2) if market_cap else 'TBD',
                    'Enterprise Value ($B)': round(enterprise_value / 1_000_000_000, 2) if enterprise_value else 'TBD',
                    'EV/Revenue': round(enterprise_value / revenue, 1) if enterprise_value and revenue > 0 else 'TBD',
                    'EV/EBITDA': round(enterprise_value / ebitda_approx, 1) if enterprise_value and ebitda_approx > 0 else 'TBD'
                })
        
        return pd.DataFrame(comparison_data)
    
    def export_analysis_report(self, reference_company: str, output_file: str = None):
        """Export comprehensive analysis report"""
        
        if not output_file:
            output_file = f"{reference_company.replace(' ', '_')}_analysis_report.csv"
        
        # Get comparable companies
        comparable_df = self.tool.find_comparable_companies(reference_company, top_companies=15)
        
        if not comparable_df.empty:
            comparable_df.to_csv(output_file, index=False)
            print(f"Analysis report exported to: {output_file}")
            return output_file
        else:
            print("No data available for export")
            return None

def create_requirements_file():
    """Create requirements.txt for Azure Key Vault version"""
    requirements = """azure-search-documents>=11.4.0
azure-identity>=1.12.0
azure-keyvault-secrets>=4.7.0
openai==0.28.0
PyPDF2>=3.0.0
pdfplumber>=0.9.0
pandas>=1.5.0
numpy>=1.24.0
python-dotenv>=1.0.0"""
    
    with open("requirements.txt", "w") as f:
        f.write(requirements)
    print("Created requirements.txt with Azure Key Vault dependencies")

def create_azure_vault_runner():
    """Create runner script for Azure Key Vault authentication"""
    
    runner_script = '''import os
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
        
        print("\\nProcessing 10-K documents...")
        for pdf_file in pdf_files:
            if os.path.exists(pdf_file):
                print(f"\\nProcessing {pdf_file}...")
                success = tool.ingest_10k_pdf(pdf_file)
                if success:
                    print(f"✓ Successfully ingested {pdf_file}")
                else:
                    print(f"✗ Failed to ingest {pdf_file}")
            else:
                print(f"File not found: {pdf_file}")
        
        # Example analysis: Find companies comparable to Amazon
        print("\\n" + "="*80)
        print("VALUATION ANALYSIS: COMPANIES COMPARABLE TO AMAZON")
        print("="*80)
        
        comparable_df = tool.find_comparable_companies("Amazon", top_companies=10)
        
        if not comparable_df.empty:
            print("\\nValuation Metrics for Companies Comparable to Amazon:")
            print(comparable_df.to_string(index=False))
            
            # Save results
            output_file = "amazon_comparable_companies_valuation.csv"
            comparable_df.to_csv(output_file, index=False)
            print(f"\\nResults saved to: {output_file}")
            
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
'''
    
    with open("run_azure_vault_analysis.py", "w") as f:
        f.write(runner_script)
    print("Created run_azure_vault_analysis.py")

def create_env_template():
    """Create .env template file"""
    
    env_template = """# Azure Authentication Configuration
AZURE_TENANT_ID=your-tenant-id-here
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-here

# Azure Services Configuration
AZURE_KEY_VAULT_URL=https://your-keyvault.vault.azure.net/
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net

# Key Vault Secret Names (these are the names of secrets stored in Key Vault)
# The tool will retrieve these secrets automatically:
# - azure-search-key
# - azure-openai-endpoint  
# - azure-openai-key
"""
    
    with open(".env.template", "w") as f:
        f.write(env_template)
    print("Created .env.template - copy this to .env and fill in your values")

def main():
    """Demo function for Azure Key Vault version"""
    print("Azure Key Vault 10-K Ingestion Tool")
    print("="*50)
    
    # Create helper files
    create_requirements_file()
    create_azure_vault_runner()
    create_env_template()
    
    print("\\nSetup files created:")
    print("1. requirements.txt - Install with: pip install -r requirements.txt")
    print("2. run_azure_vault_analysis.py - Main execution script")
    print("3. .env.template - Copy to .env and configure")
    print("\\nNext steps:")
    print("1. Set up your Azure Key Vault with the required secrets")
    print("2. Configure your .env file with Azure credentials")
    print("3. Run: python run_azure_vault_analysis.py")

if __name__ == "__main__":
    main()