import json
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

# --- HTML Page Views ---

def register_page(request):
    if request.user.is_authenticated:
        return redirect('/')
    return render(request, 'accounts/register.html')

def login_page(request):
    if request.user.is_authenticated:
        return redirect('/')
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    return redirect('/login')

# --- JSON API Views ---

@require_http_methods(["POST"])
def api_register(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse(
            {"error": {"code": "BAD_REQUEST", "message": "Invalid JSON body"}},
            status=400
        )

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return JsonResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "Email and password are required"}},
            status=400
        )

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "Invalid email address"}},
            status=400
        )

    if len(password) < 8 or len(password) > 128:
        return JsonResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "Password must be between 8 and 128 characters"}},
            status=400
        )

    if User.objects.filter(username=email).exists():
        return JsonResponse(
            {"error": {"code": "EMAIL_EXISTS", "message": "Email already in use"}},
            status=409
        )

    user = User.objects.create_user(username=email, email=email, password=password)
    login(request, user)
    return JsonResponse({"id": user.id, "email": user.email}, status=201)

@require_http_methods(["POST"])
def api_login(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse(
            {"error": {"code": "BAD_REQUEST", "message": "Invalid JSON body"}},
            status=400
        )

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return JsonResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "Email and password are required"}},
            status=400
        )

    user = authenticate(request, username=email, password=password)
    if user is None:
        return JsonResponse(
            {"error": {"code": "INVALID_CREDENTIALS", "message": "Wrong email or password"}},
            status=401
        )

    login(request, user)
    return JsonResponse({"id": user.id, "email": user.email}, status=200)

@require_http_methods(["POST"])
def api_logout(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}},
            status=401
        )

    logout(request)
    return HttpResponse(status=204)
