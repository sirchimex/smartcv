from django.urls import path
from . import views

app_name = "ai"

urlpatterns = [
    path("cvs/<int:pk>/ai/summary/",          views.ai_rewrite_summary,    name="rewrite_summary"),
    path("cvs/<int:pk>/ai/analyze/",           views.ai_analyze,            name="analyze"),
    path("cvs/<int:pk>/ai/career/",            views.ai_career_suggestions, name="career_suggestions"),
    path("cvs/<int:pk>/ai/improve-bullet/",    views.ai_improve_bullet,     name="improve_bullet"),
    path("cvs/<int:pk>/ai/field-suggestions/", views.ai_field_suggestions,  name="field_suggestions"),
]
