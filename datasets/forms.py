from pathlib import Path

from django import forms
from .models import SalesLine, SalesOrder


MAX_UPLOAD_SIZE = 10 * 1024 * 1024


class DatasetUploadForm(forms.Form):
    name = forms.CharField(
        label="Dataset name",
        max_length=255,
        required=False,
        help_text=(
            "Optional. If left empty, the name will be derived "
            "from the CSV filename."
        ),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "For example: January 2026 Sales",
            }
        ),
    )

    currency = forms.CharField(
        label="Currency",
        min_length=3,
        max_length=3,
        help_text="Enter a three-letter currency code such as EUR or USD.",
        widget=forms.TextInput(
            attrs={
                "class": "form-control text-uppercase",
                "placeholder": "EUR",
                "autocomplete": "off",
            }
        ),
    )

    csv_file = forms.FileField(
        label="Sales CSV file",
        allow_empty_file=True,
        help_text=(
            "Upload a UTF-8 CSV file no larger than 10 MB."
        ),
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".csv,text/csv",
            }
        ),
    )

    def clean_currency(self):
        currency = self.cleaned_data["currency"].strip().upper()

        if not currency.isascii() or not currency.isalpha():
            raise forms.ValidationError(
                "Enter a valid three-letter currency code using A–Z."
            )

        return currency

    def clean_csv_file(self):
        csv_file = self.cleaned_data["csv_file"]
        extension = Path(csv_file.name).suffix.lower()

        if extension != ".csv":
            raise forms.ValidationError(
                "The uploaded file must use the .csv extension."
            )

        if csv_file.size == 0:
            raise forms.ValidationError(
                "The uploaded CSV file is empty."
            )

        if csv_file.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                "The uploaded CSV file must not exceed 10 MB."
            )

        return csv_file


class AnalyticsFilterForm(forms.Form):
    start_date = forms.DateField(
        label="From",
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    end_date = forms.DateField(
        label="To",
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    product = forms.ChoiceField(
        label="Product",
        required=False,
        choices=(),
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    category = forms.ChoiceField(
        label="Category",
        required=False,
        choices=(),
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    region = forms.ChoiceField(
        label="Region",
        required=False,
        choices=(),
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    sales_channel = forms.ChoiceField(
        label="Sales channel",
        required=False,
        choices=(),
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    customer = forms.ChoiceField(
        label="Customer",
        required=False,
        choices=(),
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    def __init__(self, *args, dataset, **kwargs):
        super().__init__(*args, **kwargs)

        self.dataset = dataset

        products = (
            SalesLine.objects
            .filter(order__dataset=dataset)
            .order_by("product_name")
            .values_list("product_name", flat=True)
            .distinct()
        )

        categories = (
            SalesLine.objects
            .filter(order__dataset=dataset)
            .order_by("category")
            .values_list("category", flat=True)
            .distinct()
        )

        self.fields["product"].choices = [
            ("", "All products"),
            *((product, product) for product in products),
        ]

        self.fields["category"].choices = [
            ("", "All categories"),
            *((category, category) for category in categories),
        ]

        if dataset.has_region:
            regions = (
                SalesOrder.objects
                .filter(dataset=dataset)
                .exclude(region__isnull=True)
                .exclude(region="")
                .order_by("region")
                .values_list("region", flat=True)
                .distinct()
            )

            self.fields["region"].choices = [
                ("", "All regions"),
                *((region, region) for region in regions),
            ]
        else:
            self.fields.pop("region")

        if dataset.has_sales_channel:
            sales_channels = (
                SalesOrder.objects
                .filter(dataset=dataset)
                .exclude(sales_channel__isnull=True)
                .exclude(sales_channel="")
                .order_by("sales_channel")
                .values_list("sales_channel", flat=True)
                .distinct()
            )

            self.fields["sales_channel"].choices = [
                ("", "All sales channels"),
                *(
                    (sales_channel, sales_channel)
                    for sales_channel in sales_channels
                ),
            ]
        else:
            self.fields.pop("sales_channel")

        if dataset.has_customer_id:
            customers = (
                SalesOrder.objects
                .filter(dataset=dataset)
                .exclude(customer_id__isnull=True)
                .exclude(customer_id="")
                .order_by("customer_id")
                .values_list("customer_id", flat=True)
                .distinct()
            )

            self.fields["customer"].choices = [
                ("", "All customers"),
                *((customer, customer) for customer in customers),
            ]
        else:
            self.fields.pop("customer")

        if dataset.start_date:
            self.fields["start_date"].initial = dataset.start_date
            self.fields["start_date"].widget.attrs["min"] = (
                dataset.start_date.isoformat()
            )
            self.fields["start_date"].widget.attrs["max"] = (
                dataset.end_date.isoformat()
            )

        if dataset.end_date:
            self.fields["end_date"].initial = dataset.end_date
            self.fields["end_date"].widget.attrs["min"] = (
                dataset.start_date.isoformat()
            )
            self.fields["end_date"].widget.attrs["max"] = (
                dataset.end_date.isoformat()
            )

    def clean(self):
        cleaned_data = super().clean()

        start_date = (
            cleaned_data.get("start_date")
            or self.dataset.start_date
        )
        end_date = (
            cleaned_data.get("end_date")
            or self.dataset.end_date
        )

        cleaned_data["start_date"] = start_date
        cleaned_data["end_date"] = end_date

        if (
            start_date
            and self.dataset.start_date
            and start_date < self.dataset.start_date
        ):
            self.add_error(
                "start_date",
                "The start date cannot be earlier than this dataset.",
            )

        if (
            end_date
            and self.dataset.end_date
            and end_date > self.dataset.end_date
        ):
            self.add_error(
                "end_date",
                "The end date cannot be later than this dataset.",
            )

        if start_date and end_date and start_date > end_date:
            self.add_error(
                "end_date",
                "The end date must be on or after the start date.",
            )

        return cleaned_data
