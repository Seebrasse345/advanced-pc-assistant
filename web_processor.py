import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urlparse
import logging
from datetime import datetime

class WebProcessor:
    def __init__(self, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/97.0.4692.71 Safari/537.36"):
        """Initialize WebProcessor with a default user agent."""
        self.user_agent = user_agent
        self.headers = {
            "User-Agent": user_agent
        }
        
        # Set up logging
        self.logger = logging.getLogger('WebProcessor')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def fetch_url(self, url, timeout=10):
        """Fetch content from a URL."""
        try:
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def extract_text_from_html(self, html_content):
        """Extract clean text from HTML content."""
        if not html_content:
            return None
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "footer", "nav", "aside"]):
            script.extract()
        
        # Get text and clean it
        text = soup.get_text(separator=' ')
        
        # Clean the text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def extract_main_content(self, html_content, url):
        """Extract the main content from an HTML page."""
        if not html_content:
            return None
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove navigation, header, footer, etc.
        for tag in soup.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style', 'noscript']):
            tag.decompose()
        
        # Try to find the main content
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|post|article'))
        
        if main_content:
            text = main_content.get_text(separator=' ')
        else:
            # Fallback to the body if no main content is found
            text = soup.body.get_text(separator=' ') if soup.body else soup.get_text(separator=' ')
        
        # Clean the text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def extract_metadata(self, html_content, url):
        """Extract metadata from HTML content."""
        if not html_content:
            return {}
            
        metadata = {
            "url": url,
            "domain": urlparse(url).netloc,
            "fetched_at": datetime.now().isoformat()
        }
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            metadata["title"] = title_tag.string.strip()
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            metadata["description"] = meta_desc['content'].strip()
        
        # Extract meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            metadata["keywords"] = meta_keywords['content'].strip()
        
        # Extract Open Graph metadata
        og_title = soup.find('meta', property='og:title')
        if og_title:
            metadata["og_title"] = og_title.get('content', '')
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            metadata["og_description"] = og_desc.get('content', '')
        
        return metadata
    
    def process_url(self, url):
        """Process a URL and extract content and metadata."""
        html_content = self.fetch_url(url)
        if not html_content:
            return None
        
        # Extract content
        main_content = self.extract_main_content(html_content, url)
        
        # Extract metadata
        metadata = self.extract_metadata(html_content, url)
        
        # Determine title
        title = metadata.get("title") or metadata.get("og_title") or url
        
        return {
            "title": title,
            "content": main_content,
            "source": url,
            "metadata": metadata
        }
    
    def extract_links(self, html_content, base_url):
        """Extract links from HTML content."""
        if not html_content:
            return []
            
        soup = BeautifulSoup(html_content, 'html.parser')
        base_domain = urlparse(base_url).netloc
        
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Skip empty links and javascript
            if not href or href.startswith('javascript:') or href == "#":
                continue
            
            # Handle relative URLs
            if href.startswith('/'):
                parsed_base = urlparse(base_url)
                href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            elif not href.startswith(('http://', 'https://')):
                if not base_url.endswith('/'):
                    base_url += '/'
                href = f"{base_url}{href}"
            
            # Only include links to the same domain
            link_domain = urlparse(href).netloc
            if link_domain == base_domain:
                links.append(href)
        
        return links
    
    def process_url_with_links(self, url, include_links=False):
        """Process a URL and optionally extract links."""
        html_content = self.fetch_url(url)
        if not html_content:
            return None
        
        result = self.process_url(url)
        
        if include_links:
            result["links"] = self.extract_links(html_content, url)
        
        return result 