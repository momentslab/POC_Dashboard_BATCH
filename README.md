# AWS Batch Monitoring Dashboard

A real-time monitoring dashboard for AWS Batch jobs built with Streamlit and DynamoDB.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Modules](#modules)
- [Data Model](#data-model)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [AWS Setup](#aws-setup)

## Overview

This dashboard provides real-time monitoring and visualization of AWS Batch jobs. It connects to a DynamoDB table that stores job state changes captured by EventBridge and processed by a Lambda function.

### Key Features

- Real-time job monitoring with automatic refresh
- Interactive filtering by status, task type, and region
- Detailed job information with full AWS event data
- Statistical overview (success rate, job counts)
- Color-coded status visualization
- Intelligent extraction of Task IDs and Media IDs
- Action simulation (retry, abort, mark as broken)

### Supported Task Types

The dashboard automatically categorizes jobs into the following types:
- **Ingest**: Orchestrator repair ingest jobs
- **Assembly (Zip Package)**: Assembly standard jobs
- **Storage**: Storage jobs
- **Text Recognition**: Text recognition jobs

## Architecture

```
AWS Batch Jobs
    |
    v
EventBridge (Batch Job State Change)
    |
    v
Lambda Function (MonitoringTaskPOC)
    |
    v
DynamoDB Table (MonitoringToolTest)
    |
    v
Streamlit Dashboard (This Application)
```

### AWS Components

1. **EventBridge Rule**: Captures all AWS Batch job state changes
2. **Lambda Function**: Processes events and stores them in DynamoDB
3. **DynamoDB Table**: Centralized storage for job states (latest state only)

### Application Components

- **app.py**: Main Streamlit application
- **dynamo_queries.py**: DynamoDB query module
- **lambda_code_no_history.py**: Lambda function code
- **test_dynamo.py**: Connection testing script
- **setup.sh**: Automated installation script

## Modules

### 1. app.py

Main Streamlit application providing the web interface.

**Key Functions:**

- `load_jobs_from_dynamodb()`: Loads jobs from DynamoDB with 60-second cache
- `extract_queue_name(queue_arn)`: Extracts queue name from ARN
- `extract_job_definition_name(job_def_arn)`: Extracts job definition name from ARN
- `extract_task_id(job_name)`: Extracts MongoDB ObjectID (24 hex characters) from job name
- `format_task_type(queue_name, job_def_name)`: Maps queue/job definition to human-readable task type
- `format_jobs_dataframe(jobs)`: Transforms DynamoDB data into display-ready DataFrame
- `get_job_history(job_id)`: Retrieves complete history for a specific job
- `highlight_status(row)`: Applies conditional formatting based on job status

**Status Color Coding:**

- FAILED: Red background
- SUCCEEDED: Green background
- RUNNING/STARTING/RUNNABLE: Yellow background
- PENDING: Blue background
- SUBMITTED: Purple background
- Others: Gray background

**Displayed Columns:**

1. Media ID
2. Task ID
3. Task Type
4. Status
5. Job ID
6. Job Name
7. Region
8. Timestamp
9. Status Reason

### 2. dynamo_queries.py

DynamoDB query module providing data access layer.

**Class: DynamoDBQueries**

Constructor parameters:
- `table_name` (str): DynamoDB table name (default: 'MonitoringToolTest')
- `region` (str): AWS region (default: 'eu-west-1')

**Methods:**

- `get_all_jobs()`: Retrieves all jobs with automatic pagination handling
- `get_latest_state_per_job()`: Returns only the latest state for each unique job
- `get_failed_jobs()`: Filters jobs with FAILED status
- `get_jobs_by_status(status)`: Filters jobs by specific status
- `get_jobs_by_queue(queue_name)`: Filters jobs by queue name
- `get_jobs_by_time_range(hours)`: Retrieves jobs from the last N hours
- `get_job_history(job_id)`: Retrieves information for a specific job
- `get_statistics()`: Calculates global statistics (total, succeeded, failed, running, success rate)
- `test_connection()`: Tests DynamoDB connection and displays table information

**Pagination Handling:**

All scan operations automatically handle DynamoDB pagination using `LastEvaluatedKey` to ensure complete data retrieval regardless of table size.

### 3. lambda_code_no_history.py

AWS Lambda function code for processing EventBridge events.

**Function: lambda_handler(event, context)**

Processes AWS Batch job state change events and stores them in DynamoDB.

**Event Processing:**

1. Extracts job metadata from EventBridge event
2. Attempts to extract Media ID from multiple sources:
   - Direct event field
   - Job parameters
   - Job tags
   - Job name parsing (MongoDB ObjectID pattern)
3. Stores job state in DynamoDB (overwrites previous state)

**DynamoDB Item Structure:**

```python
{
    'jobId': str,           # Partition key
    'timestamp': str,       # ISO 8601 format
    'jobName': str,
    'status': str,
    'jobQueue': str,        # ARN
    'jobDefinition': str,   # ARN
    'region': str,
    'account': str,
    'statusReason': str,
    'fullEvent': str,       # JSON string of complete event
    'media_id': str         # Optional
}
```

**Note:** This version does not maintain job state history. Each `put_item` operation overwrites the previous state for the same `jobId`.

### 4. test_dynamo.py

Connection testing script to validate AWS credentials and DynamoDB access.

**Test Functions:**

- `test_aws_credentials()`: Validates AWS credentials using STS GetCallerIdentity
- `test_dynamodb_connection()`: Tests connection to DynamoDB table
- `test_data_retrieval()`: Performs sample data queries and displays statistics

**Usage:**

```bash
python3 test_dynamo.py
```

**Output:**

- AWS Account ID and User ARN
- DynamoDB table information
- Sample job data
- Connection status and error messages

### 5. setup.sh

Automated installation and configuration script.

**Features:**

- Validates Python 3 and pip installation
- Installs Python dependencies from requirements.txt
- Checks for AWS CLI installation
- Offers to install AWS CLI via Homebrew
- Configures AWS credentials if not already set
- Runs connection tests via test_dynamo.py

**Usage:**

```bash
chmod +x setup.sh
./setup.sh
```

## Data Model

### DynamoDB Table Structure

**Table Name:** MonitoringToolTest

**Primary Key:**
- Partition Key: `jobId` (String)
- Sort Key: None

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| jobId | String | AWS Batch job ID (Primary Key) |
| timestamp | String | ISO 8601 timestamp of event |
| jobName | String | Full job name |
| status | String | Job status (SUBMITTED, PENDING, RUNNABLE, STARTING, RUNNING, SUCCEEDED, FAILED) |
| jobQueue | String | ARN of the job queue |
| jobDefinition | String | ARN of the job definition |
| region | String | AWS region |
| account | String | AWS account ID |
| statusReason | String | Reason for current status |
| fullEvent | String | Complete EventBridge event as JSON |
| media_id | String | Media identifier (optional) |

**Storage Strategy:**

This implementation uses a single partition key without a sort key. Each job ID maps to exactly one item, which is overwritten on each state change. This approach:

- Reduces storage costs
- Simplifies queries
- Provides only the latest state
- Does not maintain historical state transitions

For historical tracking, see alternative implementations in the migration documentation.

### Job Name Pattern

Job names typically follow this pattern:

```
prefix-TASK_ID-timestamp
```

Example:
```
pre-69490f5fc05fb78da7b7380f-1766395755577
```

Where:
- `pre`: Prefix indicating environment or job type
- `69490f5fc05fb78da7b7380f`: MongoDB ObjectID (24 hex characters) - extracted as Task ID
- `1766395755577`: Unix timestamp in milliseconds

### Queue ARN Format

```
arn:aws:batch:region:account:job-queue/queue-name
```

Example:
```
arn:aws:batch:eu-west-1:388659957718:job-queue/orchestrator-repair-ingest-standard-pre
```

### Job Definition ARN Format

```
arn:aws:batch:region:account:job-definition/name:version
```

Example:
```
arn:aws:batch:eu-west-1:388659957718:job-definition/storage-pre-v2:129
```

## Installation

### Prerequisites

- Python 3.7 or higher
- pip3
- AWS CLI
- AWS credentials with DynamoDB read access

### Quick Start

1. Clone the repository:

```bash
git clone https://github.com/momentslab/POC_Dashboard_BATCH.git
cd POC_Dashboard_BATCH
```

2. Run the setup script:

```bash
chmod +x setup.sh
./setup.sh
```

3. Launch the dashboard:

```bash
streamlit run app.py
```

4. Open your browser to `http://localhost:8501`

### Manual Installation

If you prefer manual installation:

```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Configure AWS credentials
aws configure

# Test DynamoDB connection
python3 test_dynamo.py

# Launch dashboard
streamlit run app.py
```

## Configuration

### DynamoDB Connection

Edit `dynamo_queries.py` to change the default table or region:

```python
def __init__(self, table_name: str = 'MonitoringToolTest', region: str = 'eu-west-1'):
```

### Cache Duration

The dashboard caches DynamoDB queries for 60 seconds. To modify this, edit `app.py`:

```python
@st.cache_data(ttl=60)  # Change TTL value in seconds
def load_jobs_from_dynamodb():
```

### Page Configuration

Modify the Streamlit page configuration in `app.py`:

```python
st.set_page_config(page_title="AWS Batch Monitoring Dashboard", layout="wide")
```

## Usage

### Dashboard Interface

**Header Section:**
- Title and refresh button
- Manual cache clearing

**Filters Section:**
- Status filter (multi-select)
- Task Type filter (multi-select)
- Region filter (multi-select)

**Statistics Section:**
- Total Jobs
- Succeeded Jobs
- Failed Jobs
- Running Jobs
- Success Rate (percentage)

**Jobs Table:**
- Color-coded rows by status
- Sortable columns
- Scrollable view

**Job Details Section:**
- Select a job from dropdown
- View general information
- View technical details
- Expand to see full AWS event JSON

**Actions Section (Simulation):**
- Retry job
- Abort job
- Mark as broken
- Action history log

### Filtering Jobs

Use the multi-select filters to narrow down the displayed jobs:

```
Status: [SUCCEEDED, FAILED, RUNNING, ...]
Task Type: [Ingest, Assembly, Storage, ...]
Region: [eu-west-1, us-east-1, ...]
```

### Refreshing Data

- **Automatic**: Data is cached for 60 seconds
- **Manual**: Click the "Refresh" button to clear cache and reload

### Viewing Job Details

1. Scroll to "Job Details" section
2. Select a job from the dropdown
3. View formatted information
4. Expand "Full AWS Event" to see raw JSON

## AWS Setup

### EventBridge Rule

Create an EventBridge rule to capture Batch job state changes:

**Event Pattern:**

```json
{
  "source": ["aws.batch"],
  "detail-type": ["Batch Job State Change"]
}
```

**Target:** Lambda function (MonitoringTaskPOC)

### Lambda Function

1. Create a new Lambda function
2. Copy code from `lambda_code_no_history.py`
3. Set runtime to Python 3.9 or higher
4. Configure execution role with DynamoDB write permissions
5. Set EventBridge rule as trigger

**Required IAM Permissions:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem"
      ],
      "Resource": "arn:aws:dynamodb:eu-west-1:*:table/MonitoringToolTest"
    }
  ]
}
```

### DynamoDB Table

Create a DynamoDB table with the following configuration:

- **Table name:** MonitoringToolTest
- **Partition key:** jobId (String)
- **Sort key:** None
- **Billing mode:** On-demand or Provisioned (based on usage)
- **Encryption:** AWS owned key or AWS managed key

### IAM Permissions for Dashboard

The AWS credentials used by the dashboard require read access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan",
        "dynamodb:GetItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:eu-west-1:*:table/MonitoringToolTest"
    }
  ]
}
```

## Troubleshooting

### Connection Issues

**Problem:** Cannot connect to DynamoDB

**Solutions:**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check region configuration in `dynamo_queries.py`
- Verify IAM permissions for DynamoDB access
- Ensure table name is correct

### No Data Displayed

**Problem:** Dashboard shows no jobs

**Solutions:**
- Verify EventBridge rule is active
- Check Lambda function logs in CloudWatch
- Confirm jobs are running in AWS Batch
- Verify DynamoDB table contains data: `aws dynamodb scan --table-name MonitoringToolTest --limit 1`

### Import Errors

**Problem:** Module not found errors

**Solutions:**
- Reinstall dependencies: `pip3 install -r requirements.txt`
- Verify Python version: `python3 --version`
- Use virtual environment to avoid conflicts

## License

This project is internal to Moments Lab.

## Support

For issues or questions, contact the development team.


