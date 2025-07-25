# 🕷️ Advanced Website Crawler

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4.9%2B-green.svg)](https://www.crummy.com/software/BeautifulSoup/)
[![Playwright](https://img.shields.io/badge/Playwright-1.30%2B-orange.svg)](https://playwright.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/SWEHULYADAV/advanced-website-crawler?style=social)](https://github.com/SWEHULYADAV/advanced-website-crawler/stargazers)
[![Follow](https://img.shields.io/github/followers/SWEHULYADAV?style=social)](https://github.com/SWEHULYADAV)

[Discord](https://discord.gg/your-server) | [Documentation](https://github.com/SWEHULYADAV/advanced-website-crawler/wiki) | [Report Bug](https://github.com/SWEHULYADAV/advanced-website-crawler/issues) | [Request Feature](https://github.com/SWEHULYADAV/advanced-website-crawler/issues)

</div>

A powerful and feature-rich web crawler built in Python that supports both static and dynamic webpage crawling, with extensive content extraction capabilities. Perfect for web scraping, content archiving, and data analysis projects.

## � Description

The Advanced Website Crawler is a sophisticated Python-based web scraping tool designed to handle modern web applications with both static and dynamic content. Here's what makes it special:

### 🎯 Key Features

- **Smart Crawling**: Automatically detects and processes both static HTML and JavaScript-rendered content
- **Multi-threaded Performance**: Parallel processing capabilities for faster crawling
- **Comprehensive Content Extraction**: Captures HTML, JavaScript, CSS, text, and media files
- **Streaming Content Detection**: Identifies and extracts streaming URLs and embedded media players
- **Organized Output**: Structured storage of all extracted content in a clean directory hierarchy

### 🔍 Use Cases

1. **Content Archiving**
   - Website backups and archives
   - Digital content preservation
   - Offline access to web content

2. **Data Analysis**
   - Market research and competitive analysis
   - Content auditing
   - SEO analysis and optimization

3. **Media Collection**
   - Image and video downloading
   - Streaming URL extraction
   - Multimedia content cataloging

4. **Site Analysis**
   - Structure mapping
   - Link relationship analysis
   - Content organization study

### 💡 Intelligent Features

- **Adaptive Processing**: Automatically adjusts crawling strategy based on website structure
- **Resource-Friendly**: Efficient memory usage and controlled parallel processing
- **Error Handling**: Robust recovery from network issues and malformed content
- **Format Support**: Handles various content types including HTML5, modern JavaScript, and streaming media

### 🛠️ Technical Capabilities

- Sitemap.xml processing for efficient crawling
- robots.txt compliance
- Dynamic content rendering with Playwright
- Multi-threaded URL processing
- Structured JSON and CSV output
- Comprehensive metadata extraction
- Custom user-agent and header management

## �📌 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#️-configuration-options)
- [Output Files](#-output-files)
- [Best Practices](#-best-practices)
- [Requirements](#-requirements)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact](#-contact)

## ✨ Features

- 🌐 **Multi-mode Crawling**
  - Complete website crawling
  - Batch URL processing
  - Single page extraction
  
- 🚀 **Advanced Capabilities**
  - Static page crawling
  - Dynamic (JavaScript) content extraction
  - Sitemap.xml support
  - Parallel processing
  
- 📦 **Content Extraction**
  - HTML source code
  - JavaScript files
  - CSS stylesheets
  - Text content
  - Media files (images & videos)
  - Streaming URLs detection
  
- 🗂️ **Organized Output**
  ```
  output/
  └── domain_name/
      ├── source/
      │   ├── html/
      │   ├── js/
      │   └── css/
      ├── text/
      └── media/
  ```

## 🔧 Installation & Requirements

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

### Core Dependencies

- **Web Scraping & Browsing**
  - `beautifulsoup4` - HTML parsing
  - `playwright` - Browser automation
  - `requests` - HTTP requests
  - `urllib3` - HTTP client
  - `lxml` - XML/HTML processing

- **Performance Optimization**
  - `aiohttp` - Async HTTP
  - `aiodns` - DNS resolver
  - `cchardet` - Character encoding
  - `brotli` - Compression

- **Data Processing**
  - `html5lib` - HTML parser
  - `cssselect` - CSS selectors
  - `python-dateutil` - Date handling

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/SWEHULYADAV/advanced-website-crawler.git
   cd advanced-website-crawler
   ```

2. Create a virtual environment (recommended):
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```bash
   playwright install
   ```

### Optional Dependencies

- **Development Tools**
  - `black` - Code formatting
  - `pylint` - Code linting
  - `pytest` - Testing

Install development dependencies:
```bash
pip install -r requirements.txt[dev]
```

## 🚀 Usage

The crawler offers three main modes of operation:

### 1. Complete Website Crawling
```bash
python CrawlAnything.py
# Select option 1
```

### 2. Batch URL Processing
```bash
python CrawlAnything.py
# Select option 2
```

### 3. Single Page Extraction
```bash
python CrawlAnything.py
# Select option 3
```

## ⚙️ Configuration Options

- 🔄 **Parallel Processing**
  - Enable/disable parallel crawling
  - Customize number of workers (1-20)

- 🎯 **Media Downloads**
  - Optional image and video downloading
  - Structured media storage

- 🌐 **Browser Options**
  - Headless mode toggle
  - Custom user agent
  - Network request interception

## 📝 Output Files

1. **CSV Output**
   - List of all crawled URLs
   - Crawl status and timestamps

2. **JSON Output**
   - Detailed metadata
   - Content structure
   - Media information
   - Streaming URLs

3. **Extracted Content**
   - Original HTML files
   - Parsed text content
   - Downloaded media
   - JavaScript and CSS files

## 🛡️ Features

### Content Extraction
- ✅ Complete HTML source code
- ✅ JavaScript files and inline scripts
- ✅ CSS stylesheets (internal & external)
- ✅ Text content and metadata
- ✅ Images and videos
- ✅ Streaming URLs and players

### Performance
- ⚡ Parallel processing
- 🔄 Batch URL handling
- 🎯 Selective content downloading
- 🚦 Rate limiting and respect for robots.txt

### Organization
- 📁 Structured output folders
- 🏷️ Clear file naming
- 📊 Detailed logging
- 🔍 Easy content navigation

## 💡 Best Practices

1. **Respect Robots.txt**
   - The crawler automatically checks and follows robots.txt rules
   - Implements polite crawling delays

2. **Error Handling**
   - Robust error recovery
   - Detailed error logging
   - Session persistence

3. **Resource Management**
   - Memory-efficient processing
   - Controlled parallel execution
   - Clean temporary files

## 📋 Requirements

- Python 3.8 or higher
- BeautifulSoup4
- Playwright
- Requests
- urllib3
- Threading support

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## � Screenshots

<details>
<summary>Click to expand screenshots</summary>

### Main Menu
![Main Menu](screenshots/main-menu.png)

### Crawling in Action
![Crawling](screenshots/crawling.png)

### Output Structure
![Output](screenshots/output.png)

</details>

## 🚫 Common Issues & Solutions

### SSL Certificate Errors
```python
urllib3.exceptions.InsecureRequestWarning
```
**Solution**: The crawler automatically handles SSL verification. For debugging, you can use:
```python
python CrawlAnything.py --ignore-ssl
```

### Rate Limiting
```
HTTP 429: Too Many Requests
```
**Solution**: Adjust the crawler delay in configuration or reduce parallel workers:
```python
python CrawlAnything.py --delay 2 --workers 5
```

### Memory Usage
For large websites, monitor memory usage:
```bash
# Linux/Mac
top -pid $(pgrep -f CrawlAnything.py)

# Windows
tasklist | findstr "python"
```

## 📊 Performance Tips

1. **Optimize Parallel Processing**
   - Start with 5-10 workers
   - Monitor CPU and memory usage
   - Adjust based on target website's response

2. **Storage Management**
   - Regular cleanup of temporary files
   - Implement data retention policies
   - Use compression for archived content

3. **Network Optimization**
   - Enable connection pooling
   - Implement retry mechanisms
   - Use appropriate timeouts

## 🔗 Contact

- **Creator**: SWEHUL YADAV
- **Email**: Yadav12ahul@gmail.com
- **LinkedIn**: [SWEHUL YADAV]([https://linkedin.com/in/your-profile](https://in.linkedin.com/in/rahul-yadav-swehul))
- **Twitter**: [@YourHandle](https://twitter.com/SWEHULYADAV)

## �🙏 Acknowledgments

- BeautifulSoup4 for HTML parsing
- Playwright for dynamic content
- Python community for inspiration
- All our [contributors](https://github.com/SWEHULYADAV/advanced-website-crawler/graphs/contributors)

## 📈 Project Stats

[![Contributors](https://img.shields.io/github/contributors/SWEHULYADAV/advanced-website-crawler)](https://github.com/SWEHULYADAV/advanced-website-crawler/graphs/contributors)
[![Issues](https://img.shields.io/github/issues/SWEHULYADAV/advanced-website-crawler)](https://github.com/SWEHULYADAV/advanced-website-crawler/issues)
[![PRs](https://img.shields.io/github/issues-pr/SWEHULYADAV/advanced-website-crawler)](https://github.com/SWEHULYADAV/advanced-website-crawler/pulls)

---
<p align="center">
Made with ❤️ by <a href="https://github.com/SWEHULYADAV">SWEHULYADAV</a>
</p>

<p align="center">
If you found this project helpful, please consider giving it a ⭐
</p>
