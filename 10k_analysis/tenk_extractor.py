import re
import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from pathlib import Path

@dataclass
class CompanyInfo:
    """Data class to store extracted company information"""
    company_name: str
    ticker_symbols: List[str]
    cik: Optional[str] = None
    commission_file_number: Optional[str] = None
    exchange: Optional[str] = None

class TenKExtractor:
    """Extract company information from 10-K filings"""
    
    def __init__(self):
        self.session = requests.Session()
        # Set user agent as required by SEC
        self.session.headers.update({
            'User-Agent': 'Your Company Name your.email@domain.com'
        })
    
    def extract_from_text(self, text: str) -> CompanyInfo:
        """Extract company information from 10-K text content"""
        
        # Clean the text
        text = self._clean_text(text)
        
        # Extract company name
        company_name = self._extract_company_name(text)
        
        # Extract ticker symbols
        ticker_symbols = self._extract_ticker_symbols(text)
        
        # Extract additional information
        cik = self._extract_cik(text)
        commission_file = self._extract_commission_file(text)
        exchange = self._extract_exchange(text)
        
        return CompanyInfo(
            company_name=company_name,
            ticker_symbols=ticker_symbols,
            cik=cik,
            commission_file_number=commission_file,
            exchange=exchange
        )
    
    def extract_from_file(self, file_path: str) -> CompanyInfo:
        """Extract company information from a 10-K file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        return self.extract_from_text(content)
    
    def extract_from_url(self, url: str) -> CompanyInfo:
        """Extract company information from a 10-K URL"""
        response = self.session.get(url)
        response.raise_for_status()
        return self.extract_from_text(response.text)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove HTML tags if present
        text = re.sub(r'<[^>]+>', '', text)
        return text
    
    def _extract_company_name(self, text: str) -> str:
        """Extract company name using multiple patterns"""
        
        patterns = [
            # Pattern 1: Direct company name in header
            r'(\w+(?:\s+\w+)*(?:\s+Inc\.?|\s+Corp\.?|\s+Corporation|\s+Company|\s+LLC|\s+Ltd\.?|\s+L\.P\.|\s+LP))\s*\n.*FORM\s+10-K',
            
            # Pattern 2: Registrant name
            r'(?:Exact name of registrant|registrant\'s name).*?:\s*([^\n\r]+?)(?:\s*\n|\s*\()',
            
            # Pattern 3: Company name before address
            r'^([A-Z][A-Za-z\s&.,]+(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?|L\.P\.))(?:\s*\n|\s*\()',
            
            # Pattern 4: In securities table
            r'([\w\s&.,]+(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?|L\.P\.))\s*(?:Class\s+[ABC]|Common Stock)',
            
            # Pattern 5: From title/header area
            r'ANNUAL REPORT.*?\n\s*([A-Z][A-Za-z\s&.,]+(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?|L\.P\.))',
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                company_name = matches.group(1).strip()
                # Clean up the name
                company_name = re.sub(r'\s+', ' ', company_name)
                company_name = company_name.strip('.,();')
                if len(company_name) > 5:  # Basic validation
                    return company_name
        
        # Fallback: Look for any corporation-like entity in first 2000 characters
        first_part = text[:2000]
        fallback_pattern = r'\b([A-Z][A-Za-z\s&.,]{2,50}(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?))\b'
        matches = re.findall(fallback_pattern, first_part)
        if matches:
            return matches[0].strip()
        
        return "Company name not found"
    
    def _extract_ticker_symbols(self, text: str) -> List[str]:
        """Extract ticker symbols from various sections"""
        
        ticker_symbols = []
        
        # Pattern 1: Securities table format
        securities_patterns = [
            r'Trading Symbol(?:\(s\))?\s*Name.*?\n.*?(\w{1,5})\s+',
            r'(\w{1,5})\s+(?:Nasdaq|NYSE|AMEX|OTC)',
            r'Symbol:\s*(\w{1,5})',
            r'ticker\s*symbol[:\s]*(\w{1,5})',
        ]
        
        for pattern in securities_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            ticker_symbols.extend(matches)
        
        # Pattern 2: Look for securities registration table
        securities_section = self._find_securities_section(text)
        if securities_section:
            # Extract from structured table
            table_tickers = self._extract_from_securities_table(securities_section)
            ticker_symbols.extend(table_tickers)
        
        # Pattern 3: Multiple class structures (like Alphabet's GOOGL/GOOG)
        class_patterns = [
            r'Class\s+[ABC]\s+.*?(\w{3,5})',
            r'(\w{3,5})\s+Class\s+[ABC]',
        ]
        
        for pattern in class_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            ticker_symbols.extend(matches)
        
        # Clean and deduplicate
        ticker_symbols = self._clean_ticker_symbols(ticker_symbols)
        
        return ticker_symbols
    
    def _find_securities_section(self, text: str) -> Optional[str]:
        """Find the securities registration section"""
        
        patterns = [
            r'Securities registered pursuant to Section 12\(b\).*?(?=Securities registered pursuant to Section 12\(g\)|ITEM|Note:|$)',
            r'Title of each class.*?Trading Symbol.*?Name of each exchange.*?\n(.*?)(?=\n\s*Securities|\n\s*ITEM|\n\s*Note:)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0) if len(match.groups()) == 0 else match.group(1)
        
        return None
    
    def _extract_from_securities_table(self, table_text: str) -> List[str]:
        """Extract ticker symbols from securities table"""
        
        # Split into lines and look for ticker patterns
        lines = table_text.split('\n')
        tickers = []
        
        for line in lines:
            # Look for 3-5 character symbols that might be tickers
            potential_tickers = re.findall(r'\b([A-Z]{3,5})\b', line)
            for ticker in potential_tickers:
                # Filter out common false positives
                if ticker not in ['NYSE', 'NASDAQ', 'AMEX', 'CLASS', 'STOCK', 'COMMON', 'MARKET']:
                    tickers.append(ticker)
        
        return tickers
    
    def _clean_ticker_symbols(self, ticker_symbols: List[str]) -> List[str]:
        """Clean and validate ticker symbols"""
        
        cleaned = []
        seen = set()
        
        for ticker in ticker_symbols:
            # Basic cleaning
            ticker = ticker.strip().upper()
            
            # Validation rules
            if (len(ticker) >= 1 and len(ticker) <= 5 and 
                ticker.isalpha() and 
                ticker not in seen and
                ticker not in ['NYSE', 'NASDAQ', 'AMEX', 'OTC', 'CLASS', 'STOCK', 'COMMON']):
                
                cleaned.append(ticker)
                seen.add(ticker)
        
        return cleaned
    
    def _extract_cik(self, text: str) -> Optional[str]:
        """Extract CIK number"""
        patterns = [
            r'CIK\s*(?:No\.?)?\s*:?\s*(\d{10})',
            r'Central Index Key\s*:?\s*(\d{10})',
            r'Commission File Number:\s*\d+-(\d{10})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_commission_file(self, text: str) -> Optional[str]:
        """Extract commission file number"""
        pattern = r'Commission file number:\s*([\d-]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _extract_exchange(self, text: str) -> Optional[str]:
        """Extract primary exchange"""
        patterns = [
            r'(Nasdaq Global Select Market)',
            r'(New York Stock Exchange)',
            r'(NYSE)',
            r'(NASDAQ)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

# Usage example and testing functions
def test_extractor():
    """Test the extractor with sample data"""
    
    # Sample text from Alphabet 10-K (simplified)
    sample_text = """
    UNITED STATES SECURITIES AND EXCHANGE COMMISSION
    FORM 10-K
    
    Alphabet Inc.
    (Exact name of registrant as specified in its charter)
    
    Commission file number: 001-37580
    
    Securities registered pursuant to Section 12(b) of the Act:
    Title of each class Trading Symbol(s) Name of each exchange on which registered
    Class A Common Stock, $0.001 par value GOOGL Nasdaq Stock Market LLC
    Class C Capital Stock, $0.001 par value GOOG Nasdaq Stock Market LLC
    """
    
    extractor = TenKExtractor()
    result = extractor.extract_from_text(sample_text)
    
    print("Extraction Results:")
    print(f"Company Name: {result.company_name}")
    print(f"Ticker Symbols: {result.ticker_symbols}")
    print(f"Commission File: {result.commission_file_number}")
    print(f"Exchange: {result.exchange}")

def process_multiple_files(file_paths: List[str]) -> pd.DataFrame:
    """Process multiple 10-K files and return results as DataFrame"""
    
    extractor = TenKExtractor()
    results = []
    
    for file_path in file_paths:
        try:
            result = extractor.extract_from_file(file_path)
            results.append({
                'file_path': file_path,
                'company_name': result.company_name,
                'ticker_symbols': ', '.join(result.ticker_symbols),
                'cik': result.cik,
                'commission_file': result.commission_file_number,
                'exchange': result.exchange
            })
        except Exception as e:
            results.append({
                'file_path': file_path,
                'company_name': f'Error: {str(e)}',
                'ticker_symbols': '',
                'cik': '',
                'commission_file': '',
                'exchange': ''
            })
    
    return pd.DataFrame(results)

if __name__ == "__main__":
    # Run test
    test_extractor()
