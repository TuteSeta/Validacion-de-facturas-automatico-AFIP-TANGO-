import pandas as pd

# Sufijos para distinguir columnas origen/destino
def left_join_on_keys(df_left: pd.DataFrame, df_right: pd.DataFrame, keys: list) -> pd.DataFrame:
    return df_left.merge(df_right, on=keys, how="left", suffixes=("_origen", "_destino"))
