from flask import Flask, render_template, request, Response
import json
import time
import uuid
import datetime
from scraper import fetch_data
import os

app = Flask(__name__)

scraped_data_store = {}

@app.after_request
def disable_buffering(response):
    response.headers['X-Accel-Buffering'] = 'no'
    return response

def parse_date(date_str):
    return datetime.datetime.strptime(date_str, "%d/%m/%Y").date()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_quota', methods=['POST'])
def get_quota():
    company_numbers = [c.strip() for c in request.form['company_numbers'].splitlines() if c.strip()]
    start_date_str = request.form['start_date']
    end_date_str = request.form['end_date']

    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    delta_days = (end_date - start_date).days + 1

    request_id = str(uuid.uuid4())
    scraped_data_store[request_id] = []

    def generate():
        total = len(company_numbers)
        for idx, comp in enumerate(company_numbers, start=1):
            try:
                entries = fetch_data(comp, start_date_str, end_date_str)
            except Exception as e:
                err_msg = f"Error for {comp}: {e}"
                yield f"data: {json.dumps({'error': err_msg, 'progress': int(100 * idx / total)})}\n\n"
                continue

            for entry in entries:
                entry['CompanyNumber'] = comp
                scraped_data_store[request_id].append(entry)
                progress = int(100 * idx / total)
                yield f"data: {json.dumps({'data': entry, 'progress': progress})}\n\n"
                time.sleep(0.05)

        summary = {}
        today = end_date
        quota_keywords = [
            "طباعة طلب تصريح عمل آلي - المدفوع مسبقاً",
            "تصريح عمل على كفالة ذويهم",
            "تصريح عمل الانتقال"
        ]

        for entry in scraped_data_store[request_id]:
            comp = entry['CompanyNumber']
            permit_type = entry['PermitType']
            try:
                entry_date = parse_date(entry['Date'])
            except Exception:
                continue

            if comp not in summary:
                summary[comp] = {
                    'QuotaLast7': 0,
                    'ReplacementLast7': 0,
                    'QuotaLastN': 0,
                    'ReplacementLastN': 0
                }

            days_diff = (today - entry_date).days
            if 0 <= days_diff < 7:
                if any(keyword in permit_type for keyword in quota_keywords):
                    summary[comp]['QuotaLast7'] += 1
                if "تصريح عمل الاستبدال" in permit_type:
                    summary[comp]['ReplacementLast7'] += 1

            if 0 <= days_diff < delta_days:
                if any(keyword in permit_type for keyword in quota_keywords):
                    summary[comp]['QuotaLastN'] += 1
                if "تصريح عمل الاستبدال" in permit_type:
                    summary[comp]['ReplacementLastN'] += 1

        yield f"data: {json.dumps({'summary': summary, 'done': True, 'request_id': request_id})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)