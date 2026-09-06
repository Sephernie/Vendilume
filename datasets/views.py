from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from pathlib import Path
from tempfile import TemporaryDirectory

from datetime import datetime, time, timedelta, timezone as datetime_timezone
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import urlopen

from django.conf import settings

from .services.csv_processor import (
    CsvValidationError,
    read_and_validate_csv,
)
from .services.dataset_importer import (
    persist_processed_dataset,
)
from .services.analytics_insights import (
    generate_sales_insights,
)

from .forms import AnalyticsFilterForm, DatasetUploadForm
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
    if request.method == "POST":
        form = DatasetUploadForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]

            with TemporaryDirectory() as temporary_directory:
                temporary_path = (
                    Path(temporary_directory)
                    / "uploaded.csv"
                )

                with temporary_path.open("wb") as destination:
                    for chunk in csv_file.chunks():
                        destination.write(chunk)

                try:
                    result = read_and_validate_csv(
                        temporary_path
                    )
                except CsvValidationError as error:
                    for validation_error in error.errors:
                        form.add_error(
                            "csv_file",
                            validation_error,
                        )
                else:
                    dataset = persist_processed_dataset(
                        result=result,
                        name=form.cleaned_data["name"],
                        original_filename=csv_file.name,
                        currency=form.cleaned_data[
                            "currency"
                        ],
                    )

                    messages.success(
                        request,
                        f'"{dataset.name}" was imported '
                        "successfully.",
                    )

                    return redirect(
                        "datasets:detail",
                        pk=dataset.pk,
                    )
    else:
        form = DatasetUploadForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "datasets/upload.html",
        context,
    )


def dataset_analytics(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk)

    grafana_available = False
    dashboard_url = None
    filter_form = None
    insights = []

    selected_start_date = dataset.start_date
    selected_end_date = dataset.end_date
    selected_product = ""
    selected_category = ""
    selected_region = ""
    selected_sales_channel = ""
    selected_customer = ""

    if dataset.status == Dataset.Status.READY:
        filter_form = AnalyticsFilterForm(
            request.GET or None,
            dataset=dataset,
        )

        if filter_form.is_bound and filter_form.is_valid():
            selected_start_date = filter_form.cleaned_data[
                "start_date"
            ]
            selected_end_date = filter_form.cleaned_data[
                "end_date"
            ]
            selected_product = filter_form.cleaned_data[
                "product"
            ]
            selected_category = filter_form.cleaned_data[
                "category"
            ]
            selected_region = filter_form.cleaned_data.get(
                "region",
                "",
            )
            selected_sales_channel = filter_form.cleaned_data.get(
                "sales_channel",
                "",
            )
            selected_customer = filter_form.cleaned_data.get(
                "customer",
                "",
            )

        if selected_start_date and selected_end_date:
            insights = generate_sales_insights(
                dataset=dataset,
                start_date=selected_start_date,
                end_date=selected_end_date,
                product=selected_product,
                category=selected_category,
                region=selected_region,
                sales_channel=selected_sales_channel,
                customer=selected_customer,
            )

        try:
            health_url = f"{settings.GRAFANA_BASE_URL}/api/health"

            with urlopen(health_url, timeout=2) as response:
                grafana_available = response.status == 200
        except (OSError, URLError):
            grafana_available = False

        if grafana_available:
            parameters = {
                "var-dataset_id": dataset.pk,
                "var-product": selected_product or "$__all",
                "var-category": selected_category or "$__all",
                "var-region": selected_region or "$__all",
                "var-sales_channel": (
                    selected_sales_channel or "$__all"
                ),
                "var-customer": selected_customer or "$__all",
                "kiosk": "tv",
            }

            if selected_start_date and selected_end_date:
                range_start = datetime.combine(
                    selected_start_date,
                    time.min,
                    tzinfo=datetime_timezone.utc,
                )
                range_end = datetime.combine(
                    selected_end_date + timedelta(days=1),
                    time.min,
                    tzinfo=datetime_timezone.utc,
                )

                parameters["from"] = int(
                    range_start.timestamp() * 1000
                )
                parameters["to"] = (
                    int(range_end.timestamp() * 1000) - 1
                )

            dashboard_url = (
                f"{settings.GRAFANA_BASE_URL}"
                f"/d/{settings.GRAFANA_DASHBOARD_UID}"
                f"/vendilume-sales-overview?"
                f"{urlencode(parameters)}"
            )

    return render(
        request,
        "datasets/analytics.html",
        {
            "dataset": dataset,
            "filter_form": filter_form,
            "insights": insights,
            "grafana_available": grafana_available,
            "dashboard_url": dashboard_url,
        },
    )
