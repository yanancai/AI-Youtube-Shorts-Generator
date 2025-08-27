import openai
import requests
from dotenv import load_dotenv
import os
import json
import re
from datetime import datetime

load_dotenv()


def load_prompt():
    """Load the GPT prompt from prompt.ninja file"""
    try:
        # First try the enhanced prompt
        enhanced_prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "enhanced_prompt.ninja")
        if os.path.exists(enhanced_prompt_path):
            with open(enhanced_prompt_path, 'r', encoding='utf-8') as f:
                print("📋 Using enhanced prompt for exact quote extraction")
                return f.read().strip()
        
        # Fall back to original prompt
        prompt_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt.ninja")
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            print("📋 Using original prompt (consider upgrading to enhanced_prompt.ninja)")
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(
            "Error: Neither enhanced_prompt.ninja nor prompt.ninja file found in the project root directory.\n"
            "Please create one of these files with your GPT prompt, or copy one from the prompt_examples/ directory.\n"
            "For best results, use: cp enhanced_prompt.ninja prompt.ninja"
        )
    except Exception as e:
        raise Exception(f"Error loading prompt: {e}")


def clean_gpt_json_response(response_text):
    """
    Clean and extract JSON from GPT response that might contain markdown or extra text
    """
    print(f"🔧 Cleaning GPT response: {repr(response_text[:200])}...")
    
    try:
        # First, try to parse as-is in case it's already clean JSON
        return json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        print(f"   Initial JSON parse failed: {e}")
    
    # Remove common markdown formatting
    cleaned = response_text.strip()
    
    # Remove code block markers (```json, ```, etc.)
    cleaned = re.sub(r'```(?:json)?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
    
    # Remove any explanatory text before JSON (like "Here are the highlights:")
    lines = cleaned.split('\n')
    json_start_idx = -1
    
    # Find the first line that looks like JSON (starts with [ or {)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('[') or stripped.startswith('{'):
            json_start_idx = i
            break
    
    if json_start_idx >= 0:
        # Take only lines from JSON start onwards
        json_lines = lines[json_start_idx:]
        cleaned = '\n'.join(json_lines)
        print(f"   Found JSON start at line {json_start_idx}")
    
    print(f"   Cleaned text: {repr(cleaned[:200])}...")
    
    # Try to parse the cleaned text
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"   Cleaned JSON parse failed: {e}")
    
    # Advanced JSON repair for malformed responses
    try:
        return repair_malformed_json(cleaned)
    except Exception as e:
        print(f"   JSON repair failed: {e}")
    
    # If all else fails, return None and log the issue
    print(f"❌ Could not extract valid JSON from response")
    print(f"   Full response: {repr(response_text[:1000])}...")  # Limit output length
    return None


def repair_malformed_json(text):
    """
    Attempt to repair malformed JSON by using regex to extract structured data
    """
    print("🔧 Attempting to repair malformed JSON...")
    
    # Pattern to match complete JSON objects with title, exact_quote, content, priority
    object_pattern = r'\{\s*"title"\s*:\s*"([^"]+)"\s*,\s*"exact_quote"\s*:\s*"([^"]*(?:\\.[^"]*)*)".*?"content"\s*:\s*"([^"]*(?:\\.[^"]*)*)".*?"priority"\s*:\s*(\d+)\s*\}'
    
    # Try to find individual objects and reconstruct array
    objects = []
    
    # First try: Use regex to extract complete objects
    matches = re.finditer(object_pattern, text, re.DOTALL)
    for match in matches:
        title, exact_quote, content, priority = match.groups()
        # Unescape quotes
        exact_quote = exact_quote.replace('\\"', '"')
        content = content.replace('\\"', '"')
        
        objects.append({
            "title": title,
            "exact_quote": exact_quote,
            "content": content,
            "priority": int(priority)
        })
    
    if objects:
        print(f"✅ Repaired JSON with {len(objects)} objects using regex extraction")
        return objects
    
    # Second try: Manual parsing for cases where regex fails
    # Split by object boundaries and try to extract each field
    # Look for patterns like: "title": "...", "exact_quote": "...", etc.
    
    # Find all title fields as object boundaries
    title_matches = list(re.finditer(r'"title"\s*:\s*"([^"]+)"', text))
    
    for i, title_match in enumerate(title_matches):
        try:
            title = title_match.group(1)
            start_pos = title_match.start()
            
            # Find the end of this object (start of next object or end of text)
            if i + 1 < len(title_matches):
                end_pos = title_matches[i + 1].start()
            else:
                end_pos = len(text)
            
            object_text = text[start_pos:end_pos]
            
            # Extract fields from this object
            exact_quote_match = re.search(r'"exact_quote"\s*:\s*"(.*?)"(?=\s*,\s*"content")', object_text, re.DOTALL)
            content_match = re.search(r'"content"\s*:\s*"(.*?)"(?=\s*,\s*"priority")', object_text, re.DOTALL)
            priority_match = re.search(r'"priority"\s*:\s*(\d+)', object_text)
            
            if exact_quote_match and content_match and priority_match:
                exact_quote = exact_quote_match.group(1).replace('\\"', '"').replace('\\n', '\n')
                content = content_match.group(1).replace('\\"', '"')
                priority = int(priority_match.group(1))
                
                objects.append({
                    "title": title,
                    "exact_quote": exact_quote,
                    "content": content,
                    "priority": priority
                })
                
        except Exception as e:
            print(f"   Warning: Failed to parse object {i+1}: {e}")
            continue
    
    if objects:
        print(f"✅ Repaired JSON with {len(objects)} objects using manual parsing")
        return objects
    
    # Third try: Try to fix common JSON formatting issues
    # Look for incomplete objects and try to complete them
    if '"title"' in text:
        print("   Found title field, attempting basic reconstruction...")
        
        # Try to wrap in array brackets if missing
        if not text.strip().startswith('['):
            test_json = '[' + text.strip() + ']'
            try:
                return json.loads(test_json)
            except json.JSONDecodeError:
                pass
        
        # Try to wrap individual objects in braces if missing
        if not text.strip().startswith('{') and not text.strip().startswith('['):
            test_json = '[{' + text.strip() + '}]'
            try:
                return json.loads(test_json)
            except json.JSONDecodeError:
                pass
    
    raise ValueError("Could not repair malformed JSON")


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


def save_gpt_interaction(input_text, output_text, mode="single", gpt_interactions_dir="outputs"):
    """Save GPT input and output for debugging"""
    try:
        # Ensure the GPT interactions directory exists
        os.makedirs(gpt_interactions_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Handle special cases for placeholder responses
        is_request_only = output_text == "REQUEST_SENT"
        is_error = output_text.startswith("ERROR:")
        
        # Save the interaction
        interaction_path = os.path.join(gpt_interactions_dir, f"gpt_{mode}_{timestamp}.json")
        interaction_data = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "input": input_text,
            "output": output_text,
            "input_length": len(input_text),
            "output_length": len(output_text) if not is_request_only else 0,
            "status": "request_sent" if is_request_only else ("error" if is_error else "completed")
        }
        
        with open(interaction_path, 'w', encoding='utf-8') as f:
            json.dump(interaction_data, f, indent=2, ensure_ascii=False)
        
        # Always save input as readable text file (even if response is pending/error)
        input_path = os.path.join(gpt_interactions_dir, f"gpt_{mode}_input_{timestamp}.txt")
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write("=== GPT INPUT ===\n")
            f.write(f"Mode: {mode}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Status: {'Request Sent' if is_request_only else ('Error' if is_error else 'Completed')}\n")
            f.write("=" * 50 + "\n\n")
            f.write(input_text)
        
        # Save output only if it's not a request-only save
        if not is_request_only:
            output_path = os.path.join(gpt_interactions_dir, f"gpt_{mode}_output_{timestamp}.txt")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("=== GPT OUTPUT ===\n")
                f.write(f"Mode: {mode}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Status: {'Error' if is_error else 'Completed'}\n")
                f.write("=" * 50 + "\n\n")
                f.write(output_text)
            
            print(f"💾 GPT interaction saved to:")
            print(f"   - JSON format: {interaction_path}")
            print(f"   - Input text: {input_path}")
            print(f"   - Output text: {output_path}")
        else:
            print(f"💾 GPT input saved to:")
            print(f"   - JSON format: {interaction_path}")
            print(f"   - Input text: {input_path}")
            print(f"   - Output will be saved when response is received")
        
    except Exception as e:
        print(f"Warning: Failed to save GPT interaction: {e}")
        # Try to at least save the input to a basic file as fallback
        try:
            fallback_path = os.path.join(gpt_interactions_dir, f"gpt_input_fallback_{timestamp}.txt")
            with open(fallback_path, 'w', encoding='utf-8') as f:
                f.write(f"FALLBACK SAVE - {datetime.now()}\n")
                f.write(f"Mode: {mode}\n")
                f.write("=" * 50 + "\n\n")
                f.write(input_text)
            print(f"💾 Fallback: Input saved to {fallback_path}")
        except:
            print("❌ Could not save GPT input even as fallback")


# Function to extract multiple segments with exact quotes
def extract_segments_with_quotes(json_string):
    """Extract segments that include exact quotes for precise word matching"""
    try:
        print(f"🔍 Extracting segments with quotes from: {repr(json_string[:100])}...")
        
        # Clean and parse the JSON string
        data = clean_gpt_json_response(json_string)
        if not data:
            print("❌ No valid JSON data extracted")
            return []
        
        print(f"✅ Successfully parsed JSON with {len(data)} items")
        
        segments = []
        for i, segment in enumerate(data):
            print(f"   Processing segment {i+1}: {segment.keys() if isinstance(segment, dict) else type(segment)}")
            
            if not isinstance(segment, dict):
                print(f"   Warning: Segment {i+1} is not a dictionary, skipping")
                continue
                
            title = segment.get("title", f"Clip_{len(segments) + 1}")
            exact_quote = segment.get("exact_quote", "")
            content = segment.get("content", "")
            priority = int(segment.get("priority", 5))
            
            # Validate that we have an exact quote
            if not exact_quote:
                print(f"   Warning: Segment '{title}' has no exact_quote, skipping")
                continue
            
            print(f"   ✅ Valid segment: '{title}' (priority {priority})")
            
            segments.append({
                "start": 0,  # Will be filled by word matching
                "end": 0,    # Will be filled by word matching
                "title": title,
                "exact_quote": exact_quote,  # This is what we'll match against
                "content": content,
                "priority": priority,
                "duration": 0  # Will be calculated after word matching
            })
        
        # Sort by priority (1 is highest priority)
        segments.sort(key=lambda x: x["priority"])
        print(f"🎯 Extracted {len(segments)} valid segments")
        return segments
        
    except Exception as e:
        print(f"❌ Error in extract_segments_with_quotes: {e}")
        import traceback
        traceback.print_exc()
        return []


# Function to extract multiple segments (legacy - for backward compatibility)
def extract_segments(json_string):
    """Legacy function - tries new format first, falls back to old format"""
    try:
        # First try the new format with exact quotes
        segments = extract_segments_with_quotes(json_string)
        if segments:
            return segments
        
        # Fall back to old format
        data = clean_gpt_json_response(json_string)
        if not data:
            return []
        
        segments = []
        for segment in data:
            start_time = float(segment.get("start", 0))
            end_time = float(segment.get("end", 0))
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
try:
    system = load_prompt()
    print(f"✅ System prompt loaded successfully, length: {len(system)}")
except Exception as e:
    print(f"❌ Error loading system prompt: {e}")
    system = "Error loading prompt"

User = """
Any Example
"""


def GetHighlight(Transcription, gpt_interactions_dir="outputs"):
    print("Getting Highlight from Transcription ")
    try:
        print(f"🔍 Transcription type: {type(Transcription)}")
        print(f"🔍 Transcription keys: {Transcription.keys() if isinstance(Transcription, dict) else 'Not a dict'}")
        
        # Prepare input - use conversation transcript for better GPT understanding
        if isinstance(Transcription, dict):
            print("🔍 Accessing conversation_transcript...")
            input_text = Transcription.get('conversation_transcript', '')
            if not input_text:
                print("🔍 No conversation_transcript, trying clean_transcript...")
                # Fallback to clean transcript
                input_text = Transcription.get('clean_transcript', '')
                if not input_text:
                    print("🔍 No clean_transcript, trying segments...")
                    # Final fallback to original format
                    segments = Transcription.get('segments', [])
                    input_text = ""
                    for segment in segments:
                        if isinstance(segment, dict):
                            text = segment.get('text', '')
                            start = segment.get('start_time', 0)
                            end = segment.get('end_time', 0)
                            input_text += f"{start} - {end}: {text}\n"
                        else:
                            # Legacy format: tuple (text, start, end)
                            text, start, end = segment
                            input_text += f"{start} - {end}: {text}\n"
        else:
            print("🔍 Transcription is not dict, using as-is...")
            input_text = Transcription
        
        print(f"🔍 Input text length: {len(input_text)}")
        print(f"🔍 Input text preview: {repr(input_text[:200])}")
        
        # Insert transcript into the prompt template
        print("🔍 Loading system prompt...")
        print(f"🔍 System prompt preview: {system[:200]}...")
        
        print("🔍 Formatting prompt with transcript...")
        try:
            # Use replace instead of format to avoid issues with curly braces in transcript
            prompt_with_transcript = system.replace('{transcript}', input_text)
            print("✅ Prompt formatting successful")
        except Exception as format_error:
            print(f"❌ Error in prompt formatting: {format_error}")
            print(f"   System prompt type: {type(system)}")
            print(f"   Input text type: {type(input_text)}")
            print(f"   Input text sample: {repr(input_text[:100])}")
            raise format_error
        
        print(f"🔤 Transcript length: {len(input_text)} characters")
        print(f"🔤 Prompt length: {len(prompt_with_transcript)} characters")
        print(f"🔤 Prompt preview: {prompt_with_transcript[:300]}...")
        print(f"🔤 Using Azure OpenAI: {USE_AZURE_OPENAI}")
        
        # Save input immediately, regardless of what happens with the response
        save_gpt_interaction(prompt_with_transcript, "REQUEST_SENT", "single", gpt_interactions_dir)
        
        if USE_AZURE_OPENAI:
            url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_OPENAI_KEY,
            }
            payload = {
                "messages": [
                    {"role": "user", "content": prompt_with_transcript},
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
                    {"role": "user", "content": prompt_with_transcript},
                ],
            )
            json_string = response.choices[0].message.content

        # Save GPT interaction for debugging (update with actual response)
        save_gpt_interaction(prompt_with_transcript, json_string, "single", gpt_interactions_dir)

        # Clean the GPT response and extract times
        print(f"📤 Raw GPT response preview: {json_string[:100]}...")
        Start, End = extract_times(json_string)
        
        if Start == End:
            print(f"⚠️  No valid segment found in GPT response")
            Ask = input("Error - Get Highlights again (y/n) -> ").lower()
            if Ask == "y":
                Start, End = GetHighlight(Transcription, gpt_interactions_dir)
        return Start, End
    except Exception as e:
        print(f"Error in GetHighlight: {e}")
        # Ensure we save the input even if there's an error
        try:
            save_gpt_interaction(prompt_with_transcript, f"ERROR: {str(e)}", "single_error", gpt_interactions_dir)
        except:
            pass  # Don't fail if saving fails
        return 0, 0


def GetMultipleHighlights(Transcription, gpt_interactions_dir="outputs"):
    print("Getting Multiple Highlights from Transcription ")
    try:
        print(f"🔍 Transcription type: {type(Transcription)}")
        print(f"🔍 Transcription keys: {Transcription.keys() if isinstance(Transcription, dict) else 'Not a dict'}")
        
        # Prepare input - use conversation transcript for better GPT understanding
        if isinstance(Transcription, dict):
            print("🔍 Accessing conversation_transcript...")
            input_text = Transcription.get('conversation_transcript', '')
            if not input_text:
                print("🔍 No conversation_transcript, trying clean_transcript...")
                # Fallback to clean transcript
                input_text = Transcription.get('clean_transcript', '')
                if not input_text:
                    print("🔍 No clean_transcript, trying segments...")
                    # Final fallback to original format
                    segments = Transcription.get('segments', [])
                    input_text = ""
                    for segment in segments:
                        if isinstance(segment, dict):
                            text = segment.get('text', '')
                            start = segment.get('start_time', 0)
                            end = segment.get('end_time', 0)
                            input_text += f"{start} - {end}: {text}\n"
                        else:
                            # Legacy format: tuple (text, start, end)
                            text, start, end = segment
                            input_text += f"{start} - {end}: {text}\n"
        else:
            print("🔍 Transcription is not dict, using as-is...")
            input_text = Transcription
        
        print(f"🔍 Input text length: {len(input_text)}")
        print(f"🔍 Input text preview: {repr(input_text[:200])}")
        
        # Insert transcript into the prompt template
        print("🔍 Loading system prompt...")
        print(f"🔍 System prompt preview: {system[:200]}...")
        
        print("🔍 Formatting prompt with transcript...")
        try:
            # Use replace instead of format to avoid issues with curly braces in transcript
            prompt_with_transcript = system.replace('{transcript}', input_text)
            print("✅ Prompt formatting successful")
        except Exception as format_error:
            print(f"❌ Error in prompt formatting: {format_error}")
            print(f"   System prompt type: {type(system)}")
            print(f"   Input text type: {type(input_text)}")
            print(f"   Input text sample: {repr(input_text[:100])}")
            raise format_error
        
        print(f"🔤 Transcript length: {len(input_text)} characters")
        print(f"🔤 Prompt length: {len(prompt_with_transcript)} characters")
        print(f"🔤 Prompt preview: {prompt_with_transcript[:300]}...")
        print(f"🔤 Using Azure OpenAI: {USE_AZURE_OPENAI}")
        
        # Save input immediately, regardless of what happens with the response
        save_gpt_interaction(prompt_with_transcript, "REQUEST_SENT", "multiple", gpt_interactions_dir)
            
        if USE_AZURE_OPENAI:
            url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_OPENAI_KEY,
            }
            payload = {
                "messages": [
                    {"role": "user", "content": prompt_with_transcript},
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
                    {"role": "user", "content": prompt_with_transcript},
                ],
            )
            json_string = response.choices[0].message.content

        # Save GPT interaction for debugging (update with actual response)
        save_gpt_interaction(prompt_with_transcript, json_string, "multiple", gpt_interactions_dir)

        # Clean the GPT response and extract segments
        print(f"📤 Raw GPT response preview: {json_string[:100]}...")
        segments = extract_segments(json_string)
        
        if not segments:
            print(f"⚠️  No valid segments found in GPT response")
            Ask = input("Error - Get Highlights again (y/n) -> ").lower()
            if Ask == "y":
                segments = GetMultipleHighlights(Transcription, gpt_interactions_dir)
        return segments
    except Exception as e:
        print(f"Error in GetMultipleHighlights: {e}")
        # Ensure we save the input even if there's an error
        try:
            save_gpt_interaction(prompt_with_transcript, f"ERROR: {str(e)}", "multiple_error", gpt_interactions_dir)
        except:
            pass  # Don't fail if saving fails
        return []


def refine_segments_with_word_timestamps(segments, transcription_result, timestamp_refinement_dir="outputs"):
    """
    Refine segment timestamps using word-level matching with exact quotes
    
    Args:
        segments: List of segments from GPT (may include exact_quote field)
        transcription_result: Dict containing word_segments and other transcription data
        outputs_dir: Directory to save debug information
    
    Returns:
        List of segments with refined timestamps
    """
    if not transcription_result.get('word_segments'):
        print("Warning: No word-level timestamps available, using original segments")
        return segments
    
    from .TimestampUtils import find_word_timestamps
    
    refined_segments = []
    for segment in segments:
        # Prefer exact_quote for matching, fall back to content
        text_to_match = segment.get('exact_quote', segment.get('content', ''))
        
        if not text_to_match:
            refined_segments.append(segment)
            continue
        
        # Clean the text for matching (remove speaker labels if present)
        clean_text = clean_text_for_matching(text_to_match)
        
        print(f"\n🔍 Matching text for '{segment.get('title', 'Untitled')}':")
        print(f"   Original: \"{text_to_match[:100]}{'...' if len(text_to_match) > 100 else ''}\"")
        print(f"   Cleaned:  \"{clean_text[:100]}{'...' if len(clean_text) > 100 else ''}\"")
        
        # Find precise timestamps for this content
        timestamp_result = find_word_timestamps(clean_text, transcription_result['word_segments'])
        
        if timestamp_result and timestamp_result.get('confidence', 0) > 0.5:
            # Update with precise timestamps (preserve decimal precision)
            refined_segment = segment.copy()
            refined_segment['start'] = timestamp_result['start_time']
            refined_segment['end'] = timestamp_result['end_time']
            refined_segment['duration'] = timestamp_result['end_time'] - timestamp_result['start_time']
            refined_segment['word_match_confidence'] = timestamp_result['confidence']
            refined_segment['matched_text'] = clean_text  # Store what was actually matched
            refined_segments.append(refined_segment)
            
            print(f"✅ Refined timing: {refined_segment['start']}-{refined_segment['end']}s (conf: {timestamp_result['confidence']:.2%})")
        else:
            # Keep original if word matching failed
            if 'start' not in segment or segment['start'] == 0:
                # If no original timing, estimate based on position
                segment = estimate_timing_from_position(segment, transcription_result)
            
            refined_segments.append(segment)
            confidence = timestamp_result.get('confidence', 0) if timestamp_result else 0
            print(f"⚠️  Could not refine '{segment.get('title', 'Clip')}' (conf: {confidence:.2%}), using original/estimated timestamps")
    
    # Save refinement details for debugging
    try:
        os.makedirs(timestamp_refinement_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        refinement_path = os.path.join(timestamp_refinement_dir, f"refinement_{timestamp}.json")
        
        refinement_data = {
            "timestamp": datetime.now().isoformat(),
            "original_segments": segments,
            "refined_segments": refined_segments,
            "refinement_summary": {
                "total_segments": len(segments),
                "successfully_refined": len([s for s in refined_segments if 'word_match_confidence' in s]),
                "failed_refinements": len([s for s in refined_segments if 'word_match_confidence' not in s]),
                "avg_confidence": sum(s.get('word_match_confidence', 0) for s in refined_segments) / len(refined_segments) if refined_segments else 0
            }
        }
        
        with open(refinement_path, 'w', encoding='utf-8') as f:
            json.dump(refinement_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n🔍 Timestamp refinement details saved to: {refinement_path}")
        
        # Print summary
        summary = refinement_data['refinement_summary']
        print(f"📊 Refinement Summary:")
        print(f"   • Total clips: {summary['total_segments']}")
        print(f"   • Successfully refined: {summary['successfully_refined']}")
        print(f"   • Failed refinements: {summary['failed_refinements']}")
        print(f"   • Success rate: {summary['successfully_refined']/summary['total_segments']:.1%}")
        print(f"   • Average confidence: {summary['avg_confidence']:.1%}")
        
    except Exception as e:
        print(f"Warning: Failed to save refinement details: {e}")
    
    return refined_segments


def clean_text_for_matching(text):
    """
    Clean text for word-level matching by removing speaker labels and extra formatting
    """
    # Remove speaker labels (e.g., "SPEAKER_00: " or "John: ")
    import re
    
    # Pattern for speaker labels
    speaker_patterns = [
        r'^SPEAKER_\d+:\s*',  # SPEAKER_00: 
        r'^[A-Z_]+:\s*',      # JOHN: or MARY_SMITH:
        r'^\w+:\s*'           # John: or Mary:
    ]
    
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        cleaned_line = line.strip()
        
        # Try to remove speaker labels
        for pattern in speaker_patterns:
            cleaned_line = re.sub(pattern, '', cleaned_line)
        
        if cleaned_line:  # Only add non-empty lines
            cleaned_lines.append(cleaned_line)
    
    return ' '.join(cleaned_lines).strip()


def estimate_timing_from_position(segment, transcription_result):
    """
    Estimate timing for a segment based on its position and content if exact matching fails
    """
    segments = transcription_result.get('segments', [])
    if not segments:
        return segment
    
    # For now, just use a simple fallback
    # In a more sophisticated version, we could try fuzzy matching or content analysis
    total_duration = segments[-1][2] if segments else 60  # Last segment end time
    estimated_start = max(0, total_duration * 0.1)  # Start at 10% through
    estimated_end = min(total_duration, estimated_start + 30)  # 30 second clip
    
    segment = segment.copy()
    segment['start'] = estimated_start
    segment['end'] = estimated_end
    segment['duration'] = estimated_end - estimated_start
    segment['timing_method'] = 'estimated'
    
    return segment


if __name__ == "__main__":
    print(GetHighlight(User))
