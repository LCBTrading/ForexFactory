from flask import Flask, Response
import io

app = Flask(__name__)

@app.route("/calendar")
def calendar_endpoint():
    try:
        # Read the data from the CSV file that was updated manually
        with open("data.csv", "r", encoding="utf-8") as f:
            csv_data = f.read()
        return Response(csv_data, mimetype="text/csv")
    except Exception as e:
        return Response(f"Error fetching data: {e}", status=500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
