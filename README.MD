# GasMan Transcriber

A Django-based audio transcription service that uses Google Cloud Speech-to-Text API for accurate transcription with speaker diarization. This service is part of the GasMan 2000 platform, designed to help process and analyze gas station-related audio recordings.

## Features

- Audio file transcription with speaker diarization
- Support for multiple audio formats (WAV, MP3, FLAC, OGG)
- Automatic upload to Google Cloud Storage
- Local and cloud storage of transcriptions
- Web interface for managing transcription jobs
- Real-time transcription progress tracking

## Prerequisites

- Python 3.8 or higher
- Google Cloud Platform account with Speech-to-Text API enabled
- Google Cloud service account credentials
- Django 5.0.1 or higher

## Installation

1. Clone the repository:
```bash
git clone https://github.com/soulofmischief87/GasManTranscribe.git
cd GasManTranscribe
conda create --name transcription python=3.8
conda activate transcription

2. Install dependencies:
```
pip install -r requirements.txt
```

run with python manage.py runserver

