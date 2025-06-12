from flask import Flask, jsonify, render_template_string, request
from pydoll import Chrome  # Replace requests and BeautifulSoup with PyDoll
import logging
from datetime import datetime
import re
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Lock
import atexit

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache and lock for thread-safe updates
cached_data = None
cache_lock = Lock()

# HTML template with embedded CSS (unchanged)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grow A Garden Stock API</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }
        h1 {
            text-align: center;
            color: #2c3e50;
        }
        h2 {
            color: #34495e;
        }
        pre {
            background: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
        code {
            font-family: 'Courier New', Courier, monospace;
            color: #c0392b;
        }
        ul {
            list-style: none;
            padding: 0;
        }
        li {
            margin: 10px 0;
        }
        a {
            color: #2980b9;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .footer {
            text-align: center;
            margin-top: 20px;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Grow A Garden Stock API</h1>
        <p>Welcome to the API for accessing real-time stock data from <a href="https://www.vulcanvalues.com/grow-a-garden/stock">VulcanValues Grow A Garden</a>. Data is updated every 5 minutes.</p>
        <h2>Available API Endpoints</h2>
        <ul>
            <li>
                <strong>GET /api/stocks</strong>
                <p>Returns all stock data (seeds, gear, and Easter items).</p>
                <pre><code>curl -X GET {{ base_url }}/api/stocks</code></pre>
                <p>Example Response:</p>
                <pre><code>{
    "seeds": [...],
    "gear": [...],
    "easter": [...],
    "last_updated": "YYYY-MM-DD HH:MM:SS"
}</code></pre>
            </li>
            <li>
                <strong>GET /api/stocks/seeds</strong>
                <p>Returns only seed stock data.</p>
                <pre><code>curl -X GET {{ base_url }}/api/stocks/seeds</code></pre>
            </li>
            <li>
                <strong>GET /api/stocks/gear</strong>
                <p>Returns only gear stock data.</p>
                <pre><code>curl -X GET {{ base_url }}/api/stocks/gear</code></pre>
            </li>
            <li>
                <strong>GET /api/stocks/easter</strong>
                <p>Returns only Easter stock data.</p>
                <pre><code>curl -X GET {{ base_url }}/api/stocks/easter</code></pre>
            </li>
        </ul>
        <div class="footer">
            <p>Built with Flask | Data sourced from <a href="https://www.vulcanvalues.com">VulcanValues</a> | Deployed on Render</p>
        </div>
    </div>
</body>
</html>
"""

# Updated function to scrape stock data using PyDoll
def scrape_stock_data():
    url = "https://www.vulcanvalues.com/grow-a-garden/stock"
    try:
        # Initialize PyDoll browser
        options = Chrome.Options()
        # Optional: Add proxy or other options
        # options.add_argument("--proxy-server=http://your-proxy:port")
        browser = Chrome(options=options)
        
        # Navigate to the page (PyDoll handles CAPTCHAs automatically)
        browser.visit(url)

        # Initialize data structure
        stock_data = {
            "seeds": [],
            "gear": [],
            "easter": [],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Find sections for seeds, gear, and Easter stocks
        sections = browser.find_elements("css selector", "div[class*='stock'], div[class*='seed'], div[class*='gear'], div[class*='easter']")
        for section in sections:
            title = section.find_element("css selector", "h2, h3")
            if not title:
                continue
            title_text = title.text.lower().strip()

            # Determine category
            category = None
            if "seed" in title_text:
                category = "seeds"
            elif "gear" in title_text:
                category = "gear"
            elif "easter" in title_text:
                category = "easter"
            else:
                continue

            # Find items in the section
            items = section.find_elements("css selector", "div[class*='item'], div[class*='product']")
            for item in items:
                name = item.find_element("css selector", "span[class*='name'], span[class*='title']")
                price = item.find_element("css selector", "span[class*='price'], span[class*='cost']")
                stock = item.find_element("css selector", "span[class*='stock'], span[class*='availability']")

                item_data = {
                    "name": name.text.strip() if name else "Unknown",
                    "price": price.text.strip() if price else "N/A",
                    "stock": stock.text.strip() if stock else "N/A"
                }
                stock_data[category].append(item_data)

        # Close the browser
        browser.quit()
        return stock_data

    except Exception as e:
        logger.error(f"Error scraping data: {e}")
        return {
            "error": "Failed to scrape data",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Function to update cache
def update_cache():
    global cached_data
    try:
        new_data = scrape_stock_data()
        with cache_lock:
            cached_data = new_data
        logger.info("Cache updated successfully")
    except Exception as e:
        logger.error(f"Error updating cache: {e}")

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=update_cache, trigger="interval", minutes=5)
scheduler.start()

# Ensure scheduler shuts down when app exits
atexit.register(lambda: scheduler.shutdown())

# Initial scrape to populate cache
update_cache()

# Route for static homepage
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, base_url=request.host_url.rstrip('/'))

# API endpoint for all stock data
@app.route('/api/stocks', methods=['GET'])
def get_all_stocks():
    with cache_lock:
        if cached_data is None:
            return jsonify({"error": "Data not yet available", "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify(cached_data)

# API endpoint for seeds
@app.route('/api/stocks/seeds', methods=['GET'])
def get_seeds():
    with cache_lock:
        if cached_data is None:
            return jsonify({"error": "Data not yet available", "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify({"seeds": cached_data.get("seeds", []), "last_updated": cached_data.get("last_updated")})

# API endpoint for gear
@app.route('/api/stocks/gear', methods=['GET'])
def get_gear():
    with cache_lock:
        if cached_data is None:
            return jsonify({"error": "Data not yet available", "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify({"gear": cached_data.get("gear", []), "last_updated": cached_data.get("last_updated")})

# API endpoint for Easter items
@app.route('/api/stocks/easter', methods=['GET'])
def get_easter():
    with cache_lock:
        if cached_data is None:
            return jsonify({"error": "Data not yet available", "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify({"easter": cached_data.get("easter", []), "last_updated": cached_data.get("last_updated")})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
