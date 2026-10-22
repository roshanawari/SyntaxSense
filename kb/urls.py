from django.urls import path
from . import views
from . import api_sources
from . import api_ask
from . import api_questions

urlpatterns = [
    # Pages
    path('', views.home_page, name='home'),
    path('sources', views.sources_page, name='sources'),
    path('sources/new', views.source_new_page, name='source_new'),
    path('sources/<int:source_id>', views.source_detail_page, name='source_detail'),
    path('sources/<int:source_id>/files/<int:file_id>', views.file_detail_page, name='file_detail'),
    path('questions', views.questions_page, name='questions'),
    path('questions/<int:question_id>', views.question_detail_page, name='question_detail'),

    # API - Sources
    path('api/sources', api_sources.api_sources_list, name='api_sources_list'),
    path('api/sources/text', api_sources.api_source_add_text, name='api_source_add_text'),
    path('api/sources/upload', api_sources.api_source_add_upload, name='api_source_add_upload'),
    path('api/sources/github', api_sources.api_source_add_github, name='api_source_add_github'),
    path('api/sources/<int:source_id>', api_sources.api_source_detail, name='api_source_detail'),
    path('api/sources/<int:source_id>/files/<int:file_id>', api_sources.api_source_file_detail, name='api_source_file_detail'),

    # API - Ask & Questions
    path('api/ask', api_ask.api_ask, name='api_ask'),
    path('api/questions', api_questions.api_questions_list, name='api_questions_list'),
    path('api/questions/<int:question_id>', api_questions.api_question_detail, name='api_question_detail'),
]
