import pandas as pd
import numpy as np
from typing import Dict
from datetime import datetime


class DataQualityChecker:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.report = {}

    # ======================
    # NULL CHECKS
    # ======================
    def check_nulls(self):
        null_counts = self.df.isnull().sum()
        null_percent = (null_counts / len(self.df)) * 100

        self.report['nulls'] = pd.DataFrame({
            'null_count': null_counts,
            'null_percent': null_percent
        })

    # ======================
    # DUPLICATE DETECTION
    # ======================
    def check_duplicates(self):
        total_duplicates = self.df.duplicated().sum()
        duplicate_rows = self.df[self.df.duplicated()]

        self.report['duplicates'] = {
            'total_duplicates': total_duplicates,
            'sample': duplicate_rows.head(10)
        }

    # ======================
    # OUTLIER DETECTION (IQR)
    # ======================
    def check_outliers(self):
        outlier_summary = {}
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outliers = self.df[(self.df[col] < lower_bound) | (self.df[col] > upper_bound)]

            outlier_summary[col] = {
                'count': len(outliers),
                'lower_bound': lower_bound,
                'upper_bound': upper_bound
            }

        self.report['outliers'] = outlier_summary

    # ======================
    # GENERATE HTML REPORT
    # ======================
    def generate_html_report(self, output_file: str = "data_quality_report.html"):
        html_content = f"""
        <html>
        <head>
            <title>Data Quality Report</title>
            <style>
                body {{ font-family: Arial; padding: 20px; }}
                h1 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f4f4f4; }}
            </style>
        </head>
        <body>
            <h1>Data Quality Report</h1>
            <p>Generated at: {datetime.now()}</p>
        """

        # NULLS
        if 'nulls' in self.report:
            html_content += "<h2>Null Values</h2>"
            html_content += self.report['nulls'].to_html()

        # DUPLICATES
        if 'duplicates' in self.report:
            html_content += "<h2>Duplicates</h2>"
            html_content += f"<p>Total duplicates: {self.report['duplicates']['total_duplicates']}</p>"
            html_content += self.report['duplicates']['sample'].to_html()

        # OUTLIERS
        if 'outliers' in self.report:
            html_content += "<h2>Outliers</h2><table><tr><th>Column</th><th>Count</th><th>Lower Bound</th><th>Upper Bound</th></tr>"
            for col, data in self.report['outliers'].items():
                html_content += f"<tr><td>{col}</td><td>{data['count']}</td><td>{data['lower_bound']}</td><td>{data['upper_bound']}</td></tr>"
            html_content += "</table>"

        html_content += "</body></html>"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"Report generated: {output_file}")


# ======================
# USAGE EXAMPLE
# ======================
if __name__ == "__main__":
    # Load sample data
    df = pd.DataFrame({
        'name': ['A', 'B', 'C', 'C', None],
        'age': [20, 21, 22, 22, 1000],
        'salary': [1000, 2000, None, 2000, 3000]
    })

    dq = DataQualityChecker(df)

    dq.check_nulls()
    dq.check_duplicates()
    dq.check_outliers()

    dq.generate_html_report()
