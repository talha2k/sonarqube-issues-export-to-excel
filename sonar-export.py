try:
    import pandas as pd
    import requests
    import base64
    import os
    import argparse
    from datetime import datetime, timedelta
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Run: pip install requests pandas openpyxl python-dotenv")
    exit(1)

#load env file
load_dotenv()

# SonarQube parameters
SONARQUBE_URL = os.getenv("SONAR_URL", "http://localhost:9000/api/issues/search")
PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY", "")
TOKEN = os.getenv("SONAR_TOKEN", "")

# Add basic input validation
if not PROJECT_KEY or not TOKEN:
    print("Error: PROJECT_KEY and TOKEN must be configured")
    exit(1)

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Export SonarQube issues to CSV or Excel format')
parser.add_argument('--format', type=str, choices=['csv', 'xlsx'], default='xlsx',
                    help='Output format: csv or xlsx (default: xlsx)')
args = parser.parse_args()

# Function to write data in chunks to CSV
def write_chunk_to_csv(filename, chunk_data, mode='w'):
    """
    Write a chunk of issue data to a CSV file.

    Parameters:
        filename (str): The path to the output CSV file.
        chunk_data (list): List of issue dictionaries to write.
        mode (str): File write mode, 'w' for write (creates new file), 'a' for append.

    Behavior:
        - Converts chunk_data to a pandas DataFrame.
        - Writes the DataFrame to the specified CSV file.
        - If mode is 'w', includes the header; if 'a', omits the header.
    """
    df = pd.DataFrame(chunk_data)
    # For CSV, we can simply append with or without header
    df.to_csv(filename, index=False, mode=mode, header=(mode == 'w'))

# Function to write data in chunks to Excel
def write_chunk_to_excel(filename, chunk_data, mode='w'):
    df = pd.DataFrame(chunk_data)
    if mode == 'w':
        # First chunk: create new file
        df.to_excel(filename, index=False, engine='openpyxl')
    else:
        # Subsequent chunks: append to existing file without headers
        with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
            # Get the current number of rows
            book = writer.book
            sheet = book.active
            startrow = sheet.max_row
            # Write the new data
            df.to_excel(writer, index=False, header=False, startrow=startrow)

# Fetch issues from SonarQube
auth = base64.b64encode(f'{TOKEN}:'.encode()).decode()
headers = {'Authorization': f'Basic {auth}'}
page_size = 500  # Page size, maximum allowed by SonarQube

# Adjust date ranges as necessary to ensure each range returns less than 10,000 issues
start_date = datetime(2000, 1, 1)  # Example start date
end_date = datetime.now()  # Current date and time
delta = timedelta(days=30)  # Adjust the range to ensure < 10,000 results

current_start_date = start_date
all_issues = []
output_file = f'sonarqube_issues.{args.format}'
chunk_size = 5000  # Write to file every 5000 issues
write_mode = 'w'  # Start with write mode for the first chunk
total_issues_count = 0

# Select the appropriate write function based on format
write_function = write_chunk_to_csv if args.format == 'csv' else write_chunk_to_excel

while current_start_date < end_date:
    current_end_date = current_start_date + delta
    if current_end_date > end_date:
        current_end_date = end_date
        
    print(f"Fetching issues from {current_start_date.strftime('%Y-%m-%d')} to {current_end_date.strftime('%Y-%m-%d')}...")

    params = { #Adjust as required
        'componentKeys': PROJECT_KEY,
        'createdAfter': current_start_date.strftime('%Y-%m-%d'),
        'createdBefore': current_end_date.strftime('%Y-%m-%d'),
        'ps': page_size,
        'p': 1
    }

    while True:
        try:
            response = requests.get(SONARQUBE_URL, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    issues = data.get('issues', [])
                    all_issues.extend(issues)
                    total_issues_count += len(issues)
                    
                    # Write to file in chunks to save memory
                    if len(all_issues) >= chunk_size:
                        print(f"Writing chunk of {len(all_issues)} issues to {args.format.upper()}...")
                        write_function(output_file, all_issues, write_mode)
                        all_issues = []  # Clear memory
                        write_mode = 'a'  # Switch to append mode after first write
                    
                    # Check if there are more pages
                    if len(issues) < page_size:
                        break  # No more pages
                    else:
                        params['p'] += 1  # Next page
                except requests.exceptions.JSONDecodeError as e:
                    print('Failed to parse JSON response:', e)
                    print('Response content:', response.text)
                    break
            else:
                if response.status_code == 401:
                    print('❌ Authentication failed. Check your TOKEN.')
                elif response.status_code == 404:
                    print('❌ Project not found. Check your PROJECT_KEY and SONARQUBE_URL.')
                elif response.status_code == 403:
                    print('❌ Access denied. Check project permissions.')
                else:
                    print(f'❌ API request failed with status {response.status_code}')
                print('Response content:', response.text)
                break
        except requests.exceptions.Timeout:
            print('❌ Connection timed out. Check your network or try again later.')
            break
        except requests.exceptions.ConnectionError:
            print('❌ Connection error. Check your network and SONARQUBE_URL.')
            break
        except Exception as e:
            print(f'❌ Unexpected error occurred: {e}')
            break
            
    current_start_date = current_end_date
    print(f"Found {total_issues_count} issues so far...")

# Handle any remaining issues
if all_issues:
    print(f"Writing final chunk of {len(all_issues)} issues to {args.format.upper()}...")
    write_function(output_file, all_issues, write_mode)

if total_issues_count > 0:
    print(f'✅ Export completed: {total_issues_count} issues exported to {output_file}')
    print(f'📊 Date range: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
else:
    print('No issues found.')
