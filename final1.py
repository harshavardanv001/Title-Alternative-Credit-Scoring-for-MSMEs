from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pdfplumber
import gspread
from google.oauth2.service_account import Credentials
import re
import datetime
import time
import logging

# ==============================================================================
# GLOBAL CONFIGURATION
# ==============================================================================
SPREADSHEET_ID = "1Tmk5Zy5mAnuteXnlYa3EhY9PkTDkN5Qzmdw16n9DEpo"
CREDENTIALS_FILE = "credentials.json"
UPLOAD_FOLDER = 'uploads'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class MSMEReputationEngine:
    def __init__(self):
        self.bank_name = "Cloud Forensic Analysis"
        self.system_version = "v5.0-INTEGRATED"
        self.score = 650.0  
        self.total_inflow = 0.0
        self.total_outflow = 0.0
        self.daily_balances = []
        self.risk_strikes = 0
        self.growth_signals = 0
        self.early_compliance_hits = 0
        self.late_operational_hits = 0
        self.audit_log = []

    def log_adjustment(self, weight, category, rationale):
        self.score += float(weight)
        self.score = max(300.0, min(900.0, self.score))
        entry = f"[{'+' if weight >= 0 else ''}{weight}] {category.upper()}: {rationale}"
        self.audit_log.append({
            "val": f"{'+' if weight >= 0 else ''}{weight}", 
            "msg": entry, 
            "type": "pos" if weight >= 0 else "neg"
        })

    def clean_val(self, val):
        if not val or str(val).strip() in ["", "-", "None"]: return 0.0
        try:
            clean_str = str(val).replace(',', '').replace('$', '').replace('₹', '').strip()
            if "(" in clean_str:
                return -float(clean_str.replace('(', '').replace(')', ''))
            return float(clean_str)
        except: return 0.0

    def parse_bank_day(self, date_str):
        date_str = str(date_str).strip()
        patterns = ["%d-%m-%Y", "%d-%m-%y", "%d/%m/%y", "%m/%d/%Y"]
        for p in patterns:
            try: return datetime.datetime.strptime(date_str, p).day
            except: continue
        return 1

    def scan_data(self, transaction_list):
        for row in transaction_list:
            date_val, desc_val, amt_val, bal_val = row
            desc_clean = str(desc_val).upper()
            amount = self.clean_val(amt_val)
            balance = self.clean_val(bal_val)
            self.daily_balances.append(balance)
            day = self.parse_bank_day(date_val)
            full_text = f"{desc_clean} {amt_val} {bal_val}"

            is_credit = any(x in full_text for x in ["CREDIT", "DEP", "CR", "INCOME", "PAYROLL", "INTEREST"])
            
            if balance < -100:
                self.log_adjustment(-25.0, "SOLVENCY", f"Day {day}: Critical Overdraft State")

            if is_credit and amount > 0:
                self.total_inflow += amount
                if "INTEREST" in full_text:
                    self.log_adjustment(15.0, "ASSET", "Passive Asset Yield Detected")
                else:
                    self.log_adjustment(10.0, "REVENUE", "Standard Operational Credit")
            else:
                self.total_outflow += abs(amount)
                if any(k in desc_clean for k in ["RENT", "LEASE", "TAX", "GST", "IRS"]):
                    if day <= 10:
                        self.early_compliance_hits += 1
                        self.log_adjustment(60.0, "COMPLIANCE", f"Priority Settlement Early (Day {day})")
                    else:
                        self.late_operational_hits += 1
                        self.log_adjustment(-20.0, "LATENCY", f"Operational Delay Penalty (Day {day})")

                if amount > 5000 and not is_credit:
                    self.log_adjustment(-40.0, "VELOCITY", "Unidentified High-Volume Capital Outflow")

                if any(rk in full_text for rk in ["NSF", "FEE", "BOUNCE", "OVERDRAFT", "RETURNED"]):
                    self.risk_strikes += 1
                    self.log_adjustment(-100.0, "RISK", "Liquidity Failure Strike (Dishonored Payment)")

    def generate_html_string(self):
        f_score = int(self.score)
        if f_score >= 800:
            tier, color, bg_gradient = "PLATINUM", "#0f172a", "linear-gradient(135deg, #e2e8f0 0%, #94a3b8 100%)"
        elif f_score >= 700:
            tier, color, bg_gradient = "GOLD", "#854d0e", "linear-gradient(135deg, #fef9c3 0%, #facc15 100%)"
        elif f_score >= 550:
            tier, color, bg_gradient = "SILVER", "#334155", "linear-gradient(135deg, #f1f5f9 0%, #cbd5e1 100%)"
        else:
            tier, color, bg_gradient = "BRONZE", "#78350f", "linear-gradient(135deg, #ffedd5 0%, #fb923c 100%)"

        decision = "✅ APPROVED" if f_score > 650 else "⏳ MANUAL REVIEW" if f_score >= 500 else "❌ DENIED"
        decision_color = "text-emerald-600" if "APPROVED" in decision else "text-amber-600" if "REVIEW" in decision else "text-rose-600"

        logs_html = "".join([f"""
            <div class="flex items-center p-4 mb-2 {'bg-emerald-50/50 border-emerald-100' if l['type']=='pos' else 'bg-rose-50/50 border-rose-100'} border rounded-2xl">
                <span class="font-mono font-bold w-12 {'text-emerald-700' if l['type']=='pos' else 'text-rose-700'}">{l['val']}</span>
                <div class="flex-1 text-sm font-semibold text-slate-700">{l['msg']}</div>
            </div>""" for l in self.audit_log])

        return f"""
        <html>
        <head>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;700;800&display=swap" rel="stylesheet">
            <style>body{{font-family:'Plus Jakarta Sans',sans-serif; background:#f8fafc;}} .tier-g{{background:{bg_gradient};}}</style>
        </head>
        <body class="p-4">
            <div class="max-w-4xl mx-auto">
                <div class="grid grid-cols-1 md:grid-cols-12 gap-6">
                    <div class="md:col-span-4 tier-g p-8 rounded-[2.5rem] shadow-xl text-center flex flex-col items-center justify-center border-b-4 border-black/5">
                        <h3 class="text-[10px] font-black uppercase tracking-widest text-black/30 mb-2">Score</h3>
                        <div class="text-7xl font-black tracking-tighter" style="color:{color}">{f_score}</div>
                        <div class="mt-4 px-4 py-1 bg-black/10 rounded-full text-[10px] font-black uppercase" style="color:{color}">{tier}</div>
                    </div>
                    <div class="md:col-span-8 space-y-4">
                        <div class="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm">
                            <h3 class="text-[10px] font-black text-slate-400 uppercase mb-2">Decision</h3>
                            <div class="text-2xl font-black {decision_color}">{decision}</div>
                        </div>
                        <div class="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm max-h-[300px] overflow-y-auto">
                            {logs_html}
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>"""

def extract_pdf_data(pdf_path):
    transactions = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                for line in text.split('\n'):
                    match = re.match(r"(\d{2}-\d{2}-\d{4})\s+(.*)", line)
                    if match:
                        date = match.group(1); rest = match.group(2)
                        nums = re.findall(r"(-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", rest)
                        if len(nums) >= 1:
                            balance = nums[-1].replace(',', '')
                            desc_part = rest.split(nums[0])[0].strip()
                            amount = nums[0].replace(',', '') if len(nums) > 1 else "0"
                            transactions.append([date, desc_part, amount, balance])
        return transactions
    except: return None

def upload_to_sheets(data_list):
    if not os.path.exists(CREDENTIALS_FILE): return
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        sh = client.open_by_key(SPREADSHEET_ID)
        new_tab = "Audit_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        worksheet = sh.add_worksheet(title=new_tab, rows=len(data_list)+50, cols=10)
        worksheet.update([["Date", "Description", "Amount", "Balance"]] + data_list, value_input_option='USER_ENTERED')
    except: pass

app = Flask(__name__)
CORS(app)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'statement' not in request.files: return jsonify({"error": "No file"}), 400
    file = request.files['statement']
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    results = extract_pdf_data(file_path)
    if results:
        upload_to_sheets(results)
        engine = MSMEReputationEngine()
        engine.scan_data(results)
        return jsonify({"report_html": engine.generate_html_string()}), 200
    return jsonify({"error": "Failed"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)