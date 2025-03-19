# Advanced PC Assistant Agent with RAG

An AI-powered agent that assists with various PC tasks using OpenAI's API. This project provides an interactive CLI interface where users can request help with file operations, system information, web requests, and more. The agent now features Retrieval Augmented Generation (RAG) with a knowledge base to provide more informed responses based on stored information and web content.

## Features

- **Command Execution**: Run system commands directly from the assistant
- **File Operations**: Read, write, list, and delete files
- **System Information**: Get detailed information about CPU, memory, disk, and network
- **Web Requests**: Send GET and POST requests to websites
- **Screenshot Capabilities**: Capture and save screenshots of your screen
- **Browser Integration**: Open URLs directly in your default browser
- **Task Management**: Keep track of tasks with a built-in task manager
- **HTTP Traffic Logging**: Use the built-in scraper to log HTTP traffic for analysis
- **Knowledge Base**: Store and retrieve information for more contextual responses
- **Web Scraping**: Extract and store content from websites
- **RAG Integration**: Enhance responses with relevant information from the knowledge base

## Installation

### Prerequisites

- Python 3.8 or higher
- OpenAI API Key

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/advanced-pc-assistant.git
   cd advanced-pc-assistant
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your OpenAI API key as an environment variable:
   ```bash
   # For Linux/Mac
   export OPENAI_API_KEY='your-api-key'
   
   # For Windows (Command Prompt)
   set OPENAI_API_KEY=your-api-key
   
   # For Windows (PowerShell)
   $env:OPENAI_API_KEY='your-api-key'
   ```

## Usage

### Starting the Agent

To start the main assistant agent:

```bash
python agent.py
```

The agent will initialize and prompt you for commands. Type `exit` to quit the application.

### HTTP Traffic Logging

To start the HTTP traffic logger:

```bash
# Start with default settings
python scraper.py

# Filter by URL or domain
python scraper.py --filter linkedin
python scraper.py --domain example.com
```

Note: The HTTP logging feature uses mitmproxy for traffic interception. On Windows, it will automatically configure proxy settings.

## Available Tools

The agent comes with several built-in tools:

### System Tools

- **cmd**: Execute system commands
  ```
  Run a directory listing: ls -la
  ```

- **system_info**: Get system information
  ```
  Get my current memory usage
  ```

### File Operations

- **file_operations**: Manipulate files and directories
  ```
  Show me the files in my Documents folder
  Create a new text file with my schedule
  ```

### Web Tools

- **web_request**: Send HTTP requests
  ```
  Check if a website is online
  Fetch the content of a webpage
  ```

- **browser**: Open URLs in your default browser
  ```
  Open GitHub in my browser
  ```

### Visual Tools

- **screenshot**: Capture your screen
  ```
  Take a screenshot of my entire screen
  Capture just the top-left portion of my screen
  ```

### Task Management

- **task_manager**: Manage tasks
  ```
  Add a new task to review documentation
  Show me my current tasks
  Mark task #3 as complete
  ```

### Knowledge Base Tools

- **kb_add**: Add content to the knowledge base
  ```
  Store this information for future reference
  ```

- **kb_search**: Search for information in the knowledge base
  ```
  Find information about Python in my knowledge base
  ```

- **kb_retrieve**: Get a specific document from the knowledge base
  ```
  Retrieve document with ID abc-123-xyz
  ```

- **kb_recent**: View recently added documents
  ```
  Show me the most recent additions to my knowledge base
  ```

- **kb_delete**: Remove a document from the knowledge base
  ```
  Delete document with ID abc-123-xyz
  ```

- **kb_stats**: Get statistics about the knowledge base
  ```
  How many documents are in my knowledge base?
  ```

### Web Processing Tools

- **web_scrape**: Extract content from a website and add it to the knowledge base
  ```
  Scrape and store content from https://example.com/article
  ```

- **web_crawl**: Crawl multiple pages of a website and add content to the knowledge base
  ```
  Crawl https://example.com and store the first 5 pages
  ```

## How RAG Works in this Application

The Retrieval Augmented Generation (RAG) implementation in this agent:

1. **Stores Knowledge**: Content from web scraping, user interactions, and manually added information is stored in a SQLite database with vector embeddings.

2. **Retrieves Context**: When you ask a question, the agent searches the knowledge base for relevant information using semantic similarity.

3. **Enhances Responses**: The retrieved information is used to provide more accurate and contextually relevant answers.

4. **Learns Over Time**: As more information is added to the knowledge base, the agent becomes more knowledgeable and helpful.

## Configuration

You can customize the assistant's behavior by modifying these parameters in `agent.py`:

- Change the AI model by updating the `model` parameter in the `Agent` class instantiation
- Add custom tools by extending the `additional_tools` parameter
- Modify the knowledge base path by changing the `kb_path` parameter (default: "data/knowledge.db")

## Troubleshooting

### API Key Issues

If you encounter errors related to the API key:
- Ensure the environment variable is set correctly
- Check that your API key is valid and has sufficient credits

### Knowledge Base Issues

If the knowledge base isn't working as expected:
- Ensure the required dependencies are installed
- Check that the database file is accessible and writable
- Try adding simple test content to verify storage and retrieval

### Proxy Setting Issues

If you encounter issues with the HTTP logger:
- Ensure you have administrator privileges
- Try running the application as administrator
- Manually reset your proxy settings if needed

## License

This project is released under the MIT License. See the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request 