from google.cloud import speech_v1
from google.cloud.speech_v1 import enums
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def transcribe_file_with_diarization(file_path):
    """
    Transcribe the given audio file using Google Cloud Speech-to-Text with speaker diarization.
    
    Args:
        file_path (str): Path to the audio file to transcribe
    """
    client = speech_v1.SpeechClient()

    # Read the audio file
    with open(file_path, "rb") as audio_file:
        content = audio_file.read()

    # Configure the recognition settings
    audio = speech_v1.RecognitionAudio(content=content)
    
    # Get speaker count from environment variable, default to 2 if not set
    speaker_count = int(os.getenv('SPEAKER_COUNT', '2'))
    
    config = speech_v1.RecognitionConfig(
        encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=int(os.getenv('SAMPLE_RATE', '16000')),
        language_code=os.getenv('LANGUAGE_CODE', 'en-US'),
        enable_speaker_diarization=True,
        diarization_speaker_count=speaker_count
    )

    print("Starting transcription...")
    
    # Make the API call
    response = client.recognize(config=config, audio=audio)
    
    # Process the response
    result = response.results[-1]
    words_info = result.alternatives[0].words

    # Extract words with speaker tags
    transcript = []
    current_speaker = None
    current_line = []

    for word_info in words_info:
        if word_info.speaker_tag != current_speaker:
            if current_line:
                transcript.append(f"Speaker {current_speaker}: {' '.join(current_line)}")
                current_line = []
            current_speaker = word_info.speaker_tag
        current_line.append(word_info.word)

    # Add the last line
    if current_line:
        transcript.append(f"Speaker {current_speaker}: {' '.join(current_line)}")

    # Print the transcript
    print("\nTranscript with speaker diarization:")
    for line in transcript:
        print(line)

    # Save transcript to file if output path is specified
    output_path = os.getenv('OUTPUT_PATH')
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(transcript))
        print(f"\nTranscript saved to: {output_path}")

def main():
    # Get credentials path from environment variable
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set in .env file")
    
    # Get audio file path from environment variable
    audio_file_path = os.getenv('AUDIO_FILE_PATH')
    if not audio_file_path:
        raise ValueError("AUDIO_FILE_PATH not set in .env file")
    
    try:
        transcribe_file_with_diarization(audio_file_path)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()