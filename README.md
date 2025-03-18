# Advanced PC Assistant Agent

An AI-powered agent that assists with various PC tasks using OpenAI's API. This project provides an interactive CLI interface where users can request help with file operations, system information, web requests, and more.

## Features

- **Command Execution**: Run system commands directly from the assistant
- **File Operations**: Read, write, list, and delete files
- **System Information**: Get detailed information about CPU, memory, disk, and network
- **Web Requests**: Send GET and POST requests to websites
- **Screenshot Capabilities**: Capture and save screenshots of your screen
- **Browser Integration**: Open URLs directly in your default browser
- **Task Management**: Keep track of tasks with a built-in task manager
- **HTTP Traffic Logging**: Use the built-in scraper to log HTTP traffic for analysis

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

## Configuration

You can customize the assistant's behavior by modifying these parameters in `agent.py`:

- Change the AI model by updating the `model` parameter in the `Agent` class instantiation
- Add custom tools by extending the `additional_tools` parameter

## Troubleshooting

### API Key Issues

If you encounter errors related to the API key:
- Ensure the environment variable is set correctly
- Check that your API key is valid and has sufficient credits

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