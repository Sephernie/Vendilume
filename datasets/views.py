from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .models import Dataset


def dataset_history(request):
    datasets = Dataset.objects.all()

    context = {
        "datasets": datasets,
    }

    return render(request, "datasets/history.html", context)


def dataset_detail(request, pk):
    dataset = get_object_or_404(
        Dataset.objects.prefetch_related("warnings"),
        pk=pk,
    )

    context = {
        "dataset": dataset,
    }

    return render(request, "datasets/detail.html", context)


def delete_dataset(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk)

    if request.method == "POST":
        dataset_name = dataset.name
        dataset.delete()

        messages.success(
            request,
            f'"{dataset_name}" was deleted successfully.',
        )

        return redirect("datasets:history")

    context = {
        "dataset": dataset,
    }

    return render(request, "datasets/delete_confirm.html", context)


def upload_dataset(request):
    return render(request, "datasets/upload.html")
