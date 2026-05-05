# Credit Card Pre-Delinquency Management (PDM) BI Dashboard

## Project Overview
This project is an end-to-end solution I developed to process raw account and transaction data from a bank, visualize payment behaviors, detect early credit delinquency risks, and present actionable metrics via an interactive, real-time web-based Business Intelligence (BI) dashboard.

My primary goal is to accurately classify "Bad Statements" (where a customer paid less than the minimum due within the valid billing window) and aggregate these risks to present a Global Bad Rate along with deep dives into specific billing cycles and overdue buckets.

## Project Structure
- `active_customer.xlsx` – Raw input: Mapping of active accounts.
- `capexmonthend_accounts_cc.xlsx` – Raw input: Statement-level snapshots (Due Dates, Minimum Amounts).
- `stg_aa_ctransaction_cc_rec_mdl.xlsx` – Raw input: Transaction logs.
- `training.ipynb` – The exploratory data analysis (EDA) and methodology prototyping notebook.
- `export_bi_data.py` – The core Python ETL script containing the finalized data pipeline logic that outputs the results to `bi_data.json`.
- `server.py` – A lightweight local Python web server I built to host the UI and execute the ETL pipeline dynamically.
- `dashboard.html` – The interactive, beautifully styled frontend visualizing the data via Chart.js.

## Exploratory Data Analysis (EDA) & Prototyping Methods
Before building the automated ETL script, I rigorously analyzed the raw data in the `training.ipynb` notebook to understand its structure, anomalies, and relationships.

1. **Data Quality Checks**:
   - I examined all datasets for missing values (nulls) and found 92 null values in the `tansaction_remark` column. 
   - I checked for duplicates and identified 12 duplicate transactions, specifically where remarks were null or unverified. I made the decision to drop these duplicate records to prevent double-counting payments that might be logging errors from the bank's collection system.

2. **Data Filtering**:
   - I isolated the active customers (`status == 'Active'`), discovering that 46 out of the 48 accounts were currently active.
   - I filtered the transaction logs to only include valid payments by ensuring the `tansaction_remark` started with the word "PAYMENT". This yielded 57 valid payment transactions.

3. **Data Type Enforcement**:
   - I converted all date columns (`last_billing_date`, `min_amt_due_date`, `post_date`) into explicit pandas datetime objects to prevent logical comparison errors downstream.
   - I converted all financial amounts to absolute values using `.abs()` to handle discrepancies where the bank might log payments as negative amounts.

4. **Relational Joining**:
   - I performed an `inner join` between the statements dataset and the active customers list to instantly filter out statements belonging to closed accounts.
   - I then performed a `left join` of the resulting active statements against the filtered payment transactions on the `customer_account_no`.

5. **Time Boundary Logic (The Window Rule)**:
   - To accurately attribute a payment to a specific billing cycle, I implemented a strict time boundary logic. I validated that the payment `post_date` fell precisely on or after the `last_billing_date` and on or before the `min_amt_due_date`.
   - Any payments falling outside this valid window were zeroed out.

6. **Aggregation & Bad Flag Assignment**:
   - I grouped the valid payments back up to the statement level and summed the total valid payments.
   - Finally, I compared the `total_paid` against the `minimum_amount`. If `total_paid < minimum_amount`, I flagged the statement as `is_bad = 1` (a Bad Statement).

## Key Architecture & Implementation Decisions

### 1. Web Dashboard vs. Native Excel
**Decision:** I built an HTML/JS web dashboard utilizing `Chart.js` with a modern, glassmorphic UI instead of native Excel charts. 
**Reasoning:** Web dashboards provide vastly superior interactivity (hover tooltips, dropdown filtering by cycle), real-time API integrations, and aesthetic flexibility compared to static Excel charts. It provides a much smoother, app-like experience.

### 2. Dedicated Local Web Server (`server.py`)
**Decision:** I included a custom HTTP server built entirely on Python's standard library.
**Reasoning:** I needed a "Run ETL Pipeline" button inside the dashboard to execute the local Python ETL script. Web browsers strictly sandbox static HTML files and prohibit them from executing local shell scripts natively for security reasons. A lightweight Python backend bridges this gap perfectly, exposing a `/run-etl` endpoint to execute the script and asynchronously reload the new data without refreshing the entire page.

### 3. Decoupling Data and UI via JSON
**Decision:** I designed the ETL script to export to `bi_data.json` instead of injecting variables directly into an HTML or `.js` file.
**Reasoning:** This aligns with modern industry standards. The frontend dynamically fetches the JSON payload. When the server runs the ETL pipeline, the data updates on disk, and the frontend smoothly polls the new JSON payload to re-render the charts seamlessly. 

## Installation & Setup

To ensure you don't run into any dependency errors when executing the notebook or the server, please install the required Python packages first.

1. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## How to Run the System

1. **Start the Server:**
   Open a terminal in this directory and execute:
   ```bash
   python server.py
   ```
   *You will see an output confirming: `Serving at http://localhost:8000/dashboard.html`*

2. **Access the Application:**
   Open your preferred web browser and navigate to:
   [http://localhost:8000/dashboard.html](http://localhost:8000/dashboard.html)

3. **Update Data in Real-Time:**
   - Whenever your Excel files are updated with new data drops, simply click the **"Run ETL Pipeline"** button located at the top right of the dashboard.
   - The button will trigger the backend server to process the new data natively using Pandas.
   - You will receive a success notification on the button, and the dashboard charts and tables will automatically refresh with the latest insights instantly!
