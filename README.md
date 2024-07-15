
# SonarQube to Excel Export

This Python script fetches issues from a SonarQube project and exports them to an Excel file. It uses the SonarQube REST API and handles pagination and date ranges to ensure all issues are retrieved.

## Prerequisites

- Python 3.x
- `requests`, `pandas`, `openpyxl` library
- Access to a SonarQube instance with an appropriate token

## Installation

1. Clone the repository:

```bash
git clone https://github.com/talha2k/sonarqube-issues-export-to-excel.git
cd sonarqube-issues-export-to-excel
```

2. Install the required Python libraries:

```bash
pip install requests pandas openpyxl
```

## Usage

1. Update the `SONARQUBE_URL`, `PROJECT_KEY`, and `TOKEN` variables in the script with your SonarQube instance details.

2. Run the script:

```bash
python sonar-export.py
```

3. The script will fetch the issues and save them to an Excel file named `sonarqube_issues.xlsx`.

## Script Explanation

- The script uses the `requests` library to fetch issues from SonarQube's REST API.
- It handles pagination to fetch all issues.
- The issues are stored in a pandas DataFrame and then exported to an Excel file.

## Example

Here is an example of how to use the script:

```python
import pandas as pd
import requests
import base64
from datetime import datetime, timedelta

# SonarQube parameters
SONARQUBE_URL = 'http://localhost:9000/api/issues/search' #Sonar Instance URL
PROJECT_KEY = '' #Your Project Key
TOKEN = '' #Your Project Token

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

while current_start_date < end_date:
    current_end_date = current_start_date + delta
    if current_end_date > end_date:
        current_end_date = end_date

    params = { #Ajdust as required
        'componentKeys': PROJECT_KEY,
        'createdAfter': current_start_date.strftime('%Y-%m-%d'),
        'createdBefore': current_end_date.strftime('%Y-%m-%d'),
        'ps': page_size,
        'p': 1
    }

    while True:
        response = requests.get(SONARQUBE_URL, headers=headers, params=params)
        
        if response.status_code == 200:
            try:
                data = response.json()
                issues = data.get('issues', [])
                all_issues.extend(issues)
                
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
            print(f'Failed to fetch issues. Status code: {response.status_code}')
            print('Response content:', response.text)
            break

    current_start_date = current_end_date

if all_issues:
    # Convert to DataFrame
    df = pd.DataFrame(all_issues)
    # Save to Excel
    df.to_excel('sonarqube_issues.xlsx', index=False)
    print('Issues exported to sonarqube_issues.xlsx')
else:
    print('No issues found.')
```

## License

This project is licensed under the MIT License.
