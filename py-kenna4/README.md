# Vulnerability Analysis Web Application

A Flask-based web application for analyzing and visualizing vulnerability data from Kenna vulnerability scanner, grouped by IT Service.

## Features

### Core Functionality
- **CSV File Upload**: Drag-and-drop interface supporting files up to 100MB
- **Data Grouping**: Automatically groups vulnerabilities by IT Service
- **Smart Deduplication**: Shows unique vulnerabilities with all affected hosts
- **Interactive UI**: Expandable/collapsible service cards for easy navigation

### Data Display
- **Summary Statistics**: Overview cards showing key metrics
- **Tabular Format**: Organized vulnerability listings by IT Service
- **Severity Highlighting**: Color-coded severity levels (Critical, High, Medium, Low)
- **Host Information**: Shows all affected hosts with environment tags

### Export Options
- **CSV Export**: Raw data with all columns preserved
- **JSON Export**: Structured data with summary statistics
- **Excel Export**: Multi-sheet workbook (data + summary)
- **Text Export**: Formatted readable report

### Navigation Features
- Upload New File
- Refresh Data
- Expand/Collapse All Services
- Multiple Export Formats

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Generate sample data (optional):**
```bash
python generate_sample_data.py
```

This creates a `sample_vulnerability_data.csv` file with 500 realistic vulnerability records.

3. **Run the application:**
```bash
python app.py
```

4. **Access the application:**
Open your browser and navigate to:
```
http://localhost:5000
```

## Usage Guide

### Uploading Data

1. **Drag and Drop**: Simply drag your CSV file onto the upload area
2. **Browse**: Click "Browse Files" to select a file from your computer
3. **Wait**: The application will process and display the data automatically

### Required CSV Columns

The application requires these columns:
- `IT_Service`: The service name
- `Hostname`: Server/host identifier
- `Tag_Environment`: Environment tag (Production, Staging, etc.)
- `CVE_Description`: Vulnerability description
- `Severity`: Vulnerability severity level
- `Status`: Current status (Open, In Progress, Closed, etc.)

All other columns are optional but will be preserved in exports.

### Viewing Results

**Summary Statistics** (top of page):
- Total Vulnerabilities
- Number of IT Services
- Unique Hosts
- Critical Issues count

**IT Service Cards**:
- Click on any service header to expand/collapse
- Each card shows:
  - Service name
  - Number of unique vulnerabilities
  - Total affected hosts
  - Detailed vulnerability list with affected hosts

**Vulnerability Details**:
- CVE description
- Severity badge (color-coded)
- List of all affected hosts with environment tags
- Current status for each host

### Exporting Data

Use the navigation bar buttons to export in your preferred format:

1. **CSV**: All original data preserved
2. **JSON**: Structured format with summary statistics
3. **Excel**: Two sheets (Vulnerability Data + Summary)
4. **Text**: Formatted report for easy reading

### Navigation Controls

- **Upload New File**: Clear current data and upload a new file
- **Refresh**: Reload the current data display
- **Expand All**: Open all IT Service cards
- **Collapse All**: Close all IT Service cards

## Data Structure

### Input Format
CSV file with vulnerability scan results from Kenna or similar tools.

### Grouping Logic
1. Groups all vulnerabilities by IT_Service
2. Identifies unique vulnerabilities (no duplicates)
3. For each unique vulnerability, lists ALL affected hosts
4. Displays hosts as: "hostname (environment)"

### Example Output Structure
```
IT Service: Email Service
├── Critical: Apache CVE-2024-1234
│   └── Affected Hosts:
│       ├── mail-server-01 (Production) - Open
│       └── mail-server-02 (Staging) - In Progress
└── High: OpenSSL CVE-2024-5678
    └── Affected Hosts:
        └── mail-server-01 (Production) - Open
```

## File Structure

```
vulnerability-analysis/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── generate_sample_data.py    # Sample data generator
├── templates/
│   └── index.html             # Web interface template
├── uploads/                   # Uploaded CSV files (auto-created)
└── README.md                  # This file
```

## Technical Details

### Dependencies
- **Flask 3.0.0**: Web framework
- **pandas 2.1.4**: Data processing
- **openpyxl 3.1.2**: Excel file generation
- **Werkzeug 3.0.1**: File upload handling

### Supported File Size
- Maximum: 100MB
- Format: CSV only

### Data Processing
- In-memory processing for fast performance
- Session-based data storage
- Automatic validation of required columns

## Troubleshooting

### Missing Columns Error
**Error**: "Missing required columns: ..."

**Solution**: Ensure your CSV file contains all required columns:
- IT_Service
- Hostname
- Tag_Environment
- CVE_Description
- Severity
- Status

### File Size Error
**Error**: "File size exceeds 100MB limit"

**Solution**: Split your CSV file into smaller chunks or increase the limit in `app.py`:
```python
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB
```

### Upload Failed
**Error**: "Upload failed: ..."

**Solution**: 
- Check file format (must be .csv)
- Verify file is not corrupted
- Ensure sufficient disk space
- Check browser console for detailed errors

## Security Notes

- File uploads are stored temporarily in the `uploads/` folder
- Session-based data management (no persistent database)
- Sanitized file names using Werkzeug's `secure_filename`
- File type validation before processing

## Performance

- Handles CSV files up to 100MB
- Processes 500 records in < 1 second
- Efficient grouping using pandas
- Responsive UI with minimal JavaScript

## License

This application is provided as-is for vulnerability analysis purposes.

## Support

For issues or questions:
1. Check this README
2. Review error messages in the browser
3. Check browser console for detailed logs
4. Verify CSV file format and required columns

## Version History

**v1.0.0** (2025-11-08)
- Initial release
- CSV upload with drag-and-drop
- Grouping by IT Service
- Multiple export formats
- Interactive web interface
- Sample data generator
