import pandas as pd
import random
from datetime import datetime, timedelta

# Configuration
NUM_ROWS = 500  # Number of vulnerability records to generate

# Data pools
IT_SERVICES = [
    'Email Service', 'Web Application', 'Database Service', 'File Storage',
    'Authentication Service', 'API Gateway', 'Payment Gateway', 'CRM System',
    'ERP System', 'Monitoring Service', 'Backup Service', 'VPN Service'
]

HOSTNAMES = [
    'web-server-01', 'web-server-02', 'web-server-03', 'db-server-01', 'db-server-02',
    'api-gateway-01', 'api-gateway-02', 'mail-server-01', 'mail-server-02',
    'file-server-01', 'file-server-02', 'auth-server-01', 'vpn-gateway-01',
    'crm-app-01', 'erp-app-01', 'backup-server-01', 'monitor-server-01',
    'payment-gw-01', 'payment-gw-02', 'storage-node-01', 'storage-node-02'
]

ENVIRONMENTS = ['Production', 'Staging', 'Development', 'UAT', 'QA']

CVE_DESCRIPTIONS = [
    'Apache HTTP Server CVE-2024-1234: Remote Code Execution vulnerability in mod_proxy',
    'OpenSSL CVE-2024-5678: Buffer overflow in SSL/TLS handshake',
    'Microsoft Windows CVE-2024-9012: Privilege escalation in Windows Kernel',
    'Linux Kernel CVE-2024-3456: Local privilege escalation via race condition',
    'PostgreSQL CVE-2024-7890: SQL injection vulnerability in prepared statements',
    'MySQL CVE-2024-2345: Authentication bypass in mysql_native_password',
    'Oracle Java CVE-2024-6789: Remote code execution in Java Serialization',
    'Python CVE-2024-4567: Arbitrary code execution in pickle module',
    'PHP CVE-2024-8901: Remote file inclusion vulnerability',
    'Node.js CVE-2024-1357: Prototype pollution vulnerability',
    'Docker CVE-2024-2468: Container breakout vulnerability',
    'Kubernetes CVE-2024-3579: API server authentication bypass',
    'Nginx CVE-2024-4680: Integer overflow in HTTP/2 implementation',
    'Redis CVE-2024-5791: Unauthorized access to protected memory',
    'MongoDB CVE-2024-6802: NoSQL injection vulnerability',
    'Tomcat CVE-2024-7913: Directory traversal vulnerability',
    'Jenkins CVE-2024-8024: Remote code execution in build scripts',
    'GitLab CVE-2024-9135: Authentication bypass in OAuth implementation',
    'Elasticsearch CVE-2024-0246: Remote code execution via script injection',
    'RabbitMQ CVE-2024-1357: Authentication bypass in management plugin'
]

SEVERITIES = ['Critical', 'High', 'Medium', 'Low']
SEVERITY_WEIGHTS = [0.15, 0.30, 0.35, 0.20]  # Distribution of severities

STATUSES = ['Open', 'In Progress', 'Closed', 'Risk Accepted', 'False Positive']
STATUS_WEIGHTS = [0.40, 0.25, 0.20, 0.10, 0.05]

DEVICE_TYPES = ['Server', 'Virtual Machine', 'Container', 'Network Device']
OS_OPTIONS = ['Windows Server 2019', 'Ubuntu 20.04', 'RHEL 8', 'CentOS 7', 'Debian 11']
REGIONS = ['US-EAST', 'US-WEST', 'EU-CENTRAL', 'ASIA-PACIFIC']
COUNTRIES = ['United States', 'Germany', 'United Kingdom', 'Singapore', 'Japan']

def generate_ip():
    """Generate a random IP address"""
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

def generate_date(days_back_max=180):
    """Generate a random date within the last N days"""
    days_back = random.randint(1, days_back_max)
    return (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

def generate_sample_data(num_rows):
    """Generate sample vulnerability data"""
    
    data = []
    
    for i in range(num_rows):
        hostname = random.choice(HOSTNAMES)
        environment = random.choice(ENVIRONMENTS)
        it_service = random.choice(IT_SERVICES)
        severity = random.choices(SEVERITIES, weights=SEVERITY_WEIGHTS)[0]
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
        cve_desc = random.choice(CVE_DESCRIPTIONS)
        
        # Create due date based on severity
        severity_days = {'Critical': 7, 'High': 30, 'Medium': 60, 'Low': 90}
        found_date = generate_date(90)
        found_datetime = datetime.strptime(found_date, '%Y-%m-%d')
        due_date = (found_datetime + timedelta(days=severity_days[severity])).strftime('%Y-%m-%d')
        
        # Calculate overdue days if status is Open
        if status == 'Open':
            overdue_days = max(0, (datetime.now() - datetime.strptime(due_date, '%Y-%m-%d')).days)
        else:
            overdue_days = 0
        
        row = {
            'Hostname': hostname,
            'Host_Alias': f"{hostname}-alias",
            'Asset_Locator': f"LOC-{random.randint(1000, 9999)}",
            'IP': generate_ip(),
            'Status': status,
            'Source': 'Kenna Security',
            'Port': random.choice([80, 443, 22, 3306, 5432, 8080, 3389]),
            'Tech': random.choice(['Apache', 'Nginx', 'IIS', 'Tomcat', 'Node.js']),
            'Last_Seen': datetime.now().strftime('%Y-%m-%d'),
            'Repeated': random.choice(['Yes', 'No']),
            'Mitigation_Status': status,
            'Mitigation_Date': generate_date(30) if status == 'Closed' else '',
            'Mitigating_Owner': f"owner{random.randint(1, 10)}@company.com",
            'Mitigating_Owner_Sub_Function': random.choice(['Infrastructure', 'Application', 'Security', 'Network']),
            'Mitigating_Action': 'Patch Applied' if status == 'Closed' else 'In Review',
            'Remarks': random.choice(['', 'High priority', 'Scheduled for next cycle', 'Under investigation']),
            'Vul': f"VUL-{random.randint(10000, 99999)}",
            'Patching_Plan': random.choice(['Immediate', 'Next Cycle', 'Scheduled', 'Deferred']),
            'Tag_Device_Type': random.choice(DEVICE_TYPES),
            'Vulnerability': cve_desc.split(':')[0],
            'CVE_Description': cve_desc,
            'Severity': severity,
            'Connector_Source': 'Kenna',
            'Found': found_date,
            'Created': found_date,
            'Asset_OS': random.choice(OS_OPTIONS),
            'Vul_Updated': datetime.now().strftime('%Y-%m-%d'),
            'DMZ': random.choice(['Yes', 'No']),
            'Tag_Environment': environment,
            'Vul_ID': f"V-{random.randint(100000, 999999)}",
            'Asset_ID': f"A-{random.randint(100000, 999999)}",
            'kenna_Vul_ID': f"KV-{random.randint(1000000, 9999999)}",
            'kenna_Asset_ID': f"KA-{random.randint(1000000, 9999999)}",
            'Fix_ID': f"FIX-{random.randint(10000, 99999)}",
            'ITSO_ID': f"ITSO-{random.randint(1000, 9999)}",
            'IT_Service': it_service,
            'ITSO_Delegate': f"delegate{random.randint(1, 5)}@company.com",
            'Service_Owner': f"owner{random.randint(1, 10)}@company.com",
            'PLADA_Criticality': random.choice(['Critical', 'High', 'Medium', 'Low']),
            'GBGF': random.choice(['GB', 'GF', 'N/A']),
            'Service_IT_ORG_6': f"ORG-{random.randint(1, 20)}",
            'Service_IT_ORG_7': f"ORG7-{random.randint(1, 20)}",
            'Service_IT_ORG_8': f"ORG8-{random.randint(1, 20)}",
            'Region': random.choice(REGIONS),
            'Country': random.choice(COUNTRIES),
            'Service_Usage_Region': random.choice(REGIONS),
            'Service_Usage_Country': random.choice(COUNTRIES),
            'Consuming_Country': random.choice(COUNTRIES),
            'Application_Instance_ID': f"APP-{random.randint(1000, 9999)}",
            'Application_Instance_Name': it_service,
            'Citrix': random.choice(['Yes', 'No']),
            'Environment': environment,
            'Asset_Tags': f"tag{random.randint(1, 5)},tag{random.randint(1, 5)}",
            'Details': f"Detailed information about {cve_desc.split(':')[0]}",
            'Solution': random.choice(['Apply patch', 'Update software', 'Configuration change', 'Upgrade version']),
            'Import_Date': datetime.now().strftime('%Y-%m-%d'),
            'Analysis_Status': random.choice(['Analyzed', 'Pending', 'In Review']),
            'Datasource': 'Kenna Vulnerability Scanner',
            'Report_Link': f"https://reports.company.com/vuln/{random.randint(10000, 99999)}",
            'First_Notification': found_date,
            'Due_Date': due_date,
            'Kenna_Due_Date': due_date,
            'Overdue_Days': overdue_days,
            'Modified_By': f"user{random.randint(1, 20)}@company.com",
            'Modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Patch_Available': random.choice(['Yes', 'No', 'Pending']),
            'Patch_Centrally': random.choice(['Yes', 'No']),
            'Patch_Available_Date': generate_date(60) if random.random() > 0.3 else '',
            'Status_Modified_By': f"user{random.randint(1, 20)}@company.com",
            'Scanning_Ids': f"SCAN-{random.randint(100000, 999999)}",
            'Notes': random.choice(['', 'Critical system', 'Requires downtime', 'Test in staging first']),
            'Jira_Ticket': f"VULN-{random.randint(1000, 9999)}" if random.random() > 0.5 else '',
            'Jira_Status': random.choice(['Open', 'In Progress', 'Resolved', 'Closed', '']) if random.random() > 0.5 else '',
            'Asset_Priority': random.choice(['P1', 'P2', 'P3', 'P4']),
            'Previous_Severity': random.choice(SEVERITIES) if random.random() > 0.7 else '',
            'Busapp_ID': f"BA-{random.randint(1000, 9999)}",
            'L1AssetDept': random.choice(['IT', 'Operations', 'Engineering', 'Security']),
            'L2AssetDept': random.choice(['Infrastructure', 'Applications', 'Network', 'Database']),
            'L3AssetDept': random.choice(['Servers', 'Storage', 'Compute', 'Services']),
            'L4AssetDept': random.choice(['Production', 'Non-Production', 'Shared Services']),
            'L5AssetDept': random.choice(['Critical', 'Standard', 'Development']),
            'Category': random.choice(['Software', 'Configuration', 'Missing Patch', 'Zero Day']),
            'Severity_Changed': random.choice(['Yes', 'No']),
            'Vendor_Patch_Available_Date': generate_date(45) if random.random() > 0.4 else '',
            'Iriusrisk_Control_IDs': f"IRC-{random.randint(1000, 9999)},{random.randint(1000, 9999)}"
        }
        
        data.append(row)
    
    return pd.DataFrame(data)

if __name__ == '__main__':
    print("Generating sample vulnerability data...")
    print(f"Number of records: {NUM_ROWS}")
    
    df = generate_sample_data(NUM_ROWS)
    
    # Save to CSV
    output_file = 'sample_vulnerability_data.csv'
    df.to_csv(output_file, index=False)
    
    print(f"\n✅ Sample data generated successfully!")
    print(f"📁 File saved as: {output_file}")
    print(f"\nData Summary:")
    print(f"  - Total rows: {len(df)}")
    print(f"  - IT Services: {df['IT_Service'].nunique()}")
    print(f"  - Unique Hosts: {df['Hostname'].nunique()}")
    print(f"  - Environments: {', '.join(df['Tag_Environment'].unique())}")
    print(f"\nSeverity Distribution:")
    print(df['Severity'].value_counts().to_string())
    print(f"\nStatus Distribution:")
    print(df['Status'].value_counts().to_string())
    print(f"\nYou can now upload this file to the web application!")
