# scripts/generate_report.py
from ingest_bronze import spark  
from dq_functions import check_basics, get_stats
import json
import os

def run_quality_check():
    os.makedirs("../data/reports", exist_ok=True)
    
    tables = ["orders", "order_items", "products"]
    full_report = {}

    for table in tables:
        print(f"🔍 Đang kiểm tra chất lượng bảng: {table}...")
        
     
        df = spark.read.parquet(f"s3a://olist-bronze/{table}/")
   
        basics = check_basics(df)
        stats = get_stats(df)
        
        full_report[table] = {
            "summary": basics,
            "profiling": stats
        }

  
    with open("../data/reports/bronze_quality_report.json", "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=4, ensure_ascii=False)
        
    print(" Báo cáo chất lượng đã được lưu tại: data/reports/bronze_quality_report.json")

if __name__ == "__main__":
    run_quality_check()