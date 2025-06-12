from flask import Flask, jsonify, render_template_string, request
from playwright.sync_api import sync_playwright
from threading import Lock  # Added import
import logging
from datetime import datetime
import time
import random
import re

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache and lock
cached_data = None
cache_lock = Lock()

# HTML template (updated for clarity)
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
                <p>Returns all stock data (seeds, gear, Easter, honey, cosmetics).</p>
                <pre><code>curl -X GET {{ base_url }}/api/stocks</code></pre>
                <p>Example Response:</p>
                <pre><code>{
    "seeds": [...],
    "gear": [...],
    "easter": [...],
    "honey": [...],
    "cosmetics": [...],
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
            <li>
                <strong>GET /api/stocks/honey</strong>
                <p>Returns only honey stock data.</p>
                <pre><code>curl -X GET {{ base_url }}/api/stocks/honey</code></pre>
            </li>
            <li>
                <strong>GET /api/stocks/cosmetics</strong>
                <p>Returns only cosmetics stock data.</p>
                <pre><code>curl -X GET {{ base_url }}/api/stocks/cosmetics</code></pre>
            </li>
        </ul>
        <div class="footer">
            <p>Built with Flask | Data sourced from <a href="https://www.vulcanvalues.com">VulcanValues</a> | Deployed on Render</p>
        </div>
    </div>
</body>
</html>
"""

# Scrape stock data
def scrape_stock_data():
    url = "https://www.vulcanvalues.com/grow-a-garden/stock"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                viewport={"width": 1280, "height": 720},
                # proxy={"server": "http://your-proxy:port"}
            )
            page = context.new_page()

            # Stealth enhancements
            page.goto(url, timeout=30000)
            time.sleep(random.uniform(2, 4))
            page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            page.mouse.click(random.randint(100, 500), random.randint(100, 500))
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(random.uniform(2, 3))
            page.wait_for_load_state("networkidle", timeout=20000)

            # Check for CAPTCHA
            captcha_selector = "div.g-recaptcha, div[class*='cf-turnstile'], div[class*='captcha']"
            if page.query_selector(captcha_selector):
                logger.error("CAPTCHA detected, cannot proceed without solver")
                browser.close()
                return {"error": "Blocked by CAPTCHA", "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

            # Wait for content
            page.wait_for_selector("h3", timeout=15000)

            # Initialize data structure
            stock_data = {
                "seeds": [],
                "gear": [],
                "easter": [],
                "honey": [],
                "cosmetics": [],
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Find sections
            headings = page.query_selector_all("h3")
            for heading in headings:
                title_text = heading.inner_text().lower().strip()
                category = None
                if "seeds stock" in title_text:
                    category = "seeds"
                elif "gear stock" in title_text:
                    category = "gear"
                elif "egg stock" in title_text:
                    category = "easter"
                elif "honey stock" in title_text:
                    category = "honey"
                elif "cosmetics stock" in title_text:
                    category = "cosmetics"
                else:
                    continue

                # Find sibling divs containing items
                parent = heading.evaluate_handle("node => node.parentNode")
                items = parent.query_selector_all("div > p")
                for item in items:
                    text = item.inner_text().strip()
                    # Parse "Name xQuantity"
                    match = re.match(r"(.+?)\s*x(\d+)", text)
                    if match:
                        name, quantity = match.groups()
                        item_data = {
                            "name": name.strip(),
                            "quantity": int(quantity),
                            "price": "N/A"
                        }
                        stock_data[category].append(item_data)

            # Log if no data
            if not any(stock_data[cat] for cat in stock_data if cat != "last_updated"):
                logger.warning("No stock data found, check selectors or page content")

            browser.close()
            return stock_data

    except Exception as e:
        logger.error(f"Error scraping data: {str(e)}")
        return {
            "error": f"Failed to scrape data: {str(e)}",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Cache update
def update_cache():
    global cached_data
    try:
        new_data = scrape_stock_data()
        with cache_lock:
            cached_data = new_data
        logger.info("Cache updated successfully")
    except Exception as e:
        logger.error(f"Error updating cache: {e}")

# Scheduler
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=update_cache, trigger="interval", minutes=5)
scheduler.start()

# Shutdown scheduler
import atexit
atexit.register(lambda: scheduler.shutdown())

# Initial scrape
update_cache()

# Routes
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, base_url=request.host_url.rstrip('/'))

@app.route('/api/stocks', methods=['GET'])
def get_all_stocks():
    with cache_lock:
        if cached_data is None:
            return jsonify({"error": "Data not yet available", "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify(cached_data)

@app.route('/api/stocks/seeds', methods=['GET'])
def get_seeds():
    with cache_lock:
        if cached_data is None:
            return jsonify({"error": "Data not yet available", "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify({"seeds": cached_data.get("seeds", []), "last_updated": cached_data.get("last_updated")})

@app.route('/api/stocks/gear', methods=['GET'])
def get_gear():
    with cache_lock:
        if cached_data is None:
            return jsonify({"error": "Data not yet available", "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify({"gear": cached_data.get("gear", []), "last_updated": cached_data.get("last_updated")})

@app.route('/api/stocks/easter', methods=['GET'])
def get_easter():
    with cache_lock:
        if cached_data is None:
            return jsonify({"error": "Data not yet available", "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify({"easter": cached_data.get("easter", []), "last_updated": cached_data.get("last_updated")})

@app.route('/api/stocks/honey', methods=['GET'])
def get_honey():
    with cache_lock:
        if cached_data is None:
            return jsonify({"error": "Data not yet available", "last_updated": datetime.now().strftime("%Y-m-%d %H:%M:%S")})
        return jsonify({"honey": cached_data.get("honey", []), "last_updated": cached_data.get("last_updated")})

@app.route('/api/stocks/cosmetics', methods=['GET'])
def get_cosmetics():
    with cache_lock:
        if cached_data is None:
            return jsonify({"error": "Data not yet available", "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify({"cosmetics": cached_data.get("cosmetics", []), "last_updated": cached_data.get("last_updated")})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
