import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

# Load data (assuming the data preparation code is already processed as per the original code)
wage_report_file = 'wage_report_oct_week1-2.xlsx'

# Read the first 10 rows to manually process headers (rows 7-10 are index 6-9 in zero-based indexing)
header_rows = pd.read_excel(wage_report_file, nrows=10)

# Combine rows 7-10 (index 6-9) for headers
combined_header = header_rows.iloc[6:10].fillna(' ').astype(str).agg(' '.join)

# Clean up the combined headers (remove extra spaces)
cleaned_header = combined_header.str.strip().str.replace(r'\s+', ' ', regex=True)

# Read the actual data, skipping the first 7 rows
wage_report_df = pd.read_excel(wage_report_file, skiprows=12, header=None)

# Assign the cleaned headers to the DataFrame
wage_report_df.columns = cleaned_header

# Ensure specific columns are read as strings
string_columns = ['Employee ID', 'Check Number', 'Client ID', 'Invoice Number', 'Parent ID']
wage_report_df[string_columns] = wage_report_df[string_columns].astype(str)

# Columns to keep for further analysis
columns_to_keep = [
    'Employee Name', 'Employee ID', 'Job Title', 'Check Number', 'Classification', 
    'Client Hire Date', 'Client ID', 'Client Name', 'Default Annual Pay', 
    'Default Pay Amount', 'Default Pay Rate', 'Department Name', 'Department Number', 
    'Employee Status', 'Insperity Client Name', 'Insperity Hire Date', 'Job Category', 
    'Job Function', 'Pay Date', 'Pay Frequency', 'Payroll Type', 'Period Begin Date', 
    'Period End Date', 'Supervisor Name', 'TOTALS Net Pay Portion', 
    'Gross Pay Amount', 'Overhead Portion', 'Payroll Cost Amount',
    'Return to Client Ded Portion',
    'Invoice Charges & Fees Portion', 'Amount Due Portion'
]

# Keep only the specified columns
wage_report_important_columns_df = wage_report_df.loc[:, columns_to_keep]

# Remove last 4 rows (likely totals or irrelevant rows)
wage_report_important_columns_df = wage_report_important_columns_df.head(-4)

# Ensure Period End Date is datetime
wage_report_important_columns_df["Period End Date"] = pd.to_datetime(
    wage_report_important_columns_df["Period End Date"], errors="coerce"
)

# Remove rows with invalid Period End Date
wage_report_important_columns_df = wage_report_important_columns_df.dropna(
    subset=["Period End Date"]
)

# Create 'MM/YYYY Pay Only' period column as datetime
wage_report_important_columns_df["MM/YYYY Pay Only"] = wage_report_important_columns_df[
    "Period End Date"
].dt.to_period("M").dt.to_timestamp()

# Filter data by Regular Payroll Type
wage_report_regular_payroll_df = wage_report_important_columns_df[
    wage_report_important_columns_df["Payroll Type"] == "Regular"
]

# Streamlit App

# Title
st.title("Payroll Cost Over Time")

# Sidebar Time Slicer
st.sidebar.header("Filters")

# Add a slider for time slicing
min_date = wage_report_regular_payroll_df["MM/YYYY Pay Only"].min().to_pydatetime().date()
max_date = wage_report_regular_payroll_df["MM/YYYY Pay Only"].max().to_pydatetime().date()

selected_date_range = st.sidebar.slider(
    "Select Date Range",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),  # Default to full range
    format="MMM YYYY",  # Display format
)

# Filter DataFrame by selected date range
filtered_df = wage_report_regular_payroll_df[
    (wage_report_regular_payroll_df["MM/YYYY Pay Only"].dt.date >= selected_date_range[0])
    & (wage_report_regular_payroll_df["MM/YYYY Pay Only"].dt.date <= selected_date_range[1])
]

# Employee Name filter with typing and suggestions
employee_name_input = st.sidebar.multiselect(
    "Search and Select Employee Name(s)",
    options=wage_report_regular_payroll_df["Employee Name"].unique(),
    default=None,
    help="Start typing to see employee name suggestions",
)

# Apply Employee Name filter if any names are selected
if employee_name_input:
    filtered_df = filtered_df[filtered_df["Employee Name"].isin(employee_name_input)]

# Other Filters
job_titles = filtered_df["Job Title"].unique()
job_functions = filtered_df["Job Function"].unique()
job_categories = filtered_df["Job Category"].unique()
insperity_client_name = filtered_df["Insperity Client Name"].unique()

selected_job_title = st.sidebar.selectbox("Select Job Title", options=["All"] + list(job_titles))
selected_job_function = st.sidebar.selectbox("Select Job Function", options=["All"] + list(job_functions))
selected_job_category = st.sidebar.selectbox("Select Job Category", options=["All"] + list(job_categories))
selected_insperity_client_name = st.sidebar.selectbox("Select Insperity Client Name", options=["All"] + list(insperity_client_name))

# Apply additional filters
if selected_job_title != "All":
    filtered_df = filtered_df[filtered_df["Job Title"] == selected_job_title]

if selected_job_function != "All":
    filtered_df = filtered_df[filtered_df["Job Function"] == selected_job_function]

if selected_job_category != "All":
    filtered_df = filtered_df[filtered_df["Job Category"] == selected_job_category]

if selected_insperity_client_name != "All":
    filtered_df = filtered_df[filtered_df["Insperity Client Name"] == selected_insperity_client_name]

# Add a new sidebar filter for selecting the target variable
target_variable_options = [
    'TOTALS Net Pay Portion', 
    'Gross Pay Amount', 'Overhead Portion', 'Payroll Cost Amount',
    'Return to Client Ded Portion',
    'Invoice Charges & Fees Portion', 'Amount Due Portion'
]

selected_target_variable = st.sidebar.selectbox(
    "Select Target Variable for Analysis",
    options=target_variable_options,
    index=3  # Default to 'Payroll Cost Amount'
)

# Compute the average payroll cost for the selected target variable
average_payroll_cost = (
    filtered_df.groupby("MM/YYYY Pay Only")[selected_target_variable]
    .mean()
    .reset_index()
)

# Rename columns for clarity
average_payroll_cost.columns = ["Period", f"Average {selected_target_variable}"]

# Sort by Period
average_payroll_cost = average_payroll_cost.sort_values(by="Period")

# Create a Period Label column for display
average_payroll_cost["Period Label"] = average_payroll_cost["Period"].dt.strftime("%b-%Y")

# Compute the global min and max for the selected target variable
global_min = wage_report_regular_payroll_df[selected_target_variable].min()
global_max = wage_report_regular_payroll_df[selected_target_variable].max()

# Plotting
fig, ax = plt.subplots(figsize=(10, 6))
sns.lineplot(
    data=average_payroll_cost,
    x="Period Label",
    y=f"Average {selected_target_variable}",
    marker="o",
    color="b",
    ax=ax,
)

# Customize plot
ax.set_title(f"Average {selected_target_variable} Over Time")
ax.set_xlabel("Period")
ax.set_ylabel(f"Average {selected_target_variable}")
ax.tick_params(axis="x", rotation=45)

# Set fixed y-axis limits using the global min and max
ax.set_ylim(global_min, global_max)

# Show the plot in the Streamlit app
st.pyplot(fig)






# cd "C:/Users/MasnunAhmedWasi/OneDrive - ALTEA Healthcare/Dashboard Automations/HR Data"

# cd "D:/Personal/OneDrive/ALTEA/Dashboard Automations/HR Data/Wage Change Tracker/"

# streamlit run "streamlit_lessdata_morefilter_w2_wage_change_tracker_20241124_v14.py"
