from pathlib import Path

from django import forms


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
