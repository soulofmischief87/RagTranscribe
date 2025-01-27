from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import TranscriptionJob
from .forms import TranscriptionForm
from .services.transcription_service import TranscriptionService
import threading


def handle_transcription(job_id):
    """Background task to handle transcription"""
    job = TranscriptionJob.objects.get(id=job_id)
    try:
        job.status = 'processing'
        job.save()
        
        # Initialize service and process file
        service = TranscriptionService()
        result = service.transcribe_file(job.audio_file.path)
        
        if result.error:
            job.status = 'failed'
            job.error_message = result.error
        else:
            job.status = 'completed'
            job.transcript = result.transcript
            
        job.save()
        
    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        job.save()


def index(request):
    """Handle file upload and display upload form"""
    if request.method == 'POST':
        form = TranscriptionForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save()
            # Start transcription in background
            thread = threading.Thread(target=handle_transcription, args=(job.id,))
            thread.start()
            return redirect('job_status', job_id=job.id)
    else:
        form = TranscriptionForm()
    
    recent_jobs = TranscriptionJob.objects.all()[:5]
    return render(request, 'web/index.html', {'form': form, 'recent_jobs': recent_jobs})


def job_status(request, job_id):
    """Display job status and results"""
    job = get_object_or_404(TranscriptionJob, id=job_id)
    return render(request, 'web/job_status.html', {'job': job})


@csrf_exempt
def check_status(request, job_id):
    """API endpoint to check job status"""
    job = get_object_or_404(TranscriptionJob, id=job_id)
    return JsonResponse({
        'status': job.status,
        'transcript': job.transcript if job.status == 'completed' else None,
        'error': job.error_message if job.status == 'failed' else None
    })
