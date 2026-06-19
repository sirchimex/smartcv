from django.urls import path

from . import views

app_name = "resumes"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("cvs/", views.resume_list, name="list"),
    path("cvs/new/", views.resume_create, name="create"),
    path("cvs/<int:pk>/delete/", views.resume_delete, name="delete"),
    path("cvs/<int:pk>/duplicate/", views.resume_duplicate, name="duplicate"),
    path("cvs/<int:pk>/", views.builder, name="builder"),
    path("cvs/<int:pk>/details/", views.resume_meta_edit, name="meta_edit"),
    path("cvs/<int:pk>/personal-info/", views.personal_info_edit, name="personal_info_edit"),
    path("cvs/<int:pk>/customize/", views.customize, name="customize"),
    path("cvs/<int:pk>/template/", views.template_picker, name="template_picker"),
    path("cvs/<int:pk>/experience/", views.experience_edit, name="experience_edit"),
    path("cvs/<int:pk>/education/", views.education_edit, name="education_edit"),
    path("cvs/<int:pk>/preview/", views.resume_preview, name="preview"),
    path("cvs/<int:pk>/pdf/", views.resume_pdf, name="pdf"),
    path("cvs/<int:pk>/sections/<str:key>/", views.section_list, name="section_list"),
    path("cvs/<int:pk>/sections/<str:key>/add/", views.section_item_form, name="section_add"),
    path(
        "cvs/<int:pk>/sections/<str:key>/<int:item_pk>/edit/",
        views.section_item_form,
        name="section_edit",
    ),
    path(
        "cvs/<int:pk>/sections/<str:key>/<int:item_pk>/delete/",
        views.section_item_delete,
        name="section_delete",
    ),
]
