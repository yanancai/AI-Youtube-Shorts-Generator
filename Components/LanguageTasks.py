import openai
import requests
from dotenv import load_dotenv
import os
import json

load_dotenv()


def load_prompt():
    """Load the GPT prompt from prompt.ninja file"""
    try:
        prompt_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt.ninja")
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(
            "Error: prompt.ninja file not found in the project root directory.\n"
            "Please create a prompt.ninja file with your GPT prompt, or copy one from the prompt_examples/ directory.\n"
            "Example: cp prompt_examples/educational.ninja prompt.ninja"
        )
    except Exception as e:
        raise Exception(f"Error loading prompt from prompt.ninja file: {e}")


# Support for OpenAI and Azure OpenAI
USE_AZURE_OPENAI = os.getenv("USE_AZURE_OPENAI", "true").lower() != "false"

if USE_AZURE_OPENAI:
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    if not (AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT):
        raise ValueError("Azure OpenAI configuration missing. Please set AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT in your .env file.")
else:
    openai.api_key = os.getenv("OPENAI_API")
    if not openai.api_key:
        raise ValueError("API key not found. Make sure it is defined in the .env file.")


# Function to extract multiple segments
def extract_segments(json_string):
    try:
        # Parse the JSON string
        data = json.loads(json_string)
        
        segments = []
        for segment in data:
            start_time = float(segment["start"])
            end_time = float(segment["end"])
            content = segment.get("content", "")
            title = segment.get("title", f"Clip_{int(start_time)}-{int(end_time)}")
            priority = int(segment.get("priority", 5))
            
            # Validate duration (under 60 seconds)
            duration = end_time - start_time
            if duration > 60:
                print(f"Warning: Segment '{title}' is {duration:.1f}s, which exceeds 60s limit")
                continue
                
            segments.append({
                "start": int(start_time),
                "end": int(end_time), 
                "title": title,
                "content": content,
                "priority": priority,
                "duration": duration
            })
        
        # Sort by priority (1 is highest priority)
        segments.sort(key=lambda x: x["priority"])
        return segments
        
    except Exception as e:
        print(f"Error in extract_segments: {e}")
        return []


# Function to extract start and end times (legacy support)
def extract_times(json_string):
    try:
        segments = extract_segments(json_string)
        if segments:
            # Return the first (highest priority) segment for backward compatibility
            return segments[0]["start"], segments[0]["end"]
        return 0, 0
    except Exception as e:
        print(f"Error in extract_times: {e}")
        return 0, 0


# Load the system prompt from external file
system = load_prompt()

User = """
Any Example
"""


def GetHighlight(Transcription):
    print("Getting Highlight from Transcription ")
    try:
        if USE_AZURE_OPENAI:
            url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_OPENAI_KEY,
            }
            payload = {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": Transcription + system},
                ],
                "temperature": 0.7,
                "max_tokens": 1024,
            }
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            json_string = result["choices"][0]["message"]["content"]
        else:
            response = openai.ChatCompletion.create(
                model="gpt-4o-2024-05-13",
                temperature=0.7,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": Transcription + system},
                ],
            )
            json_string = response.choices[0].message.content

        json_string = json_string.replace("json", "")
        json_string = json_string.replace("```", "")
        Start, End = extract_times(json_string)
        if Start == End:
            Ask = input("Error - Get Highlights again (y/n) -> ").lower()
            if Ask == "y":
                Start, End = GetHighlight(Transcription)
        return Start, End
    except Exception as e:
        print(f"Error in GetHighlight: {e}")
        return 0, 0


def GetMultipleHighlights(Transcription):
    print("Getting Multiple Highlights from Transcription ")
    try:
        if USE_AZURE_OPENAI:
            url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_OPENAI_KEY,
            }
            payload = {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": Transcription + system},
                ],
                "temperature": 0.7,
                "max_tokens": 2048,
            }
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            json_string = result["choices"][0]["message"]["content"]
        else:
            response = openai.ChatCompletion.create(
                model="gpt-4o-2024-05-13",
                temperature=0.7,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": Transcription + system},
                ],
            )
            json_string = response.choices[0].message.content

        json_string = json_string.replace("json", "")
        json_string = json_string.replace("```", "")
        
        segments = extract_segments(json_string)
        if not segments:
            Ask = input("Error - Get Highlights again (y/n) -> ").lower()
            if Ask == "y":
                segments = GetMultipleHighlights(Transcription)
        return segments
    except Exception as e:
        print(f"Error in GetMultipleHighlights: {e}")
        return []


if __name__ == "__main__":
    print(GetHighlight(User))
