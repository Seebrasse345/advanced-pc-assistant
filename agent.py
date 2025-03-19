import os
import subprocess
from openai import OpenAI
import sys
import datetime
import logging
import json
import psutil
import platform
import requests
import pyautogui
import io
import base64
from PIL import Image
import pathlib
import webbrowser
import time
# Import knowledge base and web processor
from knowledge_base import KnowledgeBase
from web_processor import WebProcessor

def run_cmd(command):
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout + result.stderr
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class Agent:
    def __init__(self, api_key=None, model="gpt-4-0613", additional_tools=None, kb_path="data/knowledge.db"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided or set as OPENAI_API_KEY environment variable")
        self.model = model
        self.additional_tools = additional_tools or []
        self.client = OpenAI(api_key=self.api_key)
        
        # Initialize knowledge base and web processor
        self.kb = KnowledgeBase(db_path=kb_path, api_key=self.api_key)
        self.web_processor = WebProcessor()

        # Set up logging
        self.logger = logging.getLogger('Agent')
        self.logger.setLevel(logging.INFO)
        log_file = os.path.join(os.getcwd(), 'agent.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Initialize task list
        self.tasks = []
        self.completed_tasks = []

        # List of tools with added RAG capabilities
        all_tools = [
            {"type": "function", "function": {"name": "cmd", "description": "Runs a command on the system", "parameters": {"type": "object", "properties": {"command": {"type": "string", "description": "The command to run"}}, "required": ["command"]}}},
            {"type": "function", "function": {"name": "file_operations", "description": "Performs file operations like read, write, list, or delete", "parameters": {"type": "object", "properties": {"operation": {"type": "string", "enum": ["read", "write", "list", "delete"], "description": "The operation to perform"}, "path": {"type": "string", "description": "The file or directory path"}, "content": {"type": "string", "description": "Content to write (for write operation)"}}, "required": ["operation", "path"]}}},
            {"type": "function", "function": {"name": "system_info", "description": "Retrieves system information", "parameters": {"type": "object", "properties": {"info_type": {"type": "string", "enum": ["cpu", "memory", "disk", "network", "all"], "description": "Type of system information to retrieve"}}, "required": ["info_type"]}}},
            {"type": "function", "function": {"name": "web_request", "description": "Sends a web request", "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "The URL to send the request to"}, "method": {"type": "string", "enum": ["GET", "POST"], "description": "The HTTP method to use"}, "data": {"type": "object", "description": "Data to send with the request (for POST)"}}, "required": ["url", "method"]}}},
            {"type": "function", "function": {"name": "screenshot", "description": "Takes a screenshot of the screen", "parameters": {"type": "object", "properties": {"save_path": {"type": "string", "description": "Path to save the screenshot (optional)"}, "region": {"type": "string", "description": "Region to capture in format 'x,y,width,height' (optional)"}}, "required": []}}},
            {"type": "function", "function": {"name": "browser", "description": "Opens the default web browser with a URL", "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "The URL to open in the browser"}}, "required": ["url"]}}},
            {"type": "function", "function": {"name": "task_manager", "description": "Manages tasks and tracks progress", "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["add", "list", "complete", "delete"], "description": "The action to perform"}, "task_id": {"type": "integer", "description": "The ID of the task (for complete, delete actions)"}, "description": {"type": "string", "description": "Description of the task (for add action)"}}, "required": ["action"]}}},
            {"type": "function", "function": {"name": "finish_task", "description": "Signals that the current task is finished", "parameters": {"type": "object", "properties": {"message": {"type": "string", "description": "A message summarizing task completion"}}, "required": ["message"]}}},
            # Knowledge base tools
            {"type": "function", "function": {"name": "kb_add", "description": "Add content to the knowledge base", "parameters": {"type": "object", "properties": {"content": {"type": "string", "description": "The content to add"}, "title": {"type": "string", "description": "Title for the content (optional)"}, "source": {"type": "string", "description": "Source of the content (optional)"}, "metadata": {"type": "object", "description": "Additional metadata (optional)"}}, "required": ["content"]}}},
            {"type": "function", "function": {"name": "kb_retrieve", "description": "Retrieve a document from the knowledge base by ID", "parameters": {"type": "object", "properties": {"doc_id": {"type": "string", "description": "The ID of the document to retrieve"}}, "required": ["doc_id"]}}},
            {"type": "function", "function": {"name": "kb_search", "description": "Search the knowledge base for documents matching a query", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "The search query"}, "limit": {"type": "integer", "description": "Maximum number of results to return (default: 5)"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "kb_delete", "description": "Delete a document from the knowledge base", "parameters": {"type": "object", "properties": {"doc_id": {"type": "string", "description": "The ID of the document to delete"}}, "required": ["doc_id"]}}},
            {"type": "function", "function": {"name": "kb_recent", "description": "Get the most recent documents added to the knowledge base", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "description": "Maximum number of documents to return (default: 10)"}}, "required": []}}},
            {"type": "function", "function": {"name": "kb_stats", "description": "Get statistics about the knowledge base", "parameters": {"type": "object", "properties": {}, "required": []}}},
            {"type": "function", "function": {"name": "web_scrape", "description": "Scrape content from a website and add it to the knowledge base", "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "The URL to scrape"}, "add_to_kb": {"type": "boolean", "description": "Whether to add the content to the knowledge base (default: true)"}}, "required": ["url"]}}},
            {"type": "function", "function": {"name": "web_crawl", "description": "Crawl a website and add content to the knowledge base", "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "The starting URL to crawl"}, "max_pages": {"type": "integer", "description": "Maximum number of pages to crawl (default: 5)"}, "same_domain": {"type": "boolean", "description": "Only crawl pages on the same domain (default: true)"}}, "required": ["url"]}}},
        ]
        
        self.assistant = self.client.beta.assistants.create(
            name="Enhanced PC Agent with RAG",
            instructions=f"""
        You are an advanced AI agent designed to assist users with various PC-related tasks efficiently and accurately. You are equipped with a knowledge base that stores information from previous interactions and web scraping, allowing you to provide more informed and contextually relevant responses.

        Your primary goal is to provide quick, concise, and accurate step-by-step solutions to user queries. Follow these guidelines strictly:
        Never just give the instructions to the user actually execute the task yourself using the tools provided.
        
        1. Approach to Tasks:
        - Analyze each query carefully to understand the user's intent.
        - Use your knowledge base to inform your responses whenever relevant.
        - Break down complex tasks into clear, logical steps.
        - Prioritize efficiency and accuracy in your solutions.
        - If a task seems unclear or potentially harmful, ask for clarification before proceeding.

        2. Use of Tools:
        - Utilize the provided tools effectively to accomplish tasks, including:
            a) cmd: For running system commands. Use cautiously and only when necessary.
            b) file_operations: For reading, writing, listing, or deleting files.
            c) system_info: To retrieve information about CPU, memory, disk, or network.
            d) web_request: For making GET or POST requests.
            e) screenshot: For capturing screen images.
            f) browser: For opening websites or URLs in the default browser.
            g) task_manager: For tracking ongoing tasks and their progress.
            h) knowledge base (kb_*) tools: For storing and retrieving information.
            i) web scraping tools: For fetching and processing web content.
        - Choose the most appropriate tool for each task.
        - Combine tools when necessary to achieve the desired outcome.

        3. Knowledge Management:
        - Store valuable information in the knowledge base using kb_add.
        - Before answering questions, check if the knowledge base contains relevant information using kb_search.
        - When visiting a webpage that might contain useful information, consider scraping and storing it using web_scrape.
        - For thorough research, use web_crawl to collect information from multiple pages.
        - Prefer using stored knowledge over making new web requests when possible.

        4. Response Format:
        - Begin each response with a brief acknowledgment of the user's request.
        - Provide solutions in a step-by-step format, numbering each step when appropriate.
        - Keep explanations concise but clear. Avoid unnecessary verbosity.
        - If code is part of the solution, present it in a clear, readable format.

        5. Error Handling and Safety:
        - Anticipate potential errors and include error handling in your solutions.
        - If a requested action seems unsafe or could potentially harm the system, warn the user and suggest safer alternatives.

        6. Completion of Tasks:
        - After providing the solution, always use the finish_task tool to signal task completion.
        - The finish_task message should briefly summarize what was accomplished.

        Remember, your role is to be a reliable, efficient, and safe assistant for PC-related tasks. Execute the task with caution however don't ask for confirmation for every single thing.
        
        Here is some additional information about the system currently and the current directory:
        system information: {self.system_info("all")}
        current directory: {os.getcwd()}
        knowledge base document count: {self.kb.get_document_count()}
            """,
            model=model,
            tools=all_tools
        )
        self.thread = None
        self.task_finished = False

    def log_and_print(self, message):
        timestamp = get_timestamp()
        full_message = f"[{timestamp}] {message}"
        self.logger.info(message)
        print(full_message)

    def file_operations(self, operation, path, content=None):
        try:
            if operation == "read":
                with open(path, 'r') as file:
                    return file.read()
            elif operation == "write":
                # Create directory if it doesn't exist
                directory = os.path.dirname(path)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                    
                with open(path, 'w') as file:
                    file.write(content)
                return f"Successfully wrote to {path}"
            elif operation == "list":
                items = os.listdir(path)
                result = []
                for item in items:
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        result.append(f"[dir] {item}")
                    else:
                        size = os.path.getsize(item_path)
                        result.append(f"[file] {item} ({self._format_size(size)})")
                return '\n'.join(result)
            elif operation == "delete":
                if os.path.isdir(path):
                    os.rmdir(path)
                    return f"Successfully deleted directory {path}"
                else:
                    os.remove(path)
                    return f"Successfully deleted file {path}"
        except Exception as e:
            return f"Error in file operation: {str(e)}"
    
    def _format_size(self, size_bytes):
        """Format file size in a human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0 or unit == 'TB':
                return f"{size_bytes:.2f}{unit}" if unit != 'B' else f"{size_bytes}B"
            size_bytes /= 1024.0

    def system_info(self, info_type):
        if info_type == "cpu":
            return json.dumps({"cpu_percent": psutil.cpu_percent(interval=1), "cpu_count": psutil.cpu_count()})
        elif info_type == "memory":
            mem = psutil.virtual_memory()
            return json.dumps({"total": mem.total, "available": mem.available, "percent": mem.percent})
        elif info_type == "disk":
            disk = psutil.disk_usage('/')
            return json.dumps({"total": disk.total, "used": disk.used, "free": disk.free, "percent": disk.percent})
        elif info_type == "network":
            net_io = psutil.net_io_counters()
            return json.dumps({"bytes_sent": net_io.bytes_sent, "bytes_recv": net_io.bytes_recv})
        elif info_type == "all":
            return json.dumps({
                "platform": platform.platform(),
                "cpu": {"cpu_percent": psutil.cpu_percent(interval=1), "cpu_count": psutil.cpu_count()},
                "memory": dict(psutil.virtual_memory()._asdict()),
                "disk": dict(psutil.disk_usage('/')._asdict()),
                "network": dict(psutil.net_io_counters()._asdict())
            })

    def web_request(self, url, method, data=None):
        try:
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url, json=data)
            return f"Status Code: {response.status_code}, Content: {response.text[:500]}"
        except Exception as e:
            return f"Error in web request: {str(e)}"

    def screenshot(self, save_path=None, region=None):
        try:
            if region:
                # Parse region string "x,y,width,height"
                x, y, width, height = map(int, region.split(','))
                screen_img = pyautogui.screenshot(region=(x, y, width, height))
            else:
                screen_img = pyautogui.screenshot()
            
            if save_path:
                # Create directory if it doesn't exist
                directory = os.path.dirname(save_path)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                    
                screen_img.save(save_path)
                return f"Screenshot saved to {save_path}"
            
            # Return a base64-encoded image for immediate display/use
            buffered = io.BytesIO()
            screen_img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"Screenshot captured (not saved). Base64 encoding (first 100 chars): {img_str[:100]}..."
        except Exception as e:
            return f"Error taking screenshot: {str(e)}"

    def browser(self, url):
        try:
            webbrowser.open(url)
            return f"Opened URL in browser: {url}"
        except Exception as e:
            return f"Error opening URL in browser: {str(e)}"

    def task_manager(self, action, task_id=None, description=None):
        try:
            if action == "add":
                if not description:
                    return "Error: Task description is required for 'add' action."
                new_id = len(self.tasks) + len(self.completed_tasks) + 1
                task = {"id": new_id, "description": description, "created_at": get_timestamp()}
                self.tasks.append(task)
                return f"Task #{new_id} added: {description}"
            
            elif action == "list":
                if not self.tasks and not self.completed_tasks:
                    return "No tasks found."
                
                result = "Active Tasks:\n"
                for task in self.tasks:
                    result += f"#{task['id']}: {task['description']} (Created: {task['created_at']})\n"
                
                result += "\nCompleted Tasks:\n"
                for task in self.completed_tasks:
                    result += f"#{task['id']}: {task['description']} (Completed: {task.get('completed_at', 'Unknown')})\n"
                
                return result
            
            elif action == "complete":
                if not task_id:
                    return "Error: Task ID is required for 'complete' action."
                
                for i, task in enumerate(self.tasks):
                    if task["id"] == task_id:
                        task["completed_at"] = get_timestamp()
                        self.completed_tasks.append(task)
                        self.tasks.pop(i)
                        return f"Task #{task_id} marked as completed."
                
                return f"Error: Task #{task_id} not found."
            
            elif action == "delete":
                if not task_id:
                    return "Error: Task ID is required for 'delete' action."
                
                for i, task in enumerate(self.tasks):
                    if task["id"] == task_id:
                        self.tasks.pop(i)
                        return f"Task #{task_id} deleted."
                
                for i, task in enumerate(self.completed_tasks):
                    if task["id"] == task_id:
                        self.completed_tasks.pop(i)
                        return f"Completed task #{task_id} deleted."
                
                return f"Error: Task #{task_id} not found."
            
            else:
                return f"Error: Unknown action '{action}'"
        
        except Exception as e:
            return f"Error in task manager: {str(e)}"

    # Knowledge base functions
    def kb_add(self, content, title=None, source=None, metadata=None):
        """Add content to the knowledge base."""
        try:
            doc_id = self.kb.add_document(content, title, source, metadata)
            return f"Added document to knowledge base with ID: {doc_id}"
        except Exception as e:
            return f"Error adding to knowledge base: {str(e)}"
    
    def kb_retrieve(self, doc_id):
        """Retrieve a document from the knowledge base by ID."""
        try:
            doc = self.kb.retrieve_document(doc_id)
            if doc:
                return json.dumps(doc)
            return "Document not found"
        except Exception as e:
            return f"Error retrieving from knowledge base: {str(e)}"
    
    def kb_search(self, query, limit=5):
        """Search the knowledge base for documents matching a query."""
        try:
            # First try semantic search
            semantic_results = self.kb.retrieve_similar(query, limit=limit)
            
            # If no good semantic results, try keyword search
            if not semantic_results or semantic_results[0]['similarity'] < 0.6:
                keyword_results = self.kb.search_documents(query, limit=limit)
                
                # Combine results, prioritizing semantic matches
                combined = {doc['id']: doc for doc in semantic_results}
                for doc in keyword_results:
                    if doc['id'] not in combined:
                        doc['similarity'] = 0  # Add a similarity score for consistent output
                        combined[doc['id']] = doc
                
                results = list(combined.values())
                results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
                results = results[:limit]
            else:
                results = semantic_results
            
            if not results:
                return "No matching documents found"
            
            formatted_results = []
            for doc in results:
                # Truncate content for readability
                doc_content = doc['content']
                if len(doc_content) > 300:
                    doc_content = doc_content[:300] + "..."
                
                formatted_results.append({
                    "id": doc['id'],
                    "title": doc['title'],
                    "content_preview": doc_content,
                    "similarity": doc.get('similarity', 0),
                    "source": doc.get('source', 'Unknown')
                })
            
            return json.dumps(formatted_results)
        except Exception as e:
            return f"Error searching knowledge base: {str(e)}"
    
    def kb_delete(self, doc_id):
        """Delete a document from the knowledge base."""
        try:
            success = self.kb.delete_document(doc_id)
            if success:
                return f"Document {doc_id} deleted from knowledge base"
            return f"Document {doc_id} not found"
        except Exception as e:
            return f"Error deleting from knowledge base: {str(e)}"
    
    def kb_recent(self, limit=10):
        """Get the most recent documents added to the knowledge base."""
        try:
            docs = self.kb.get_recent_documents(limit)
            if not docs:
                return "No documents in knowledge base"
            
            formatted_docs = []
            for doc in docs:
                # Truncate content for readability
                doc_content = doc['content']
                if len(doc_content) > 300:
                    doc_content = doc_content[:300] + "..."
                
                formatted_docs.append({
                    "id": doc['id'],
                    "title": doc['title'],
                    "content_preview": doc_content,
                    "source": doc.get('source', 'Unknown'),
                    "created_at": doc['created_at']
                })
            
            return json.dumps(formatted_docs)
        except Exception as e:
            return f"Error retrieving recent documents: {str(e)}"
    
    def kb_stats(self):
        """Get statistics about the knowledge base."""
        try:
            doc_count = self.kb.get_document_count()
            return json.dumps({
                "document_count": doc_count,
                "knowledge_base_path": self.kb.db_path
            })
        except Exception as e:
            return f"Error retrieving knowledge base stats: {str(e)}"
    
    # Web scraping and crawling functions
    def web_scrape(self, url, add_to_kb=True):
        """Scrape content from a website and optionally add it to the knowledge base."""
        try:
            processed_data = self.web_processor.process_url(url)
            if not processed_data:
                return f"Failed to scrape content from {url}"
            
            result = f"Successfully scraped {url}"
            
            if add_to_kb and processed_data['content']:
                doc_id = self.kb.add_document(
                    content=processed_data['content'],
                    title=processed_data['title'],
                    source=url,
                    metadata=processed_data['metadata']
                )
                result += f"\nAdded to knowledge base with ID: {doc_id}"
                
                # Return a preview of the content
                content_preview = processed_data['content']
                if len(content_preview) > 300:
                    content_preview = content_preview[:300] + "..."
                
                result += f"\nContent preview: {content_preview}"
            
            return result
        except Exception as e:
            return f"Error scraping website: {str(e)}"
    
    def web_crawl(self, url, max_pages=5, same_domain=True):
        """Crawl a website and add content to the knowledge base."""
        try:
            # Get the initial page
            html_content = self.web_processor.fetch_url(url)
            if not html_content:
                return f"Failed to access {url}"
            
            # Process the initial page
            processed_data = self.web_processor.process_url(url)
            if processed_data and processed_data['content']:
                doc_id = self.kb.add_document(
                    content=processed_data['content'],
                    title=processed_data['title'],
                    source=url,
                    metadata=processed_data['metadata']
                )
            
            # Extract links from the initial page
            links = self.web_processor.extract_links(html_content, url)
            
            # Track processed links
            processed_links = {url}
            results = [f"Added initial page {url} to knowledge base"]
            
            # Process additional pages up to max_pages
            page_count = 1
            for link in links:
                if page_count >= max_pages:
                    break
                    
                if link in processed_links:
                    continue
                    
                processed_links.add(link)
                
                # Process the linked page
                link_data = self.web_processor.process_url(link)
                if link_data and link_data['content']:
                    doc_id = self.kb.add_document(
                        content=link_data['content'],
                        title=link_data['title'],
                        source=link,
                        metadata=link_data['metadata']
                    )
                    results.append(f"Added page {link} to knowledge base")
                    page_count += 1
            
            return "\n".join(results) + f"\nCrawl completed: processed {page_count} pages."
        except Exception as e:
            return f"Error during web crawl: {str(e)}"
    
    def get_rag_context(self, query):
        """Get RAG context for a query to enhance responses."""
        try:
            context, used_docs = self.kb.get_rag_context(query)
            return context, used_docs
        except Exception as e:
            self.log_and_print(f"Error getting RAG context: {str(e)}")
            return "", []

    def autobot(self):
        if not self.thread:
            self.thread = self.client.beta.threads.create()
        
        self.log_and_print("Enhanced PC Agent with RAG is running. Type 'exit' to quit.")
        while True:
            if self.task_finished:
                self.log_and_print("Task finished. Agent is exiting.")
                break

            user_input = input("You: ")
            if user_input.lower() == 'exit':
                break

            self.log_and_print(f"User: {user_input}")
            
            # Get RAG context for the query
            rag_context, used_docs = self.get_rag_context(user_input)
            
            # Combine user input with RAG context if available
            if rag_context:
                enhanced_input = f"User query: {user_input}\n\n{rag_context}"
                self.log_and_print(f"Enhanced with knowledge base context (using {len(used_docs)} documents)")
            else:
                enhanced_input = user_input

            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=enhanced_input
            )
            run = self.client.beta.threads.runs.create(
                thread_id=self.thread.id,
                assistant_id=self.assistant.id
            )

            while run.status not in ["completed", "failed"]:
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread.id,
                    run_id=run.id
                )
                if run.status == "requires_action":
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        if function_name == "cmd":
                            output = run_cmd(function_args["command"])
                        elif function_name == "file_operations":
                            output = self.file_operations(**function_args)
                        elif function_name == "system_info":
                            output = self.system_info(function_args["info_type"])
                        elif function_name == "web_request":
                            output = self.web_request(**function_args)
                        elif function_name == "screenshot":
                            output = self.screenshot(**function_args)
                        elif function_name == "browser":
                            output = self.browser(**function_args)
                        elif function_name == "task_manager":
                            output = self.task_manager(**function_args)
                        elif function_name == "finish_task":
                            self.task_finished = True
                            output = f"Task finished: {function_args['message']}"
                        # Knowledge base and web processing tools
                        elif function_name == "kb_add":
                            output = self.kb_add(**function_args)
                        elif function_name == "kb_retrieve":
                            output = self.kb_retrieve(**function_args)
                        elif function_name == "kb_search":
                            output = self.kb_search(**function_args)
                        elif function_name == "kb_delete":
                            output = self.kb_delete(**function_args)
                        elif function_name == "kb_recent":
                            output = self.kb_recent(**function_args)
                        elif function_name == "kb_stats":
                            output = self.kb_stats()
                        elif function_name == "web_scrape":
                            output = self.web_scrape(**function_args)
                        elif function_name == "web_crawl":
                            output = self.web_crawl(**function_args)
                        else:
                            output = f"Unknown function: {function_name}"

                        self.log_and_print(f"Executing {function_name}: {function_args}")
                        self.log_and_print(f"Output: {output}")
                        
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": output
                        })

                    self.client.beta.threads.runs.submit_tool_outputs(
                        thread_id=self.thread.id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
                
                # Sleep briefly to avoid excessive API calls
                time.sleep(0.5)

            messages = self.client.beta.threads.messages.list(thread_id=self.thread.id)
            for message in reversed(messages.data):
                if message.role == "assistant":
                    assistant_response = message.content[0].text.value
                    self.log_and_print(f"Assistant: {assistant_response}")
                    
                    # Log the conversation with context used
                    if rag_context:
                        self.kb.log_conversation(user_input, assistant_response, used_docs)
                    
                    break


def main():
    agent = Agent()  # Will use OPENAI_API_KEY environment variable
    agent.autobot()

if __name__ == "__main__":
    main()