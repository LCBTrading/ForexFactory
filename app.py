from flask import Flask, Response
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from bs4 import BeautifulSoup
from datetime import datetime
import time
import csv
import io
import re
import pyjson5
import shutil

app = Flask(__name__)

def clean_json_str(s):
    """
    Remove any JavaScript function calls (like Object.freeze(...))
    wrapping pure data.
    """
    pattern = r'Object\.freeze\(\s*(\{.*?\})\s*\)'
    while re.search(pattern, s, flags=re.DOTALL):
        s = re.sub(pattern, r'\1', s, flags=re.DOTALL)
    return s

def fetch_forex_factory_data():
    """
    Launches Microsoft Edge in headless mode, scrapes the Forex Factory calendar,
    and returns the filtered data as CSV.
    """
    # Configure Edge options for stability in Docker
    edge_options = EdgeOptions()
    edge_options.add_argument("--headless")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    edge_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/133.0.3065.69"
    )

    # Look up msedgedriver in PATH
    driver_path = shutil.which("msedgedriver")
    if driver_path is None:
        raise Exception("msedgedriver not found. Ensure that Microsoft Edge and msedgedriver are installed.")
    service = EdgeService(executable_path=driver_path)
    driver = webdriver.Edge(service=service, options=edge_options)

    try:
        url = "https://www.forexfactory.com/calendar"
        driver.get(url)
        # Wait for the page to load dynamic content
        time.sleep(15)
        html = driver.page_source
    finally:
        driver.quit()

    marker = "window.calendarComponentStates[1] ="
    start_index = html.find(marker)
    if start_index == -1:
        return "Error: Could not find the calendar JSON marker in the page."
    start_index += len(marker)
    end_index = html.find("};", start_index)
    if end_index == -1:
        return "Error: Could not find the end of the calendar JSON data."
    json_str = html[start_index:end_index+1]
    json_str = clean_json_str(json_str)

    try:
        calendar_data = pyjson5.loads(json_str)
    except Exception as e:
        with open("raw_calendar_data.json", "w", encoding="utf-8") as debug_file:
            debug_file.write(json_str)
        return f"Error parsing JSON: {e}. Raw JSON saved to raw_calendar_data.json for debugging."

    days = calendar_data.get("days", [])
    if not days:
        return "No calendar days found in JSON data."

    output = io.StringIO()
    fieldnames = ["name", "impactClass", "timeLabel", "date", "currency"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()

    for day in days:
        dateline = day.get("dateline")
        if dateline:
            try:
                day_timestamp = int(dateline)
                day_date = datetime.fromtimestamp(day_timestamp).strftime("%b %d, %Y")
            except ValueError:
                day_date = BeautifulSoup(day.get("date", ""), "html.parser").get_text().strip()
        else:
            day_date = BeautifulSoup(day.get("date", ""), "html.parser").get_text().strip()

        events = day.get("events", [])
        for event in events:
            event_name = event.get("name", "").strip()
            event_impact_class = event.get("impactClass", "").strip()
            event_time_label = event.get("timeLabel", "").strip()
            event_currency = event.get("currency", "").strip()
            if not event_currency:
                prefixed = event.get("prefixedName", "").strip()
                event_currency = (prefixed.split()[0] if prefixed else "").strip()
            if event_currency.upper() == "USD":
                writer.writerow({
                    "name": event_name,
                    "impactClass": event_impact_class,
                    "timeLabel": event_time_label,
                    "date": day_date,
                    "currency": event_currency
                })

    csv_data = output.getvalue()
    output.close()
    return csv_data

@app.route("/calendar")
def calendar_endpoint():
    try:
        csv_data = fetch_forex_factory_data()
        return Response(csv_data, mimetype="text/csv")
    except Exception as e:
        return Response(f"Error fetching data: {e}", status=500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
