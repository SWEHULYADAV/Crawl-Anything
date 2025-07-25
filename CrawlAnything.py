import requests
from urllib.parse import urlparse, urljoin, urlunparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import csv
import os
import json
import re
from datetime import datetime
import urllib.request
from pathlib import Path
import urllib3
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from queue import Queue

# Disable SSL warnings for problematic sites
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

visited_urls = set()  # unified set for all crawled URLs
json_data = []
lock = threading.Lock()  # Thread lock for thread-safe operations

def normalize_url(url):
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    normalized = urlunparse((scheme, netloc, path, "", "", ""))
    return normalized

def is_valid(url, base_domain):
    parsed = urlparse(url)
    return parsed.scheme in ["http", "https"] and base_domain in parsed.netloc

def can_fetch(robot_parser, url):
    try:
        # If robots.txt couldn't be loaded, allow crawling
        if not hasattr(robot_parser, '_RobotFileParser__entries') or not robot_parser._RobotFileParser__entries:
            return True
        return robot_parser.can_fetch("*", url)
    except:
        return True  # Allow crawling if there's any error checking robots.txt

def init_robot_parser(base_url):
    robots_url = urljoin(base_url, "/robots.txt")
    rp = RobotFileParser()
    try:
        # Use requests with better headers and timeout for robots.txt
        response = requests.get(robots_url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/plain,*/*;q=0.8",
            "Connection": "keep-alive"
        }, verify=False)
        
        if response.status_code == 200:
            # Create a temporary file to load robots.txt content
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
                temp_file.write(response.text)
                temp_path = temp_file.name
            
            rp.set_url(f"file:///{temp_path.replace(os.sep, '/')}")  # Use proper file URL format
            rp.read()
            os.unlink(temp_path)  # Clean up temp file
            print(f"[✓] Loaded robots.txt from {robots_url}")
        else:
            print(f"[!] robots.txt returned {response.status_code}, proceeding without restrictions")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print(f"[!] Connection issue with robots.txt (site may block bots)")
        print("[+] Proceeding without robots.txt restrictions...")
    except Exception as e:
        print(f"[!] Could not load robots.txt: {str(e)[:100]}")
        print("[+] Proceeding without robots.txt restrictions...")
    return rp

def generate_filename(url, include_timestamp=True):
    # Extract domain and path for filename
    parsed = urlparse(url)
    domain_parts = parsed.netloc.split('.')
    clean_domain = domain_parts[1] if len(domain_parts) > 2 else domain_parts[0]
    
    # Clean path
    path_part = parsed.path.strip('/').replace('/', '_')
    if not path_part:
        path_part = "home"
    
    # Remove invalid characters
    clean_path = re.sub(r'[^\w\-_]', '_', path_part)
    
    if include_timestamp:
        # Create timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{clean_domain}_{clean_path}_{timestamp}"
    else:
        return f"{clean_domain}_{clean_path}"

def download_media(url, folder_path, media_type="image"):
    """Download image or video from URL"""
    try:
        # Skip data URLs (base64 embedded content)
        if url.startswith('data:'):
            print(f"[!] Skipping data URL (base64 embedded): {url[:50]}...")
            return None
            
        # Skip very short or invalid URLs
        if len(url) < 10 or not url.startswith(('http://', 'https://')):
            print(f"[!] Skipping invalid URL: {url}")
            return None
        
        response = requests.get(url, stream=True, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }, allow_redirects=True, verify=False)
        
        if response.status_code == 200:
            # Get file extension from URL or content type
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            
            if not filename or '.' not in filename:
                # Generate filename from URL hash if no proper filename
                content_type = response.headers.get('content-type', '').lower()
                if 'image' in content_type:
                    ext = content_type.split('/')[-1].split(';')[0]
                    if ext in ['jpeg', 'jpg', 'png', 'gif', 'webp', 'svg+xml']:
                        if ext == 'svg+xml':
                            ext = 'svg'
                        filename = f"{media_type}_{abs(hash(url)) % 100000}.{ext}"
                elif 'video' in content_type:
                    ext = content_type.split('/')[-1].split(';')[0]
                    if ext in ['mp4', 'webm', 'ogg', 'avi']:
                        filename = f"{media_type}_{abs(hash(url)) % 100000}.{ext}"
                
                if not filename or '.' not in filename:
                    # Extract extension from URL path
                    url_path = parsed_url.path.lower()
                    if any(ext in url_path for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']):
                        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
                            if ext in url_path:
                                filename = f"{media_type}_{abs(hash(url)) % 100000}{ext}"
                                break
                    else:
                        filename = f"{media_type}_{abs(hash(url)) % 100000}.bin"
            
            # Clean filename
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            file_path = os.path.join(folder_path, filename)
            
            # Check if file already exists
            if os.path.exists(file_path):
                print(f"[!] File already exists: {filename}")
                return file_path
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    f.flush()  # Force write to disk immediately
                
            # Ensure file is completely written
            os.fsync(open(file_path, 'rb').fileno()) if os.path.exists(file_path) else None
            
            print(f"[✓] Downloaded {media_type}: {filename}")
            return file_path
        else:
            print(f"[!] HTTP {response.status_code} for {media_type}: {url}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"[!] Connection error for {media_type} {url}: Network issue")
    except requests.exceptions.Timeout as e:
        print(f"[!] Timeout downloading {media_type}: {url}")
    except requests.exceptions.RequestException as e:
        print(f"[!] Request error for {media_type} {url}: {str(e)[:100]}")
    except Exception as e:
        print(f"[!] Failed to download {media_type} from {url}: {str(e)[:100]}")
    return None

def init_csv_writer(base_filename, folder_path=None):
    if folder_path:
        os.makedirs(folder_path, exist_ok=True)
        filepath = os.path.join(folder_path, f"{base_filename}.csv")
    else:
        os.makedirs("output", exist_ok=True)
        filepath = os.path.join("output", f"{base_filename}.csv")
    f = open(filepath, "w", newline="", encoding="utf-8")
    writer = csv.writer(f)
    writer.writerow(["URL"])
    return f, writer, filepath

def init_json_file(base_filename, folder_path=None):
    if folder_path:
        os.makedirs(folder_path, exist_ok=True)
        filepath = os.path.join(folder_path, f"{base_filename}.json")
    else:
        os.makedirs("output", exist_ok=True)
        filepath = os.path.join("output", f"{base_filename}.json")
    # Start with empty list in file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)
    return filepath

def append_json(filepath, item):
    # Read current data
    with lock:  # Thread-safe JSON writing
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = []

        data.append(item)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()  # Force write to disk immediately
        
        # Ensure file is completely written to disk
        try:
            with open(filepath, 'r') as f:
                os.fsync(f.fileno())
        except:
            pass

def write_url(writer, file, url):
    norm_url = normalize_url(url)
    with lock:  # Thread-safe writing
        if norm_url not in visited_urls:
            visited_urls.add(norm_url)
            writer.writerow([norm_url])
            file.flush()
            print(f"[✓] Saved URL: {norm_url}")

def extract_metadata(soup, base_url, html_source="", media_folder=None, download_media_flag=False):
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_desc_tag = soup.find("meta", attrs={"name":"description"})
    meta_desc = meta_desc_tag["content"].strip() if meta_desc_tag and meta_desc_tag.get("content") else ""
    
    # Save both HTML source code and text content
    if html_source:
        try:
            # Use the media_folder as the base folder for all content
            base_folder = media_folder if media_folder else os.path.join("output", generate_filename(base_url))
            os.makedirs(base_folder, exist_ok=True)
            
            # Create subfolders for different types of content
            source_folder = os.path.join(base_folder, "source")
            os.makedirs(source_folder, exist_ok=True)
            os.makedirs(os.path.join(source_folder, "html"), exist_ok=True)
            os.makedirs(os.path.join(source_folder, "js"), exist_ok=True)
            os.makedirs(os.path.join(source_folder, "css"), exist_ok=True)
            text_folder = os.path.join(base_folder, "text")
            os.makedirs(text_folder, exist_ok=True)
            
            # Generate base filename without timestamp for cleaner structure
            parsed = urlparse(base_url)
            page_name = parsed.path.strip('/').replace('/', '_') or "home"
            base_filename = re.sub(r'[^\w\-_]', '_', page_name)
            
            # Save full HTML source code
            html_file_path = os.path.join(source_folder, "html", f"{base_filename}.html")
            with open(html_file_path, 'w', encoding='utf-8') as f:
                f.write(html_source)
            print(f"[✓] Saved HTML source code to: {html_file_path}")
            
            # Extract and save JavaScript code
            script_count = 0
            for script in soup.find_all("script"):
                if script.string:  # Only save scripts with content
                    script_count += 1
                    js_file_path = os.path.join(source_folder, "js", f"{base_filename}_script_{script_count}.js")
                    with open(js_file_path, 'w', encoding='utf-8') as f:
                        f.write(script.string)
            if script_count > 0:
                print(f"[✓] Saved {script_count} JavaScript files")
                
            # Extract and save CSS code
            style_count = 0
            for style in soup.find_all("style"):
                if style.string:  # Only save styles with content
                    style_count += 1
                    css_file_path = os.path.join(source_folder, "css", f"{base_filename}_style_{style_count}.css")
                    with open(css_file_path, 'w', encoding='utf-8') as f:
                        f.write(style.string)
            
            # Save external CSS links
            for link in soup.find_all("link", rel="stylesheet"):
                href = link.get("href")
                if href:
                    style_count += 1
                    css_file_path = os.path.join(source_folder, "css", f"{base_filename}_external_{style_count}.css")
                    try:
                        css_url = urljoin(base_url, href)
                        css_response = requests.get(css_url, timeout=10)
                        if css_response.status_code == 200:
                            with open(css_file_path, 'w', encoding='utf-8') as f:
                                f.write(css_response.text)
                    except:
                        pass
            if style_count > 0:
                print(f"[✓] Saved {style_count} CSS files")
            
            # Extract and save text content
            text_content = soup.get_text(separator='\n', strip=True)
            text_file_path = os.path.join(text_folder, f"{base_filename}.txt")
            with open(text_file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            print(f"[✓] Saved text content to: {text_file_path}")
            
        except Exception as e:
            print(f"[!] Error saving page content: {str(e)[:100]}")
            
            # Extract headings but filter out very long ones (likely misused as content)
    h1_tags = []
    for h1 in soup.find_all("h1"):
        text = h1.get_text(strip=True)
        if text and len(text) <= 200:  # Reasonable heading length
            h1_tags.append(text)
    
    h2_tags = []
    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True)
        if text and len(text) <= 150:  # Reasonable heading length
            h2_tags.append(text)
    
    h3_tags = []
    for h3 in soup.find_all("h3"):
        text = h3.get_text(strip=True)
        if text and len(text) <= 100:  # Shorter limit for h3
            h3_tags.append(text)
    
    # Get main content (first few paragraphs)
    paragraphs = []
    for p in soup.find_all("p")[:5]:  # First 5 paragraphs
        text = p.get_text(strip=True)
        if text and len(text) > 20:  # Only meaningful paragraphs
            paragraphs.append(text)
    
    # Get images with download option
    images = []
    downloaded_images = []
    print(f"[+] Found {len(soup.find_all('img'))} images on page")
    for img in soup.find_all("img"):
        img_src = img.get("src")
        img_alt = img.get("alt", "").strip()
        
        if img_src:
            # Convert relative URLs to absolute
            img_url = urljoin(base_url, img_src)
            img_info = {
                "url": img_url,
                "alt": img_alt,
                "width": img.get("width", ""),
                "height": img.get("height", "")
            }
            images.append(img_info)
            
            # Download image if requested
            if download_media_flag and media_folder:
                print(f"[+] Attempting to download image: {img_url}")
                downloaded_path = download_media(img_url, media_folder, "image")
                if downloaded_path:
                    img_info["downloaded_path"] = downloaded_path
                    downloaded_images.append(downloaded_path)
                    print(f"[✓] Image saved to: {downloaded_path}")
    
    # Get videos with download option
    videos = []
    downloaded_videos = []
    print(f"[+] Found {len(soup.find_all('video'))} videos on page")
    for video in soup.find_all("video"):
        video_src = video.get("src")
        if not video_src:
            # Check for source tags inside video
            source_tag = video.find("source")
            if source_tag:
                video_src = source_tag.get("src")
        
        if video_src:
            # Convert relative URLs to absolute
            video_url = urljoin(base_url, video_src)
            video_info = {
                "url": video_url,
                "width": video.get("width", ""),
                "height": video.get("height", ""),
                "controls": video.get("controls") is not None,
                "autoplay": video.get("autoplay") is not None
            }
            videos.append(video_info)
            
            # Download video if requested
            if download_media_flag and media_folder:
                print(f"[+] Attempting to download video: {video_url}")
                downloaded_path = download_media(video_url, media_folder, "video")
                if downloaded_path:
                    video_info["downloaded_path"] = downloaded_path
                    downloaded_videos.append(downloaded_path)
                    print(f"[✓] Video saved to: {downloaded_path}")
    
    # Detect streaming links and embedded players
    streaming_links = []
    
    # 1. Look for iframe sources (embedded players)
    for iframe in soup.find_all("iframe"):
        iframe_src = iframe.get("src")
        if iframe_src:
            iframe_url = urljoin(base_url, iframe_src)
            streaming_links.append({
                "type": "iframe_embed",
                "url": iframe_url,
                "width": iframe.get("width", ""),
                "height": iframe.get("height", ""),
                "title": iframe.get("title", "")
            })
    
    # 2. Look for streaming server links (Server 1, 2, 3, etc.)
    streaming_servers = []
    for link in soup.find_all("a", href=True):
        link_text = link.get_text(strip=True).lower()
        link_url = urljoin(base_url, link["href"])
        
        # Detect server links by text patterns
        server_patterns = [
            r'server\s*\d+', r'watch\s*link\s*\d+', r'video\s*\d+',
            r'stream\s*\d+', r'player\s*\d+', r'link\s*\d+',
            r'hd\s*link', r'live\s*stream', r'watch\s*now',
            r'play\s*now', r'stream\s*now'
        ]
        
        for pattern in server_patterns:
            if re.search(pattern, link_text):
                streaming_servers.append({
                    "text": link.get_text(strip=True),
                    "url": link_url,
                    "type": "streaming_server"
                })
                break
    
    # 3. Extract streaming URLs from JavaScript and text content
    live_streams = []
    page_text = str(soup)
    
    # Look for common streaming formats in page source
    stream_patterns = {
        "m3u8": r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
        "mpd": r'https?://[^\s"\'<>]+\.mpd[^\s"\'<>]*', 
        "rtmp": r'rtmp://[^\s"\'<>]+',
        "hls": r'https?://[^\s"\'<>]+/playlist\.m3u8[^\s"\'<>]*',
        "dash": r'https?://[^\s"\'<>]+manifest\.mpd[^\s"\'<>]*'
    }
    
    for stream_type, pattern in stream_patterns.items():
        matches = re.findall(pattern, page_text, re.IGNORECASE)
        for match in set(matches):  # Remove duplicates
            live_streams.append({
                "type": stream_type,
                "url": match.strip('"\'<>')
            })
    
    # 4. Look for embedded video URLs in data attributes
    embedded_videos = []
    for element in soup.find_all(attrs={"data-src": True}):
        data_src = element.get("data-src")
        if data_src and any(ext in data_src.lower() for ext in ['.mp4', '.webm', '.ogg', '.m3u8', '.mpd']):
            embedded_videos.append({
                "type": "data_src_video",
                "url": urljoin(base_url, data_src),
                "element": element.name
            })
    
    # 5. Look for JavaScript variables containing video URLs
    js_video_urls = []
    script_tags = soup.find_all("script")
    for script in script_tags:
        if script.string:
            # Look for common variable patterns
            js_patterns = [
                r'videoUrl\s*[=:]\s*["\']([^"\']+)["\']',
                r'streamUrl\s*[=:]\s*["\']([^"\']+)["\']',
                r'playerUrl\s*[=:]\s*["\']([^"\']+)["\']',
                r'src\s*[=:]\s*["\']([^"\']+\.(?:mp4|m3u8|mpd))["\']'
            ]
            
            for pattern in js_patterns:
                matches = re.findall(pattern, script.string, re.IGNORECASE)
                for match in matches:
                    js_video_urls.append({
                        "type": "javascript_video",
                        "url": urljoin(base_url, match)
                    })
    
    # Get navigation/menu items
    nav_items = []
    for nav in soup.find_all(['nav', 'ul']):
        for link in nav.find_all('a'):
            link_text = link.get_text(strip=True)
            if link_text and len(link_text) <= 50:  # Short navigation items
                nav_items.append(link_text)
    
    return {
        "title": title,
        "meta_description": meta_desc,
        "h1_headings": h1_tags,
        "h2_headings": h2_tags, 
        "h3_headings": h3_tags,
        "paragraphs": paragraphs,
        "images": images,
        "videos": videos,
        "streaming_links": streaming_links,
        "streaming_servers": streaming_servers,
        "live_streams": live_streams,
        "embedded_videos": embedded_videos,
        "javascript_videos": js_video_urls,
        "navigation_items": list(set(nav_items))[:10],  # Unique nav items, max 10
        "downloaded_images": downloaded_images,
        "downloaded_videos": downloaded_videos
    }

def process_sitemap_url(url_data):
    """Process single sitemap URL for parallel processing"""
    url, robot_parser, media_folder, download_media_flag = url_data
    
    norm_url = normalize_url(url)
    
    # Check if already processed
    with lock:
        if norm_url in visited_urls:
            return None
    
    if not is_valid(norm_url, urlparse(url).netloc) or not can_fetch(robot_parser, norm_url):
        return None
    
    # Skip non-HTML files
    if any(ext in norm_url.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.css', '.js', '.xml']):
        with lock:
            visited_urls.add(norm_url)
        return {"url": norm_url, "type": "resource", "source": "sitemap"}
    
    # Extract full content for HTML pages
    try:
        print(f"[+] Extracting content from: {norm_url}")
        page_response = requests.get(norm_url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        }, verify=False)
        
        if page_response.status_code == 200:
            page_soup = BeautifulSoup(page_response.text, "html.parser")
            metadata = extract_metadata(page_soup, norm_url, page_response.text, media_folder, download_media_flag)
            
            with lock:
                visited_urls.add(norm_url)
            
            data_entry = {"url": norm_url, "source": "sitemap"}
            data_entry.update(metadata)
            print(f"[✓] Content extracted from: {norm_url}")
            return data_entry
        else:
            print(f"[!] Failed to load {norm_url}: HTTP {page_response.status_code}")
            with lock:
                visited_urls.add(norm_url)
            return {"url": norm_url, "source": "sitemap", "error": f"HTTP {page_response.status_code}"}
            
    except Exception as e:
        print(f"[!] Error extracting content from {norm_url}: {str(e)[:100]}")
        with lock:
            visited_urls.add(norm_url)
        return {"url": norm_url, "source": "sitemap", "error": str(e)[:100]}

def extract_sitemap(base_url, writer, file, robot_parser, json_path, media_folder=None, download_media_flag=False):
    print("[+] Checking sitemap.xml...")
    urls = []
    sitemap_url = urljoin(base_url, "/sitemap.xml")
    try:
        response = requests.get(sitemap_url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/xml,text/xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        }, verify=False)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "xml")
            locs = [loc.text for loc in soup.find_all("loc")]
            print(f"[+] Found {len(locs)} URLs in sitemap, extracting content in parallel...")
            
            # Prepare data for parallel processing
            url_data_list = [(url, robot_parser, media_folder, download_media_flag) for url in locs]
            
            # Process URLs in parallel with controlled concurrency
            max_workers = min(10, len(locs))  # Max 10 parallel workers
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_url = {executor.submit(process_sitemap_url, url_data): url_data[0] 
                               for url_data in url_data_list}
                
                for future in as_completed(future_to_url):
                    result = future.result()
                    if result:
                        write_url(writer, file, result["url"])
                        append_json(json_path, result)
                        urls.append(result["url"])
                        
            print(f"[✓] {len(urls)} URLs processed from sitemap in parallel.")
        else:
            print(f"[!] sitemap.xml returned {response.status_code} - not available")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print("[!] Connection issue with sitemap.xml (site may block or not have sitemap)")
    except Exception as e:
        print(f"[!] Error fetching sitemap: {str(e)[:100]}")
    return urls

def crawl_single_url(url_data):
    """Process a single URL for parallel crawling"""
    url, base_domain, robot_parser, json_path, media_folder, download_media_flag = url_data
    
    norm_url = normalize_url(url)
    
    # Check if already visited (thread-safe)
    with lock:
        if norm_url in visited_urls:
            return None
    
    if not can_fetch(robot_parser, norm_url):
        print(f"[!] Disallowed by robots.txt: {norm_url}")
        return None
    
    try:
        res = requests.get(norm_url, timeout=25, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }, allow_redirects=True, verify=False)
        
        if res.status_code != 200:
            print(f"[!] Parallel crawl failed with status {res.status_code}: {norm_url}")
            return None
            
        soup = BeautifulSoup(res.text, "html.parser")
        metadata = extract_metadata(soup, norm_url, res.text, media_folder, download_media_flag)
        
        # Thread-safe addition to visited URLs
        with lock:
            visited_urls.add(norm_url)
        
        data_entry = {"url": norm_url, "source": "parallel_static"}
        data_entry.update(metadata)
        append_json(json_path, data_entry)
        
        print(f"[✓] Parallel crawl completed: {norm_url}")
        
        # Extract new links
        new_links = []
        for tag in soup.find_all("a", href=True):
            link = urljoin(norm_url, tag["href"])
            link_norm = normalize_url(link)
            if is_valid(link_norm, base_domain):
                with lock:
                    if link_norm not in visited_urls:
                        new_links.append(link_norm)
        
        return {"url": norm_url, "new_links": new_links}
        
    except requests.exceptions.ConnectionError as e:
        print(f"[!] Connection error at {norm_url}: Network/server issue")
    except requests.exceptions.Timeout as e:
        print(f"[!] Timeout error at {norm_url}: Server too slow")
    except Exception as e:
        print(f"[!] Parallel crawl error at {norm_url}: {str(e)[:100]}")
    
    return None

def crawl_static_parallel(url, base_domain, writer, file, robot_parser, json_path, media_folder=None, download_media_flag=False, max_workers=5):
    """Parallel static crawling with threading"""
    print(f"[+] Starting parallel static crawl with {max_workers} workers...")
    
    urls_to_crawl = Queue()
    urls_to_crawl.put(url)
    
    total_crawled = 0
    batch_size = max_workers * 2  # Process URLs in batches
    
    while not urls_to_crawl.empty():
        # Prepare batch of URLs
        current_batch = []
        batch_count = 0
        
        while not urls_to_crawl.empty() and batch_count < batch_size:
            current_url = urls_to_crawl.get()
            current_batch.append((
                current_url, base_domain, robot_parser, json_path, 
                media_folder, download_media_flag
            ))
            batch_count += 1
        
        if not current_batch:
            break
            
        print(f"[+] Processing batch of {len(current_batch)} URLs...")
        
        # Process batch in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(crawl_single_url, url_data): url_data[0] 
                           for url_data in current_batch}
            
            for future in as_completed(future_to_url):
                result = future.result()
                if result:
                    # Write URL to CSV (thread-safe)
                    write_url(writer, file, result["url"])
                    total_crawled += 1
                    
                    # Add new discovered links to queue
                    for new_link in result["new_links"]:
                        urls_to_crawl.put(new_link)
        
        print(f"[✓] Batch completed. Total crawled: {total_crawled}")
        
        # Small delay to prevent overwhelming the server
        time.sleep(1)
    
    print(f"[✓] Parallel static crawl completed. Total URLs crawled: {total_crawled}")

def batch_process_urls(input_file="input_urls.txt", max_workers=5):
    """Process multiple URLs from a file in parallel"""
    print("=== Batch URL Processing ===")
    
    if not os.path.exists(input_file):
        print(f"[!] Input file {input_file} not found!")
        return
    
    # Read URLs from file
    with open(input_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    if not urls:
        print("[!] No valid URLs found in input file!")
        return
    
    print(f"[+] Found {len(urls)} URLs to process")
    
    # Ask for options
    download_media_input = input("Download images and videos for all sites? (y/n, default: n): ").strip().lower()
    download_media_flag = download_media_input == 'y'
    
    workers_input = input(f"Number of parallel workers (1-10, default: {max_workers}): ").strip()
    try:
        max_workers = max(1, min(10, int(workers_input)))
    except:
        pass
    
    print(f"[+] Processing {len(urls)} URLs with {max_workers} parallel workers")
    
    # Process each URL
    for i, url in enumerate(urls, 1):
        print(f"\n[+] Processing URL {i}/{len(urls)}: {url}")
        
        try:
            # Add https if no scheme provided
            if not urlparse(url).scheme:
                url = "https://" + url
            
            domain = urlparse(url).netloc
            base_filename = generate_filename(url)
            output_folder = os.path.join("batch_output", base_filename)
            os.makedirs(output_folder, exist_ok=True)
            
            media_folder = output_folder if download_media_flag else None
            
            # Initialize files and parsers
            robot_parser = init_robot_parser(url)
            csv_file, writer, csv_path = init_csv_writer(base_filename, output_folder)
            json_path = init_json_file(base_filename, output_folder)
            
            # Clear visited URLs for each new site
            global visited_urls
            visited_urls.clear()
            
            start_time = time.time()
            
            # Quick parallel crawl
            sitemap_urls = extract_sitemap(url, writer, csv_file, robot_parser, json_path, media_folder, download_media_flag)
            crawl_static_parallel(url, domain, writer, csv_file, robot_parser, json_path, media_folder, download_media_flag, max_workers)
            
            elapsed = time.time() - start_time
            print(f"[✓] Completed {url} in {elapsed:.2f} seconds ({len(visited_urls)} URLs)")
            
            csv_file.close()
            
        except Exception as e:
            print(f"[!] Error processing {url}: {str(e)[:100]}")
            continue
    
    print(f"\n[✓] Batch processing completed for {len(urls)} URLs")

def crawl_static(url, base_domain, writer, file, robot_parser, json_path, media_folder=None, download_media_flag=False):
    norm_url = normalize_url(url)
    if norm_url in visited_urls:
        return
    if not can_fetch(robot_parser, norm_url):
        print(f"[!] Disallowed by robots.txt: {norm_url}")
        return
    try:
        res = requests.get(norm_url, timeout=25, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }, allow_redirects=True, verify=False)
        
        if res.status_code != 200:
            print(f"[!] Static crawl failed with status {res.status_code}: {norm_url}")
            return
        soup = BeautifulSoup(res.text, "html.parser")
        metadata = extract_metadata(soup, norm_url, media_folder, download_media_flag)
        write_url(writer, file, norm_url)
        
        data_entry = {"url": norm_url, "source": "static"}
        data_entry.update(metadata)
        append_json(json_path, data_entry)
        
        for tag in soup.find_all("a", href=True):
            link = urljoin(norm_url, tag["href"])
            link_norm = normalize_url(link)
            if is_valid(link_norm, base_domain) and link_norm not in visited_urls:
                crawl_static(link_norm, base_domain, writer, file, robot_parser, json_path, media_folder, download_media_flag)
    except requests.exceptions.ConnectionError as e:
        print(f"[!] Connection error at {norm_url}: Network/server issue")
    except requests.exceptions.Timeout as e:
        print(f"[!] Timeout error at {norm_url}: Server too slow")
    except Exception as e:
        print(f"[!] Static crawl error at {norm_url}: {str(e)[:100]}")

def crawl_dynamic(start_url, base_domain, writer, file, robot_parser, json_path, headless=True, media_folder=None, download_media_flag=False):
    print("[+] Crawling dynamic pages (JavaScript)...")
    to_visit = [normalize_url(start_url)]
    with sync_playwright() as p:
        # Launch browser with better options for streaming sites
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # Skip images for faster loading
                '--disable-javascript-harmony-shipping',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        page = context.new_page()
        
        # Intercept network requests to capture streaming URLs
        streaming_requests = []
        def handle_request(request):
            url = request.url
            # Look for streaming formats in network requests
            if any(ext in url.lower() for ext in ['.m3u8', '.mpd', '.ts', 'manifest']):
                streaming_requests.append({
                    "type": "network_stream",
                    "url": url,
                    "method": request.method,
                    "resource_type": request.resource_type
                })
        
        page.on("request", handle_request)
        
        while to_visit:
            url = to_visit.pop()
            if url in visited_urls:
                continue
            if not can_fetch(robot_parser, url):
                print(f"[!] Disallowed by robots.txt: {url}")
                continue
            try:
                # Clear previous streaming requests
                streaming_requests.clear()
                
                # Increase timeout for problematic sites like VIPBox
                page.goto(url, timeout=30000)  # 30 seconds instead of 1 second
                page.wait_for_timeout(5000)  # Wait longer for JS to load
                
                # Try to click on streaming server links to reveal hidden URLs
                try:
                    # Look for server/player buttons and click them
                    server_selectors = [
                        'a[href*="server"]', 'button[class*="server"]',
                        'a[href*="player"]', 'button[class*="player"]',
                        'a[href*="stream"]', 'button[class*="stream"]',
                        '.server-link', '.player-btn', '.stream-btn'
                    ]
                    
                    for selector in server_selectors:
                        try:
                            elements = page.query_selector_all(selector)
                            for element in elements[:3]:  # Click first 3 server links
                                if element:
                                    element.click()
                                    page.wait_for_timeout(2000)  # Wait for content to load
                        except:
                            continue
                
                except Exception as e:
                    print(f"[!] Error clicking streaming links: {e}")
                
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                metadata = extract_metadata(soup, url, html, media_folder, download_media_flag)
                
                # Add network-captured streaming URLs
                if streaming_requests:
                    if "network_streams" not in metadata:
                        metadata["network_streams"] = []
                    metadata["network_streams"].extend(streaming_requests)
                
                write_url(writer, file, url)
                
                data_entry = {"url": url, "source": "dynamic"}
                data_entry.update(metadata)
                append_json(json_path, data_entry)
                
                for tag in soup.find_all("a", href=True):
                    link = urljoin(url, tag["href"])
                    link_norm = normalize_url(link)
                    if is_valid(link_norm, base_domain) and link_norm not in visited_urls:
                        to_visit.append(link_norm)
            except Exception as e:
                print(f"[!] Dynamic crawl error at {url}: {e}")
        browser.close()
    print(f"[✓] {len(visited_urls)} total unique URLs found.")

def main():
    print("=== Website Crawler ===")
    print("Enter the website URL to crawl:")
    
    # Get URL from user input
    base_url = input("URL: ").strip()
    if not base_url:
        print("Error: No URL provided")
        return
    
    # Add https if no scheme provided
    if not urlparse(base_url).scheme:
        base_url = "https://" + base_url
    
    domain = urlparse(base_url).netloc
    print(f"Starting crawl for: {base_url}")
    
    # Generate filenames based on URL and timestamp
    base_filename = generate_filename(base_url)
    
    # Ask user for crawling options
    headless_input = input("Run browser in headless mode? (y/n, default: y): ").strip().lower()
    headless = headless_input != 'n'
    
    # Ask user for parallel processing
    parallel_input = input("Enable parallel processing for faster crawling? (y/n, default: y): ").strip().lower()
    use_parallel = parallel_input != 'n'
    
    # Ask for number of parallel workers if parallel is enabled
    max_workers = 5  # default
    if use_parallel:
        workers_input = input("Number of parallel workers (1-20, default: 5): ").strip()
        try:
            max_workers = max(1, min(20, int(workers_input)))
        except:
            max_workers = 5
        print(f"[+] Using {max_workers} parallel workers")
    
    # Ask user for media download option
    download_media_input = input("Download images and videos? (y/n, default: n): ").strip().lower()
    download_media_flag = download_media_input == 'y'
    
    # Create main folder for this URL's content
    site_folder = os.path.join("output", generate_filename(base_url, include_timestamp=False))
    os.makedirs(site_folder, exist_ok=True)
    
    # Create subfolders for different types of content
    media_folder = os.path.join(site_folder, "media") if download_media_flag else None
    if media_folder:
        os.makedirs(media_folder, exist_ok=True)
    
    # Initialize files and parsers
    robot_parser = init_robot_parser(base_url)
    csv_file, writer, csv_path = init_csv_writer(base_filename, site_folder)
    json_path = init_json_file(base_filename, site_folder)
    
    print(f"[+] All content will be saved to: {site_folder}")
    if media_folder:
        print(f"[+] Media files will be saved to: {media_folder}")
    
    # Extract sitemap URLs with full content (now parallel)
    start_time = time.time()
    sitemap_urls = extract_sitemap(base_url, writer, csv_file, robot_parser, json_path, media_folder, download_media_flag)
    sitemap_time = time.time() - start_time
    print(f"[✓] Sitemap processing completed in {sitemap_time:.2f} seconds")

    # Static crawl (parallel or sequential based on user choice)
    start_time = time.time()
    if use_parallel:
        print(f"[+] Starting parallel static crawl with {max_workers} workers...")
        crawl_static_parallel(base_url, domain, writer, csv_file, robot_parser, json_path, media_folder, download_media_flag, max_workers)
    else:
        print("[+] Starting sequential static crawl...")
        crawl_static(base_url, domain, writer, csv_file, robot_parser, json_path, media_folder, download_media_flag)
    static_time = time.time() - start_time
    print(f"[✓] Static crawl completed in {static_time:.2f} seconds")

    # Dynamic crawl
    start_time = time.time()
    print("[+] Starting dynamic crawl...")
    crawl_dynamic(base_url, domain, writer, csv_file, robot_parser, json_path, headless, media_folder, download_media_flag)
    dynamic_time = time.time() - start_time
    print(f"[✓] Dynamic crawl completed in {dynamic_time:.2f} seconds")

    total_time = sitemap_time + static_time + dynamic_time
    print(f"\n[✓] Crawl finished in {total_time:.2f} seconds total.")
    print(f"    - Sitemap: {sitemap_time:.2f}s")
    print(f"    - Static: {static_time:.2f}s") 
    print(f"    - Dynamic: {dynamic_time:.2f}s")
    print(f"CSV saved to: {csv_path}")
    print(f"JSON saved to: {json_path}")
    print(f"Total unique URLs found: {len(visited_urls)}")
    
    print(f"\n[✓] All files have been saved to: {site_folder}")
    csv_file.close()

def crawl_single_page(url, download_media_flag=False):
    """Crawl only a single page without following links"""
    print(f"\n[+] Crawling single page: {url}")
    
    if not urlparse(url).scheme:
        url = "https://" + url
    
    domain = urlparse(url).netloc
    base_filename = generate_filename(url)
    
    # Create folder structure
    site_folder = os.path.join("output", generate_filename(url, include_timestamp=False))
    os.makedirs(site_folder, exist_ok=True)
    
    # Setup media folder if needed
    media_folder = os.path.join(site_folder, "media") if download_media_flag else None
    if media_folder:
        os.makedirs(media_folder, exist_ok=True)
    
    # Initialize files
    robot_parser = init_robot_parser(url)
    csv_file, writer, csv_path = init_csv_writer(base_filename, site_folder)
    json_path = init_json_file(base_filename, site_folder)
    
    try:
        print("[+] Fetching page content...")
        response = requests.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        }, verify=False)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            metadata = extract_metadata(soup, url, response.text, media_folder, download_media_flag)
            
            write_url(writer, csv_file, url)
            data_entry = {"url": url, "source": "single_page"}
            data_entry.update(metadata)
            append_json(json_path, data_entry)
            
            print(f"\n[✓] Page crawled successfully")
            print(f"[✓] Files saved to: {site_folder}")
            if media_folder:
                print(f"[✓] Media saved to: {media_folder}")
        else:
            print(f"[!] Failed to fetch page: HTTP {response.status_code}")
        
    except Exception as e:
        print(f"[!] Error crawling page: {str(e)[:100]}")
    finally:
        csv_file.close()

if __name__ == "__main__":
    print("=== Advanced Website Crawler ===")
    print("1. Single URL crawling (whole site)")
    print("2. Batch URL processing from file")
    print("3. Single page crawling (no link following)")
    
    choice = input("Select option (1, 2, or 3, default: 1): ").strip()
    
    if choice == "2":
        batch_process_urls()
    elif choice == "3":
        url = input("Enter the URL to crawl: ").strip()
        if url:
            media_choice = input("Download images and videos? (y/n, default: n): ").strip().lower()
            download_media = media_choice == 'y'
            crawl_single_page(url, download_media)
        else:
            print("Error: No URL provided")
    else:
        main()
