

from fastapi import HTTPException, UploadFile,status
import pandas as pd


def validate_excel_file(file: UploadFile, required_columns: set):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only Excel files are supported."
        )
    df = pd.read_excel(file.file)
    if not required_columns.issubset(df.columns):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Excel file must contain the following columns: {', '.join(required_columns)}"
        )
    return df.drop_duplicates()
