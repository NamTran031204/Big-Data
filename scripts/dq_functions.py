# scripts/dq_functions.py
import pyspark.sql.functions as F
from pyspark.sql.types import StringType

def check_basics(df):

    total_count = df.count()
    duplicate_count = total_count - df.dropDuplicates().count()
    
    # Check null
    null_counts = df.select([
        F.count(F.when(F.col(c).isNull(), c)).alias(c) 
        for c in df.columns
    ]).collect()[0].asDict()
    
    return {
        "total_rows": total_count,
        "duplicate_rows": duplicate_count,
        "null_counts": null_counts
    }

def get_stats(df):
    """Lấy thống kê mô tả (Summary) cho các cột số"""
    numeric_cols = [f.name for f in df.schema.fields if not isinstance(f.dataType, (StringType))]
    if not numeric_cols:
        return {}
    return df.select(numeric_cols).summary("mean", "min", "25%", "50%", "75%", "max").toPandas().to_dict()