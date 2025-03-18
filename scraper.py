import subprocess
import sys
import time
import os
from mitmproxy import http
import json
from datetime import datetime
import re
import argparse

def run_powershell_command(command):
    completed = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True)
    if completed.returncode != 0:
        print(f"An error occurred: {completed.stderr}")
    return completed.stdout

def set_proxy(enable=True):
    # Skip if not on Windows
    if not sys.platform.startswith('win'):
        print(f"Proxy settings can only be changed on Windows. Current platform: {sys.platform}")
        return

    if enable:
        print("Enabling proxy...")
        command = """
        Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings' -Name ProxyEnable -Value 1
        Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings' -Name ProxyServer -Value '127.0.0.1:8080'
        """
    else:
        print("Disabling proxy...")
        command = """
        Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings' -Name ProxyEnable -Value 0
        """
    
    result = run_powershell_command(command)
    print(result)

def filter_headers(headers):
    important_headers = [
        'content-type', 'content-length', 'authorization', 'cookie',
        'user-agent', 'referer', 'origin', 'host', 'set-cookie'
    ]
    return {k.lower(): v for k, v in headers.items() if k.lower() in important_headers}

def filter_content(content):
    if content is None:
        return None
    content = re.sub(r'<[^>]+>', '', content)
    content = re.sub(r'\s+', ' ', content).strip()
    return content[:1000] + ('...' if len(content) > 1000 else '')

def extract_cookies(headers):
    cookies = headers.get_all('Set-Cookie')
    return [cookie.split(';')[0] for cookie in cookies]

class HTTPLogger:
    def __init__(self, url_filter=None, domain_filter=None):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = os.path.join(os.getcwd(), f"http_log_{timestamp}.json")
        self.url_filter = url_filter.lower() if url_filter else None
        self.domain_filter = domain_filter.lower() if domain_filter else None
        
        # Initialize the log file with an empty array
        with open(self.log_file, 'w') as f:
            f.write('[]')
            
        # Enable proxy (platform-specific)
        set_proxy(True)
        print(f"Logging HTTP requests to {self.log_file}")

    def request(self, flow: http.HTTPFlow):
        pass

    def response(self, flow: http.HTTPFlow):
        try:
            # Check if URL matches filter
            if self.url_filter and self.url_filter not in flow.request.url.lower():
                return
                
            # Check if domain matches filter
            if self.domain_filter:
                domain = flow.request.host.lower()
                if self.domain_filter not in domain:
                    return
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "url": flow.request.url,
                "method": flow.request.method,
                "request_headers": filter_headers(flow.request.headers),
                "request_content": filter_content(flow.request.content.decode('utf-8', 'ignore') if flow.request.content else None),
                "response_headers": filter_headers(flow.response.headers),
                "response_content": filter_content(flow.response.content.decode('utf-8', 'ignore') if flow.response.content else None),
                "status_code": flow.response.status_code,
                "response_cookies": extract_cookies(flow.response.headers)
            }
            
            # Only log if there's content to log
            if log_entry["request_content"] or log_entry["response_content"]:
                # Read the existing log entries
                with open(self.log_file, 'r') as f:
                    try:
                        logs = json.load(f)
                    except json.JSONDecodeError:
                        logs = []
                
                # Append the new entry
                logs.append(log_entry)
                
                # Write back the updated logs
                with open(self.log_file, 'w') as f:
                    json.dump(logs, f, indent=2)
                
                print(f"Logged: {flow.request.method} {flow.request.url}")
        except Exception as e:
            print(f"Error logging request: {str(e)}")

    def done(self):
        # Disable proxy when done
        set_proxy(False)

def parse_args():
    parser = argparse.ArgumentParser(description='HTTP Traffic Logger')
    parser.add_argument('--filter', '-f', help='URL filter string')
    parser.add_argument('--domain', '-d', help='Domain filter string')
    return parser.parse_args()

# Global logger instance for mitmdump
logger_instance = None

def start():
    global logger_instance
    args = parse_args()
    logger_instance = HTTPLogger(url_filter=args.filter, domain_filter=args.domain)
    return logger_instance

addons = [start()]

if __name__ == "__main__":
    try:
        from mitmproxy.tools.main import mitmdump
        
        args = parse_args()
        print(f"Starting HTTP logger with filters - URL: {args.filter}, Domain: {args.domain}")
        
        mitmdump(["-s", __file__])
    except KeyboardInterrupt:
        if logger_instance:
            logger_instance.done()
        print("\nLogger stopped by user.")
    except Exception as e:
        print(f"Error starting logger: {str(e)}")