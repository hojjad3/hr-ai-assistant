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

def query_employee_data(employee_id: str | None=None, fields: list[str] | None=None, filters: dict[str, Any] | None=None, aggregate: str | None=None, aggregate_field: str | None=None) -> dict[str, Any] | str | list[dict[str, Any]] | int | float:
    """Look up employee data, supporting single lookups, filtering, and aggregation.

    Args:
        employee_id: Specific employee ID to look up (optional).
        fields: Specific fields to return (optional).
        filters: Dictionary of column names and exact values to filter by (optional).
        aggregate: Type of aggregation to perform ('count', 'max', 'list') (optional).
        aggregate_field: The column name to apply the max aggregation on (optional).

    Returns:
        The requested data, count, or aggregated result.
    """
    df = load_employees_data()
    if filters:
        for k, v in filters.items():
            if k in df.columns:
                if isinstance(v, str) and (v.startswith('>=') or v.startswith('<=') or v.startswith('>') or v.startswith('<')):
                    op_str = v[:2] if v[1] == '=' else v[:1]
                    val_str = v[len(op_str):].strip()
                    try:
                        val = float(val_str)
                        if op_str == '>=':
                            df = df[df[k] >= val]
                        elif op_str == '<=':
                            df = df[df[k] <= val]
                        elif op_str == '>':
                            df = df[df[k] > val]
                        elif op_str == '<':
                            df = df[df[k] < val]
                    except ValueError:
                        df = df[df[k] == v]
                else:
                    df = df[df[k] == v]
    if employee_id:
        df = df[df['employee_id'] == employee_id]
    if df.empty:
        return 'No matching employees found.'
    if aggregate == 'count':
        return int(len(df))
    elif aggregate == 'max' and aggregate_field and (aggregate_field in df.columns):
        max_idx = df[aggregate_field].idxmax()
        row = df.loc[max_idx].to_dict()
        if fields:
            return {k: v for k, v in row.items() if k in fields}
        return row
    elif aggregate == 'list':
        records = df.to_dict(orient='records')
        if fields:
            return [{k: v for k, v in r.items() if k in fields} for r in records]
        return records
    record = df.iloc[0].to_dict()
    if fields:
        return {k: v for k, v in record.items() if k in fields}
    return record