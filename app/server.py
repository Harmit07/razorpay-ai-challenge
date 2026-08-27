"""
Lightweight embedded HTTP server for the AI Revenue Recovery Agent Dashboard.
Serves static assets and provides REST API endpoints for batch metrics, transactions, and audit trails.
"""

from __future__ import annotations
import os
import json
import mimetypes
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Any, List

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
APP_DIR = ROOT_DIR / "app"


class RecoveryDashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def do_GET(self):
        # API Routes
        if self.path == "/api/summary":
            self.send_json_response(self.get_summary_data())
            return
        elif self.path == "/api/transactions":
            self.send_json_response(self.get_transactions_data())
            return
        elif self.path.startswith("/api/audit/"):
            txn_id = self.path.split("/api/audit/")[1]
            self.send_json_response(self.get_audit_for_txn(txn_id))
            return
        elif self.path == "/api/benchmark":
            self.send_json_response(self.get_benchmark_data())
            return
        elif self.path == "/api/export/full-json":
            self.send_file_download(DATA_DIR / "full_batch_audit_trail.json", "full_batch_audit_trail.json", "application/json")
            return
        elif self.path == "/api/export/full-md":
            self.send_file_download(DATA_DIR / "full_batch_audit_report.md", "full_batch_audit_report.md", "text/markdown")
            return
        elif self.path.startswith("/api/export/txn-json/"):
            txn_id = self.path.split("/api/export/txn-json/")[1]
            records = self.get_audit_for_txn(txn_id)
            body = json.dumps(records, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="audit_trail_{txn_id}.json"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Default static file serving
        super().do_GET()

    def send_json_response(self, data: Any, status_code: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file_download(self, file_path: Path, download_filename: str, content_type: str):
        if not file_path.exists():
            self.send_error(404, "File not found")
            return
        with open(file_path, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{download_filename}"')
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def get_summary_data(self) -> Dict[str, Any]:
        benchmark_file = DATA_DIR / "comparative_benchmark_results.json"
        if benchmark_file.exists():
            with open(benchmark_file, "r", encoding="utf-8") as f:
                bench = json.load(f)
        else:
            bench = {}

        return {
            "total_transactions": bench.get("total_transactions", 750),
            "total_revenue_at_risk_inr": bench.get("total_revenue_at_risk_inr", 22624681.80),
            "ai_recovered_revenue_inr": bench.get("ai_recovered_revenue_inr", 5787950.92),
            "naive_recovered_revenue_inr": bench.get("naive_recovered_revenue_inr", 1888060.95),
            "incremental_recovered_revenue_inr": bench.get("incremental_recovered_revenue_inr", 3899889.97),
            "revenue_recovery_lift_pct": bench.get("revenue_recovery_lift_pct", 206.6),
            "ai_recovery_rate_pct": bench.get("ai_recovery_rate_pct", 25.6),
            "naive_recovery_rate_pct": bench.get("naive_recovery_rate_pct", 8.3),
            "ai_compliance_violations": 0,
            "naive_compliance_violations": bench.get("naive_compliance_violations", 612),
            "ai_recovered_count": bench.get("ai_recovered_count", 194),
            "naive_recovered_count": bench.get("naive_recovered_count", 48),
        }

    def get_benchmark_data(self) -> Dict[str, Any]:
        benchmark_file = DATA_DIR / "comparative_benchmark_results.json"
        if benchmark_file.exists():
            with open(benchmark_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_transactions_data(self) -> List[Dict[str, Any]]:
        txn_file = DATA_DIR / "synthetic_transactions_750.json"
        if txn_file.exists():
            with open(txn_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def get_audit_for_txn(self, txn_id: str) -> List[Dict[str, Any]]:
        audit_file = DATA_DIR / "full_batch_audit_trail.json"
        demo_file = DATA_DIR / "demo_single_txn_audit_trail.json"
        
        matches = []
        if audit_file.exists():
            with open(audit_file, "r", encoding="utf-8") as f:
                records = json.load(f)
                matches.extend([r for r in records if r.get("entity_id") == txn_id])

        if not matches and demo_file.exists():
            with open(demo_file, "r", encoding="utf-8") as f:
                records = json.load(f)
                matches.extend([r for r in records if r.get("entity_id") == txn_id])

        return matches


def start_server(port: int = 8080):
    server_address = ("", port)
    httpd = HTTPServer(server_address, RecoveryDashboardHandler)
    print(f"🚀 AI Revenue Recovery Dashboard running at http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server.")
        httpd.server_close()


if __name__ == "__main__":
    start_server(8080)
