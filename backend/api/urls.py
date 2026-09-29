from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health),                        # GET  status of the backend
    path("login/", views.login),                          # POST check username/password
    path("analyze/", views.analyze),                      # POST upload resume + JD -> report
    path("analysis/<str:analysis_id>/", views.analysis),  # GET  a saved report
    path("chat/", views.chat),                            # POST ask a question (RAG)
    path("evaluate/", views.evaluate),                    # POST run the retrieval evaluation
]
