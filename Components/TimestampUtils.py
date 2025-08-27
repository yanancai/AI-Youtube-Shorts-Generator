"""
Utility functions for handling word-level timestamps and text matching
"""
import difflib
import json
import os
from datetime import datetime


def find_word_timestamps(text_to_find, word_segments):
    """
    Find word-level timestamps for a given text by matching words
    
    Args:
        text_to_find: The text to find timestamps for
        word_segments: List of word segments with timestamps
    
    Returns:
        dict with start_time, end_time, and matched_words
    """
    if not word_segments:
        return None
    
    # Clean and split the target text
    target_words = text_to_find.strip().lower().split()
    if not target_words:
        return None
    
    # Create a list of word strings for matching
    transcript_words = [word['word'].lower().strip() for word in word_segments]
    
    # Use difflib to find the best matching sequence
    matcher = difflib.SequenceMatcher(None, transcript_words, target_words)
    match = matcher.find_longest_match(0, len(transcript_words), 0, len(target_words))
    
    # Dynamic confidence threshold - more lenient for longer segments
    if len(target_words) <= 20:
        confidence_threshold = 0.8  # 80% for short segments
    elif len(target_words) <= 50:
        confidence_threshold = 0.7  # 70% for medium segments  
    elif len(target_words) <= 100:
        confidence_threshold = 0.6  # 60% for long segments
    else:
        confidence_threshold = 0.5  # 50% for very long segments (200+ words)
    
    match_ratio = match.size / len(target_words)
    if match_ratio < confidence_threshold:
        print(f"Warning: Poor match for text ({match.size}/{len(target_words)} = {match_ratio:.2f}, need {confidence_threshold:.2f}): {text_to_find[:50]}...")
        return None
    
    # Get timestamps for the matched words
    start_idx = match.a
    end_idx = start_idx + match.size
    
    if end_idx > len(word_segments):
        end_idx = len(word_segments)
    
    start_time = word_segments[start_idx]['start']
    end_time = word_segments[end_idx - 1]['end']
    
    matched_words = word_segments[start_idx:end_idx]
    
    return {
        'start_time': start_time,
        'end_time': end_time,
        'matched_words': matched_words,
        'confidence': match_ratio
    }


def validate_segment_timing(segments, max_duration=60):
    """
    Validate and adjust segment timings
    
    Args:
        segments: List of segments with start/end times
        max_duration: Maximum allowed duration in seconds
    
    Returns:
        List of validated segments
    """
    validated_segments = []
    
    for segment in segments:
        start = segment.get('start', 0)
        end = segment.get('end', 0)
        duration = end - start
        
        if duration <= 0:
            print(f"Warning: Invalid segment duration {duration}s for '{segment.get('title', 'Unknown')}'")
            continue
        
        if duration > max_duration:
            print(f"Warning: Segment '{segment.get('title', 'Unknown')}' duration {duration}s exceeds {max_duration}s limit")
            # Truncate to max duration
            segment = segment.copy()
            segment['end'] = segment['start'] + max_duration
            segment['duration'] = max_duration
        
        validated_segments.append(segment)
    
    return validated_segments


def merge_overlapping_segments(segments, overlap_threshold=2.0):
    """
    Merge segments that have significant overlap
    
    Args:
        segments: List of segments sorted by start time
        overlap_threshold: Minimum overlap in seconds to trigger merge
    
    Returns:
        List of merged segments
    """
    if len(segments) <= 1:
        return segments
    
    merged = []
    current = segments[0].copy()
    
    for next_segment in segments[1:]:
        overlap = current['end'] - next_segment['start']
        
        if overlap >= overlap_threshold:
            # Merge segments
            current['end'] = max(current['end'], next_segment['end'])
            current['duration'] = current['end'] - current['start']
            current['title'] = f"{current.get('title', '')}_merged_{next_segment.get('title', '')}"
            current['content'] = f"{current.get('content', '')} {next_segment.get('content', '')}"
            current['priority'] = min(current.get('priority', 5), next_segment.get('priority', 5))
        else:
            merged.append(current)
            current = next_segment.copy()
    
    merged.append(current)
    return merged


def create_timing_report(original_segments, refined_segments, outputs_dir):
    """
    Create a detailed report comparing original vs refined timings
    """
    try:
        report_dir = os.path.join(outputs_dir, "timing_reports")
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_dir, f"timing_report_{timestamp}.json")
        
        comparisons = []
        total_drift = 0
        successful_refinements = 0
        
        for i, (orig, refined) in enumerate(zip(original_segments, refined_segments)):
            start_drift = abs(orig['start'] - refined['start'])
            end_drift = abs(orig['end'] - refined['end'])
            avg_drift = (start_drift + end_drift) / 2
            
            total_drift += avg_drift
            
            if 'word_match_confidence' in refined:
                successful_refinements += 1
            
            comparison = {
                'segment_index': i,
                'title': orig.get('title', f'Clip {i+1}'),
                'original': {
                    'start': orig['start'],
                    'end': orig['end'],
                    'duration': orig.get('duration', orig['end'] - orig['start'])
                },
                'refined': {
                    'start': refined['start'],
                    'end': refined['end'],
                    'duration': refined.get('duration', refined['end'] - refined['start'])
                },
                'drift': {
                    'start_drift': start_drift,
                    'end_drift': end_drift,
                    'avg_drift': avg_drift
                },
                'word_match_confidence': refined.get('word_match_confidence', None),
                'refinement_successful': 'word_match_confidence' in refined
            }
            comparisons.append(comparison)
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_segments': len(original_segments),
                'successful_refinements': successful_refinements,
                'failed_refinements': len(original_segments) - successful_refinements,
                'avg_timing_drift': total_drift / len(original_segments) if original_segments else 0,
                'refinement_success_rate': successful_refinements / len(original_segments) if original_segments else 0
            },
            'comparisons': comparisons
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Timing report saved to: {report_path}")
        print(f"   - Success rate: {report_data['summary']['refinement_success_rate']:.1%}")
        print(f"   - Average drift: {report_data['summary']['avg_timing_drift']:.2f}s")
        
        return report_data
        
    except Exception as e:
        print(f"Warning: Failed to create timing report: {e}")
        return None


if __name__ == "__main__":
    # Test functions
    pass
