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
import pyjson5  # Ensure you have installed pyjson5 via "pip install pyjson5"
import shutil

app = Flask(__name__)

def clean_json_str(s):
    """
    Remove any JavaScript function calls (like Object.freeze(...))
    wrapping pure data. This function uses a regular expression to
    replace instances of Object.freeze({...}) with just the inner object.
    """
    pattern = r'Object\.freeze\(\s*(\{.*?\})\s*\)'
    while re.search(pattern, s, flags=re.DOTALL):
        s = re.sub(pattern, r'\1', s, flags=re.DOTALL)
    return s

def fetch_forex_factory_data():
    """
    1) Launch Microsoft Edge in headless mode using Selenium.
    2) Navigate to the Forex Factory Calendar.
    3) Extract the JSON-like data from the page source.
    4) Clean the extracted string to remove any extraneous JS code.
    5) Parse the cleaned JSON5 data and filter for events where currency == 'USD'.
    6) Build a properly formatted CSV with one header row: name, impactClass, timeLabel, date, currency.
    7) Return the CSV as a string.
    """

    # ---------------------------------------------
    # 1) Configure and start Selenium with Edge
    # ---------------------------------------------
    edge_options = EdgeOptions()
    edge_options.add_argument("--headless")        # Run in headless mode.
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Edge/115.0.0.0"
    )

    # Look up msedgedriver in the PATH (do not use a Windows path)
    driver_path = shutil.which("msedgedriver")
    if driver_path is None:
        raise Exception("msedgedriver not found. Ensure that Microsoft Edge and msedgedriver are installed.")
    service = EdgeService(executable_path=driver_path)
    driver = webdriver.Edge(service=service, options=edge_options)

    try:
        # ---------------------------------------------
        # 2) Navigate to the Forex Factory Calendar
        # ---------------------------------------------
        url = "https://www.forexfactory.com/calendar"
        driver.get(url)
        # Wait for the page to load and for dynamic content to appear.
        time.sleep(15)
        html = driver.page_source
    finally:
        driver.quit()

    # ---------------------------------------------
    # 3) Extract JSON-like data from the page's HTML
    # ---------------------------------------------
    marker = "window.calendarComponentStates[1] ="
    start_index = html.find(marker)
    if start_index == -1:
        return "Error: Could not find the calendar JSON marker in the page."
    start_index += len(marker)
    end_index = html.find("};", start_index)
    if end_index == -1:
        return "Error: Could not find the end of the calendar JSON data."
    # Include the closing brace "}".
    json_str = html[start_index:end_index+1]

    # ---------------------------------------------
    # 4) Clean the extracted string to remove extraneous JavaScript code.
    # ---------------------------------------------
    json_str = clean_json_str(json_str)

    # ---------------------------------------------
    # 5) Parse JSON5 & filter for currency == 'USD'
    # ---------------------------------------------
    try:
        calendar_data = pyjson5.loads(json_str)
    except Exception as e:
        # Save the raw JSON substring for debugging.
        with open("raw_calendar_data.json", "w", encoding="utf-8") as debug_file:
            debug_file.write(json_str)
        return f"Error parsing JSON: {e}. Raw JSON saved to raw_calendar_data.json for debugging."

    days = calendar_data.get("days", [])
    if not days:
        return "No calendar days found in JSON data."

    # Prepare CSV output using StringIO.
    output = io.StringIO()
    fieldnames = ["name", "impactClass", "timeLabel", "date", "currency"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()  # Write the header row once

    # ---------------------------------------------
    # 6) Build the CSV rows filtering for USD events only.
    # ---------------------------------------------
    for day in days:
        # Determine the date string.
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
            # Retrieve currency from "currency" or deduce from "prefixedName"
            event_currency = event.get("currency", "").strip()
            if not event_currency:
                prefixed = event.get("prefixedName", "").strip()
                event_currency = (prefixed.split()[0] if prefixed else "").strip()

            # Filter: Include only events with currency "USD"
            if event_currency.upper() == "USD":
                writer.writerow({
                    "name": event_name,
                    "impactClass": event_impact_class,
                    "timeLabel": event_time_label,
                    "date": day_date,
                    "currency": event_currency
                })

    # ---------------------------------------------
    # 7) Return the CSV as a string.
    # ---------------------------------------------
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
