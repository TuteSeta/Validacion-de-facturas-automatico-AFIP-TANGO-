import pandas as pd

def load_excel(path: str, sheet, dtype=None) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet, dtype=dtype)
    df = df.rename(columns=lambda c: str(c).strip())
    return df
