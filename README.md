<div align="center">

# 🌱 Grow A Garden Stock API 🌿

A sleek Flask app that scrapes stock data from [VulcanValues Grow A Garden](https://www.vulcanvalues.com/grow-a-garden/stock) every 5 minutes and serves it via a RESTful API. Deployed as a static site with a modern UI, this project is perfect for tracking seeds, gear, and Easter items! 🚀

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0.3-green?logo=flask)
![Render](https://img.shields.io/badge/Deployed%20on-Render-purple?logo=render)
![License](https://img.shields.io/badge/License-MIT-orange)

</div>

---

## ✨ Features

- 🌐 **Real-Time Scraping**: Automatically fetches stock data every 5 minutes using a background scheduler.
- 🛠️ **RESTful API**: Access seeds, gear, and Easter stock data with simple GET endpoints.
- 📊 **Static Site**: A beautifully styled HTML page showcasing available APIs with `curl` examples.
- 🔒 **Thread-Safe**: Efficient in-memory caching with thread-safe updates for high performance.
- ☁️ **Render-Ready**: Deploy seamlessly on Render with minimal setup.
- 📝 **Single File**: All Python, HTML, and CSS in one `app.py` for simplicity.

---

## 🛠️ Getting Started

### Prerequisites
- 🐍 Python 3.8+
- 📦 `pip` for installing dependencies

### Installation

1. **Clone the Repository**  
   ```bash
   git clone https://github.com/your-username/grow-a-garden-api.git
   cd grow-a-garden-api
