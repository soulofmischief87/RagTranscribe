from google.cloud import speech_v1
from google.cloud import storage
import os
from dotenv import load_dotenv
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import time

load_dotenv()

@dataclass
class TranscriptionResult:
    """Data class for transcription results"""
    transcript: str
    speakers: int
    duration: float
    created_at: datetime
    error: Optional[str] = None

class TranscriptionService:
    def __init__(self):
        self.speech_client = speech_v1.SpeechClient()
        self.storage_client = storage.Client()
        self.bucket_name = os.getenv('GCS_BUCKET_NAME', 'gasman2000-transcriptions')
        self.operation_timeout = int(os.getenv('OPERATION_TIMEOUT', '600'))  # 10 minutes default
        self.poll_interval = 30  # seconds

    def _get_audio_encoding(self, file_path: str) -> Tuple[speech_v1.RecognitionConfig.AudioEncoding, int]:
        """Determine the audio encoding and sample rate based on file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        
        # Default sample rate
        sample_rate = int(os.getenv('SAMPLE_RATE', '16000'))
        
        # Map file extensions to Google Cloud Speech encodings
        encoding_map = {
            '.wav': speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
            '.mp3': speech_v1.RecognitionConfig.AudioEncoding.MP3,
            '.flac': speech_v1.RecognitionConfig.AudioEncoding.FLAC,
            '.ogg': speech_v1.RecognitionConfig.AudioEncoding.OGG_OPUS
        }
        
        encoding = encoding_map.get(ext, speech_v1.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED)
        
        if encoding == speech_v1.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED:
            raise ValueError(f"Unsupported audio format: {ext}. Supported formats are: WAV, MP3, FLAC, OGG")
            
        return encoding, sample_rate

    def _wait_for_operation(self, operation):
        """Wait for a long-running operation with progress updates"""
        start_time = time.time()
        last_progress = start_time
        
        while True:
            if operation.done():
                return operation.result()
            
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            # Check if we've exceeded the timeout
            if elapsed_time > self.operation_timeout:
                raise TimeoutError(f"Operation did not complete within {self.operation_timeout} seconds")
            
            # Print progress update every poll_interval seconds
            if current_time - last_progress >= self.poll_interval:
                print(f"Transcription in progress... {int(elapsed_time)}s elapsed")
                if operation.metadata:
                    progress = operation.metadata.progress_percent
                    if progress:
                        print(f"Progress: {progress}%")
                last_progress = current_time
            
            # Wait before next check
            time.sleep(min(10, self.poll_interval))

    def _upload_to_gcs(self, file_path: str) -> str:
        """Upload a file to Google Cloud Storage."""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            if not bucket.exists():
                raise Exception(f"Bucket {self.bucket_name} does not exist. Please create it in the Google Cloud Console.")
            
            blob_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(file_path)}"
            blob = bucket.blob(blob_name)
            
            # Upload with size logging
            file_size = os.path.getsize(file_path)
            print(f"Starting upload of {file_size/(1024*1024):.1f} MB file...")
            
            blob.upload_from_filename(file_path)
            print("Upload completed successfully")
            
            return f"gs://{self.bucket_name}/{blob_name}"
        except Exception as e:
            raise Exception(f"Failed to upload file to GCS: {str(e)}")

    def _cleanup_gcs_file(self, gcs_uri: str) -> None:
        """Clean up temporary file from GCS"""
        try:
            blob_name = gcs_uri.split('/')[-1]
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()
        except Exception as e:
            print(f"Warning: Could not delete temporary GCS file: {e}")

    def _save_transcript_to_file(self, transcript: str, original_filename: str) -> str:
        """Save transcript to a file locally and to GCS completed_transcriptions folder"""
        output_path = os.getenv('OUTPUT_PATH', 'transcripts/')
        
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Create filename based on original audio file
        base_name = os.path.splitext(os.path.basename(original_filename))[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"{base_name}_{timestamp}.txt"
        output_file = os.path.join(output_path, output_filename)
        
        # Save transcript locally
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(transcript)
            
        # Upload to GCS completed_transcriptions folder
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(f"completed_transcriptions/{output_filename}")
            blob.upload_from_string(transcript)
            print(f"Uploaded transcript to gs://{self.bucket_name}/completed_transcriptions/{output_filename}")
        except Exception as e:
            print(f"Warning: Could not upload transcript to GCS: {e}")
        
        return output_file

    def transcribe_file(self, file_path: str) -> TranscriptionResult:
        """Transcribe an audio file with speaker diarization."""
        gcs_uri = None
        try:
            start_time = datetime.now()
            
            # Get audio encoding and sample rate
            encoding, sample_rate = self._get_audio_encoding(file_path)
            
            # Handle large files via GCS
            file_size = os.path.getsize(file_path)
            use_gcs = file_size > 10 * 1024 * 1024  # 10MB limit
            
            if use_gcs:
                print(f"File size: {file_size/(1024*1024):.1f} MB")
                print("Uploading to Google Cloud Storage...")
                gcs_uri = self._upload_to_gcs(file_path)
                audio = speech_v1.RecognitionAudio(uri=gcs_uri)
            else:
                with open(file_path, "rb") as audio_file:
                    content = audio_file.read()
                audio = speech_v1.RecognitionAudio(content=content)

            # Configure speaker diarization
            diarization_config = speech_v1.SpeakerDiarizationConfig(
                enable_speaker_diarization=True,
                min_speaker_count=2,
                max_speaker_count=int(os.getenv('SPEAKER_COUNT', '2'))
            )

            # Configure recognition
            config = speech_v1.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=sample_rate,
                language_code=os.getenv('LANGUAGE_CODE', 'en-US'),
                diarization_config=diarization_config
            )

            print(f"Starting transcription with encoding: {encoding}")
            operation = self.speech_client.long_running_recognize(config=config, audio=audio)
            
            print("Waiting for operation to complete...")
            response = self._wait_for_operation(operation)

            # Clean up GCS file if used
            if gcs_uri:
                self._cleanup_gcs_file(gcs_uri)

            # Process results
            result = response.results[-1]
            words_info = result.alternatives[0].words

            # Group words by speaker
            transcript_lines = []
            current_speaker = None
            current_line = []
            speaker_set = set()

            for word_info in words_info:
                speaker_set.add(word_info.speaker_tag)
                if word_info.speaker_tag != current_speaker:
                    if current_line:
                        transcript_lines.append(f"Speaker {current_speaker}: {' '.join(current_line)}")
                        current_line = []
                    current_speaker = word_info.speaker_tag
                current_line.append(word_info.word)

            if current_line:
                transcript_lines.append(f"Speaker {current_speaker}: {' '.join(current_line)}")

            # Create the final transcript
            transcript = '\n'.join(transcript_lines)
            
            # Save to file
            output_file = self._save_transcript_to_file(transcript, file_path)
            print(f"Transcript saved to: {output_file}")

            return TranscriptionResult(
                transcript=transcript,
                speakers=len(speaker_set),
                duration=(datetime.now() - start_time).total_seconds(),
                created_at=datetime.now()
            )

        except Exception as e:
            if gcs_uri:
                self._cleanup_gcs_file(gcs_uri)
            return TranscriptionResult(
                transcript="",
                speakers=0,
                duration=0,
                created_at=datetime.now(),
                error=str(e)
            )
