"""Tool for querying the structured employee CSV database."""
import pandas as pd
from typing import Any
import os

def load_employees_data() -> pd.DataFrame:
    """Load the employee data from the CSV file.
    
    Returns:
        A pandas DataFrame containing employee records.
    """
    csv_path = os.path.join('data', 'employees.csv')
    return pd.read_csv(csv_path)

