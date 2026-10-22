from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Source, SourceFile, Question

@login_required(login_url='/login')
def home_page(request):
    return render(request, 'kb/ask.html')

@login_required(login_url='/login')
def sources_page(request):
    sources = Source.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'kb/sources.html', {'sources': sources})

@login_required(login_url='/login')
def source_new_page(request):
    return render(request, 'kb/source_new.html')

@login_required(login_url='/login')
def source_detail_page(request, source_id):
    source = get_object_or_404(Source, id=source_id, owner=request.user)
    return render(request, 'kb/source_detail.html', {'source': source})

@login_required(login_url='/login')
def file_detail_page(request, source_id, file_id):
    source = get_object_or_404(Source, id=source_id, owner=request.user)
    source_file = get_object_or_404(SourceFile, id=file_id, source=source)
    return render(request, 'kb/file_detail.html', {'source': source, 'file': source_file})

@login_required(login_url='/login')
def questions_page(request):
    questions = Question.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'kb/questions.html', {'questions': questions})

@login_required(login_url='/login')
def question_detail_page(request, question_id):
    question = get_object_or_404(Question, id=question_id, owner=request.user)
    return render(request, 'kb/question_detail.html', {'question': question})
