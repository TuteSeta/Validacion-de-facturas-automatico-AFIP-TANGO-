import pandas as pd

def left_join_on_keys(df_left: pd.DataFrame, df_right: pd.DataFrame, keys: list) -> pd.DataFrame:
    # Sufijos para distinguir columnas origen/destino
    return df_left.merge(df_right, on=keys, how="left", suffixes=("_origen", "_destino"))
