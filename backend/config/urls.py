from django.urls import path, include, re_path
from api.views import react_app

urlpatterns = [
    path("api/", include("api.urls")),   # all backend APIs start with /api/
    re_path(r"^.*$", react_app),         # every other address -> the React app
]
