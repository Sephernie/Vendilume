from django.urls import path

from . import views


app_name = "datasets"

urlpatterns = [
    path("history/", views.dataset_history, name="history"),
    path("upload/", views.upload_dataset, name="upload"),
    path(
        "<int:pk>/delete/",
        views.delete_dataset,
        name="delete",
    ),
    path("<int:pk>/", views.dataset_detail, name="detail"),
]
