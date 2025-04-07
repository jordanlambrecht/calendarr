import datetime
import os
import sys

def main():
    """Simple test script to verify Python execution and environment variables"""
    with open('/app/test_output.log', 'w') as f:
        f.write(f"Test script ran at {datetime.datetime.now()}\n")
        f.write(f"Python version: {sys.version}\n")
        f.write(f"Current directory: {os.getcwd()}\n")
        
        f.write("\nEnvironment variables:\n")
        for key, value in sorted(os.environ.items()):
            if key in ['CALENDAR_URLS', 'DISCORD_WEBHOOK_URL', 'SLACK_WEBHOOK_URL']:
                # Hide sensitive data in the logs
                f.write(f"{key}: [value hidden for security]\n")
            else:
                f.write(f"{key}: {value}\n")
        
        # Try accessing the CALENDAR_URLS specifically
        calendar_urls = os.environ.get('CALENDAR_URLS', 'NOT FOUND')
        f.write(f"\nCALENDAR_URLS exists: {calendar_urls != 'NOT FOUND'}\n")
        f.write(f"CALENDAR_URLS length: {len(calendar_urls)}\n")
        
        f.write("\nTest script completed successfully\n")
    
    # Also print to stdout for immediate feedback
    print(f"Test completed at {datetime.datetime.now()}")
    print(f"Output written to /app/test_output.log")

if __name__ == "__main__":
    main()