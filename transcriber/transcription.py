from google.cloud import speech_v1
from google.cloud import storage
import os
from dotenv import load_dotenv

load_dotenv()

def upload_to_gcs(file_path, bucket_name="transcriber_audio_files"):
    """Upload a file to Google Cloud Storage.
    
    Args:
        file_path (str): Path to the local file
        bucket_name (str): Name of the GCS bucket
    
    Returns:
        str: GCS URI of the uploaded file
    """
    storage_client = storage.Client()
    
    # Create bucket if it doesn't exist
    try:
        bucket = storage_client.get_bucket(bucket_name)
    except Exception:
        bucket = storage_client.create_bucket(bucket_name)
    
    # Upload file
    blob_name = os.path.basename(file_path)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path)
    
    return f"gs://{bucket_name}/{blob_name}"

def transcribe_file_with_diarization(file_path):
    """
    Transcribe the given audio file using Google Cloud Speech-to-Text with speaker diarization.
    
    Args:
        file_path (str): Path to the audio file to transcribe
    Returns:
        str: The formatted transcript with speaker labels
    """
    client = speech_v1.SpeechClient()
    
    # Check file size
    file_size = os.path.getsize(file_path)
    use_gcs = file_size > 10 * 1024 * 1024  # 10MB limit
    
    # Configure audio input
    if use_gcs:
        print("File is larger than 10MB, uploading to Google Cloud Storage...")
        gcs_uri = upload_to_gcs(file_path)
        audio = speech_v1.RecognitionAudio(uri=gcs_uri)
    else:
        with open(file_path, "rb") as audio_file:
            content = audio_file.read()
        audio = speech_v1.RecognitionAudio(content=content)

    # Configure the recognition settings
    diarization_config = speech_v1.SpeakerDiarizationConfig(
        enable_speaker_diarization=True,
        min_speaker_count=2,
        max_speaker_count=int(os.getenv('SPEAKER_COUNT', '2'))
    )

    config = speech_v1.RecognitionConfig(
        encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=int(os.getenv('SAMPLE_RATE', '16000')),
        language_code=os.getenv('LANGUAGE_CODE', 'en-US'),
        diarization_config=diarization_config
    )

    print("Starting transcription...")
    
    # Make the API call
    operation = client.long_running_recognize(
        config=config,
        audio=audio
    )
    
    print("Waiting for operation to complete...")
    response = operation.result(timeout=90)
    
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

    # Clean up GCS if used
    if use_gcs:
        try:
            storage_client = storage.Client()
            bucket = storage_client.get_bucket("transcriber_audio_files")
            blob = bucket.blob(os.path.basename(file_path))
            blob.delete()
        except Exception as e:
            print(f"Warning: Could not delete temporary GCS file: {e}")

    # Join all lines with newlines
    return '\n'.join(transcript)
