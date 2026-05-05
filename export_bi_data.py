import pandas as pd
import numpy as np
import json

# Load Data
ac = pd.read_excel("active_customer.xlsx")
statements = pd.read_excel("capexmonthend_accounts_cc.xlsx")
transactions = pd.read_excel("stg_aa_ctransaction_cc_rec_mdl.xlsx")

# 1. Clean Data
active_customers = ac[ac['status'] == 'Active'].copy()
paid_txns = transactions.dropna(subset=['tansaction_remark']).copy()
paid_txns = paid_txns[paid_txns['tansaction_remark'].str.upper().str.startswith('PAYMENT')]
paid_txns = paid_txns.drop_duplicates()

statements['last_billing_date'] = pd.to_datetime(statements['last_billing_date'])
statements['min_amt_due_date'] = pd.to_datetime(statements['min_amt_due_date'])
paid_txns['post_date'] = pd.to_datetime(paid_txns['post_date'])

statements['minimum_amount'] = statements['minimum_amount'].abs()
paid_txns['amount'] = paid_txns['amount'].abs()

# 2. Join Data
active_stmts = pd.merge(statements, active_customers[['customer_account_no']], on='customer_account_no', how='inner')
merged_df = pd.merge(active_stmts, paid_txns, on='customer_account_no', how='left')

# 3. Time Boundary Logic
valid_window = (
    merged_df['post_date'].notna() &
    (merged_df['post_date'] >= merged_df['last_billing_date']) &
    (merged_df['post_date'] <= merged_df['min_amt_due_date'])
)
merged_df['valid_payment_amount'] = np.where(valid_window, merged_df['amount'], 0)

# 4. Aggregation
final_cycle_payments = merged_df.groupby(
    ['customer_account_no', 'last_billing_date', 'min_amt_due_date', 'minimum_amount', 'current_overdue_cycles', 'number_of_days_in_arreas']
)['valid_payment_amount'].sum().reset_index()
final_cycle_payments.rename(columns={'valid_payment_amount': 'total_paid'}, inplace=True)

# 5. Bad Rate Logic
final_cycle_payments['is_bad'] = np.where(
    final_cycle_payments['total_paid'] < final_cycle_payments['minimum_amount'], 1, 0
)
final_cycle_payments['billing_cycle_day'] = final_cycle_payments['last_billing_date'].dt.day

# 6. BI Summaries
total_active = len(final_cycle_payments)
total_bad = int(final_cycle_payments['is_bad'].sum())
global_bad_rate = round((total_bad / total_active) * 100, 2) if total_active > 0 else 0
avg_arrears = round(final_cycle_payments['number_of_days_in_arreas'].mean(), 2)

cycle_summary = final_cycle_payments.groupby('billing_cycle_day').agg(
    total=('customer_account_no', 'count'),
    bad=('is_bad', 'sum')
).reset_index()
cycle_summary['bad_rate'] = round((cycle_summary['bad'] / cycle_summary['total']) * 100, 2)

overdue_summary = final_cycle_payments['current_overdue_cycles'].value_counts().reset_index()
overdue_summary.columns = ['cycles', 'count']
overdue_summary = overdue_summary.sort_values('cycles')

# Convert to dict for JSON
bi_data = {
    "kpis": {
        "totalActive": total_active,
        "totalBad": total_bad,
        "globalBadRate": global_bad_rate,
        "avgArrears": avg_arrears
    },
    "cycleData": {
        "labels": cycle_summary['billing_cycle_day'].astype(str).tolist(),
        "badRate": cycle_summary['bad_rate'].tolist(),
        "totalActive": cycle_summary['total'].tolist(),
        "badCount": cycle_summary['bad'].tolist()
    },
    "overdueData": {
        "labels": overdue_summary['cycles'].astype(str).tolist(),
        "data": overdue_summary['count'].tolist()
    },
    "tableData": json.loads(final_cycle_payments.to_json(orient='records', date_format='iso'))
}

with open("bi_data.json", "w", encoding="utf-8") as f:
    json.dump(bi_data, f, indent=2)

print("BI data exported successfully.")
