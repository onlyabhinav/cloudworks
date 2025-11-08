from flask import Flask, render_template, request, jsonify, send_file, session
import pandas as pd
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import io
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'vulnerability_analysis_secret_key_2025'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Required columns for validation
REQUIRED_COLUMNS = ['IT_Service', 'Hostname', 'Tag_Environment', 'CVE_Description', 'Severity', 'Status']

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

def process_vulnerability_data(df):
    """
    Process vulnerability data grouped by IT Service.
    Returns structured data with unique vulnerabilities and affected hosts.
    """
    # Validate required columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
    
    # Group by IT_Service
    grouped_data = defaultdict(lambda: defaultdict(list))
    
    for _, row in df.iterrows():
        it_service = row['IT_Service']
        # Create unique vulnerability identifier
        vuln_key = f"{row['CVE_Description']}|{row['Severity']}"
        
        # Create host identifier with environment
        host_info = {
            'hostname': row['Hostname'],
            'environment': row['Tag_Environment'],
            'display': f"{row['Hostname']} ({row['Tag_Environment']})",
            'status': row['Status']
        }
        
        # Check if this host is already in the list
        existing_hosts = grouped_data[it_service][vuln_key]
        if not any(h['hostname'] == host_info['hostname'] and h['environment'] == host_info['environment'] 
                   for h in existing_hosts):
            grouped_data[it_service][vuln_key].append(host_info)
    
    # Convert to structured format
    result = {}
    for it_service, vulnerabilities in grouped_data.items():
        result[it_service] = []
        for vuln_key, hosts in vulnerabilities.items():
            vuln_desc, severity = vuln_key.split('|', 1)
            result[it_service].append({
                'cve_description': vuln_desc,
                'severity': severity,
                'affected_hosts': hosts,
                'host_count': len(hosts)
            })
        # Sort by severity (Critical > High > Medium > Low)
        severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
        result[it_service].sort(key=lambda x: severity_order.get(x['severity'], 99))
    
    return result

def calculate_summary_stats(df):
    """Calculate summary statistics for the vulnerability data."""
    stats = {
        'total_vulnerabilities': len(df),
        'unique_services': df['IT_Service'].nunique(),
        'unique_hosts': df['Hostname'].nunique(),
        'severity_breakdown': df['Severity'].value_counts().fillna(0).to_dict(),
        'status_breakdown': df['Status'].value_counts().fillna(0).to_dict(),
        'environment_breakdown': df['Tag_Environment'].value_counts().fillna(0).to_dict(),
        'by_service': {}
    }
    
    # Calculate stats by service
    for service in df['IT_Service'].unique():
        service_df = df[df['IT_Service'] == service]
        stats['by_service'][service] = {
            'total_vulns': len(service_df),
            'unique_hosts': service_df['Hostname'].nunique(),
            'critical': len(service_df[service_df['Severity'] == 'Critical']),
            'high': len(service_df[service_df['Severity'] == 'High']),
            'medium': len(service_df[service_df['Severity'] == 'Medium']),
            'low': len(service_df[service_df['Severity'] == 'Low'])
        }
    
    return stats

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Read and process the CSV
            try:
                df = pd.read_csv(filepath)
                
                # Store data in session
                session['current_file'] = filename
                session['upload_time'] = datetime.now().isoformat()
                
                # Process the data
                grouped_data = process_vulnerability_data(df)
                stats = calculate_summary_stats(df)
                
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'stats': stats,
                    'grouped_data': grouped_data
                })
            except ValueError as ve:
                os.remove(filepath)
                return jsonify({'error': str(ve)}), 400
            except Exception as e:
                os.remove(filepath)
                return jsonify({'error': f'Error processing file: {str(e)}'}), 500
        else:
            return jsonify({'error': 'Invalid file type. Please upload a CSV file.'}), 400
    
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/export/<format>')
def export_data(format):
    try:
        if 'current_file' not in session:
            return jsonify({'error': 'No data to export'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], session['current_file'])
        if not os.path.exists(filepath):
            return jsonify({'error': 'Data file not found'}), 404
        
        df = pd.read_csv(filepath)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'csv':
            output = io.BytesIO()
            df.to_csv(output, index=False)
            output.seek(0)
            return send_file(
                output,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'vulnerability_export_{timestamp}.csv'
            )
        
        elif format == 'json':
            grouped_data = process_vulnerability_data(df)
            stats = calculate_summary_stats(df)
            
            export_data = {
                'export_date': datetime.now().isoformat(),
                'source_file': session['current_file'],
                'summary': stats,
                'data': grouped_data
            }
            
            output = io.BytesIO()
            output.write(json.dumps(export_data, indent=2).encode('utf-8'))
            output.seek(0)
            return send_file(
                output,
                mimetype='application/json',
                as_attachment=True,
                download_name=f'vulnerability_export_{timestamp}.json'
            )
        
        elif format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Sheet 1: Raw Data
                df.to_excel(writer, sheet_name='Vulnerability Data', index=False)
                
                # Sheet 2: Summary Statistics
                stats = calculate_summary_stats(df)
                
                summary_data = []
                summary_data.append(['Summary Statistics', ''])
                summary_data.append(['Total Vulnerabilities', stats['total_vulnerabilities']])
                summary_data.append(['Unique IT Services', stats['unique_services']])
                summary_data.append(['Unique Hosts', stats['unique_hosts']])
                summary_data.append(['', ''])
                summary_data.append(['Severity Breakdown', 'Count'])
                for sev, count in stats['severity_breakdown'].items():
                    summary_data.append([sev, count])
                summary_data.append(['', ''])
                summary_data.append(['Status Breakdown', 'Count'])
                for status, count in stats['status_breakdown'].items():
                    summary_data.append([status, count])
                summary_data.append(['', ''])
                summary_data.append(['Environment Breakdown', 'Count'])
                for env, count in stats['environment_breakdown'].items():
                    summary_data.append([env, count])
                summary_data.append(['', ''])
                summary_data.append(['By IT Service', ''])
                summary_data.append(['Service', 'Total Vulns', 'Unique Hosts', 'Critical', 'High', 'Medium', 'Low'])
                for service, service_stats in stats['by_service'].items():
                    summary_data.append([
                        service,
                        service_stats['total_vulns'],
                        service_stats['unique_hosts'],
                        service_stats['critical'],
                        service_stats['high'],
                        service_stats['medium'],
                        service_stats['low']
                    ])
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False, header=False)
            
            output.seek(0)
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'vulnerability_export_{timestamp}.xlsx'
            )
        
        elif format == 'text':
            grouped_data = process_vulnerability_data(df)
            stats = calculate_summary_stats(df)
            
            output = io.StringIO()
            output.write("=" * 80 + "\n")
            output.write("VULNERABILITY ANALYSIS REPORT\n")
            output.write("=" * 80 + "\n")
            output.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            output.write(f"Source File: {session['current_file']}\n")
            output.write("=" * 80 + "\n\n")
            
            # Summary Statistics
            output.write("SUMMARY STATISTICS\n")
            output.write("-" * 80 + "\n")
            output.write(f"Total Vulnerabilities: {stats['total_vulnerabilities']}\n")
            output.write(f"Unique IT Services: {stats['unique_services']}\n")
            output.write(f"Unique Hosts: {stats['unique_hosts']}\n\n")
            
            output.write("Severity Breakdown:\n")
            for sev, count in stats['severity_breakdown'].items():
                output.write(f"  {sev}: {count}\n")
            
            output.write("\nStatus Breakdown:\n")
            for status, count in stats['status_breakdown'].items():
                output.write(f"  {status}: {count}\n")
            
            output.write("\n" + "=" * 80 + "\n\n")
            
            # Detailed vulnerability data by IT Service
            for service_name in sorted(grouped_data.keys()):
                vulnerabilities = grouped_data[service_name]
                
                output.write(f"IT SERVICE: {service_name}\n")
                output.write("-" * 80 + "\n")
                output.write(f"Total Unique Vulnerabilities: {len(vulnerabilities)}\n")
                output.write(f"Total Affected Hosts: {sum(v['host_count'] for v in vulnerabilities)}\n\n")
                
                for idx, vuln in enumerate(vulnerabilities, 1):
                    output.write(f"{idx}. [{vuln['severity']}] {vuln['cve_description']}\n")
                    output.write(f"   Affected Hosts ({vuln['host_count']}):\n")
                    for host in vuln['affected_hosts']:
                        output.write(f"     - {host['display']} [Status: {host['status']}]\n")
                    output.write("\n")
                
                output.write("=" * 80 + "\n\n")
            
            text_output = io.BytesIO()
            text_output.write(output.getvalue().encode('utf-8'))
            text_output.seek(0)
            return send_file(
                text_output,
                mimetype='text/plain',
                as_attachment=True,
                download_name=f'vulnerability_report_{timestamp}.txt'
            )
        
        else:
            return jsonify({'error': 'Invalid export format'}), 400
    
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
