from pathlib import Path

from django import forms
from .models import SalesLine, SalesOrder


MAX_UPLOAD_SIZE = 10 * 1024 * 1024

CURRENCY_CHOICES = (
    ("AED", "AED — UAE Dirham"),
    ("AFN", "AFN — Afghan Afghani"),
    ("ALL", "ALL — Albanian Lek"),
    ("AMD", "AMD — Armenian Dram"),
    ("ANG", "ANG — Caribbean Guilder"),
    ("AOA", "AOA — Angolan Kwanza"),
    ("ARS", "ARS — Argentine Peso"),
    ("AUD", "AUD — Australian Dollar"),
    ("AWG", "AWG — Aruban Florin"),
    ("AZN", "AZN — Azerbaijani Manat"),
    ("BAM", "BAM — Bosnia-Herzegovina Convertible Mark"),
    ("BBD", "BBD — Barbadian Dollar"),
    ("BDT", "BDT — Bangladeshi Taka"),
    ("BGN", "BGN — Bulgarian Lev"),
    ("BHD", "BHD — Bahraini Dinar"),
    ("BIF", "BIF — Burundian Franc"),
    ("BMD", "BMD — Bermudian Dollar"),
    ("BND", "BND — Brunei Dollar"),
    ("BOB", "BOB — Bolivian Boliviano"),
    ("BRL", "BRL — Brazilian Real"),
    ("BSD", "BSD — Bahamian Dollar"),
    ("BTN", "BTN — Bhutanese Ngultrum"),
    ("BWP", "BWP — Botswana Pula"),
    ("BYN", "BYN — Belarusian Ruble"),
    ("BZD", "BZD — Belize Dollar"),
    ("CAD", "CAD — Canadian Dollar"),
    ("CDF", "CDF — Congolese Franc"),
    ("CHF", "CHF — Swiss Franc"),
    ("CLP", "CLP — Chilean Peso"),
    ("CNY", "CNY — Chinese Yuan"),
    ("COP", "COP — Colombian Peso"),
    ("CRC", "CRC — Costa Rican Colón"),
    ("CUP", "CUP — Cuban Peso"),
    ("CVE", "CVE — Cape Verdean Escudo"),
    ("CZK", "CZK — Czech Koruna"),
    ("DJF", "DJF — Djiboutian Franc"),
    ("DKK", "DKK — Danish Krone"),
    ("DOP", "DOP — Dominican Peso"),
    ("DZD", "DZD — Algerian Dinar"),
    ("EGP", "EGP — Egyptian Pound"),
    ("ERN", "ERN — Eritrean Nakfa"),
    ("ETB", "ETB — Ethiopian Birr"),
    ("EUR", "EUR — Euro"),
    ("FJD", "FJD — Fijian Dollar"),
    ("FKP", "FKP — Falkland Islands Pound"),
    ("GBP", "GBP — British Pound"),
    ("GEL", "GEL — Georgian Lari"),
    ("GHS", "GHS — Ghanaian Cedi"),
    ("GIP", "GIP — Gibraltar Pound"),
    ("GMD", "GMD — Gambian Dalasi"),
    ("GNF", "GNF — Guinean Franc"),
    ("GTQ", "GTQ — Guatemalan Quetzal"),
    ("GYD", "GYD — Guyanese Dollar"),
    ("HKD", "HKD — Hong Kong Dollar"),
    ("HNL", "HNL — Honduran Lempira"),
    ("HTG", "HTG — Haitian Gourde"),
    ("HUF", "HUF — Hungarian Forint"),
    ("IDR", "IDR — Indonesian Rupiah"),
    ("ILS", "ILS — Israeli New Shekel"),
    ("INR", "INR — Indian Rupee"),
    ("IQD", "IQD — Iraqi Dinar"),
    ("IRR", "IRR — Iranian Rial"),
    ("ISK", "ISK — Icelandic Króna"),
    ("JMD", "JMD — Jamaican Dollar"),
    ("JOD", "JOD — Jordanian Dinar"),
    ("JPY", "JPY — Japanese Yen"),
    ("KES", "KES — Kenyan Shilling"),
    ("KGS", "KGS — Kyrgyzstani Som"),
    ("KHR", "KHR — Cambodian Riel"),
    ("KMF", "KMF — Comorian Franc"),
    ("KRW", "KRW — South Korean Won"),
    ("KWD", "KWD — Kuwaiti Dinar"),
    ("KYD", "KYD — Cayman Islands Dollar"),
    ("KZT", "KZT — Kazakhstani Tenge"),
    ("LAK", "LAK — Lao Kip"),
    ("LBP", "LBP — Lebanese Pound"),
    ("LKR", "LKR — Sri Lankan Rupee"),
    ("LRD", "LRD — Liberian Dollar"),
    ("LSL", "LSL — Lesotho Loti"),
    ("LYD", "LYD — Libyan Dinar"),
    ("MAD", "MAD — Moroccan Dirham"),
    ("MDL", "MDL — Moldovan Leu"),
    ("MGA", "MGA — Malagasy Ariary"),
    ("MKD", "MKD — Macedonian Denar"),
    ("MMK", "MMK — Myanmar Kyat"),
    ("MNT", "MNT — Mongolian Tögrög"),
    ("MOP", "MOP — Macanese Pataca"),
    ("MRU", "MRU — Mauritanian Ouguiya"),
    ("MUR", "MUR — Mauritian Rupee"),
    ("MVR", "MVR — Maldivian Rufiyaa"),
    ("MWK", "MWK — Malawian Kwacha"),
    ("MXN", "MXN — Mexican Peso"),
    ("MYR", "MYR — Malaysian Ringgit"),
    ("MZN", "MZN — Mozambican Metical"),
    ("NAD", "NAD — Namibian Dollar"),
    ("NGN", "NGN — Nigerian Naira"),
    ("NIO", "NIO — Nicaraguan Córdoba"),
    ("NOK", "NOK — Norwegian Krone"),
    ("NPR", "NPR — Nepalese Rupee"),
    ("NZD", "NZD — New Zealand Dollar"),
    ("OMR", "OMR — Omani Rial"),
    ("PAB", "PAB — Panamanian Balboa"),
    ("PEN", "PEN — Peruvian Sol"),
    ("PGK", "PGK — Papua New Guinean Kina"),
    ("PHP", "PHP — Philippine Peso"),
    ("PKR", "PKR — Pakistani Rupee"),
    ("PLN", "PLN — Polish Złoty"),
    ("PYG", "PYG — Paraguayan Guaraní"),
    ("QAR", "QAR — Qatari Riyal"),
    ("RON", "RON — Romanian Leu"),
    ("RSD", "RSD — Serbian Dinar"),
    ("RUB", "RUB — Russian Ruble"),
    ("RWF", "RWF — Rwandan Franc"),
    ("SAR", "SAR — Saudi Riyal"),
    ("SBD", "SBD — Solomon Islands Dollar"),
    ("SCR", "SCR — Seychellois Rupee"),
    ("SDG", "SDG — Sudanese Pound"),
    ("SEK", "SEK — Swedish Krona"),
    ("SGD", "SGD — Singapore Dollar"),
    ("SHP", "SHP — Saint Helena Pound"),
    ("SLE", "SLE — Sierra Leonean Leone"),
    ("SOS", "SOS — Somali Shilling"),
    ("SRD", "SRD — Surinamese Dollar"),
    ("SSP", "SSP — South Sudanese Pound"),
    ("STN", "STN — São Tomé and Príncipe Dobra"),
    ("SYP", "SYP — Syrian Pound"),
    ("SZL", "SZL — Eswatini Lilangeni"),
    ("THB", "THB — Thai Baht"),
    ("TJS", "TJS — Tajikistani Somoni"),
    ("TMT", "TMT — Turkmenistani Manat"),
    ("TND", "TND — Tunisian Dinar"),
    ("TOP", "TOP — Tongan Paʻanga"),
    ("TRY", "TRY — Turkish Lira"),
    ("TTD", "TTD — Trinidad and Tobago Dollar"),
    ("TWD", "TWD — New Taiwan Dollar"),
    ("TZS", "TZS — Tanzanian Shilling"),
    ("UAH", "UAH — Ukrainian Hryvnia"),
    ("UGX", "UGX — Ugandan Shilling"),
    ("USD", "USD — US Dollar"),
    ("UYU", "UYU — Uruguayan Peso"),
    ("UZS", "UZS — Uzbekistani Som"),
    ("VES", "VES — Venezuelan Bolívar"),
    ("VND", "VND — Vietnamese Đồng"),
    ("VUV", "VUV — Vanuatu Vatu"),
    ("WST", "WST — Samoan Tālā"),
    ("XAF", "XAF — Central African CFA Franc"),
    ("XCD", "XCD — East Caribbean Dollar"),
    ("XOF", "XOF — West African CFA Franc"),
    ("XPF", "XPF — CFP Franc"),
    ("YER", "YER — Yemeni Rial"),
    ("ZAR", "ZAR — South African Rand"),
    ("ZMW", "ZMW — Zambian Kwacha"),
)


class CurrencyChoiceField(forms.ChoiceField):
    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip().upper()
        return value

    def validate(self, value):
        forms.Field.validate(self, value)

        if value and not self.valid_value(value):
            raise forms.ValidationError(
                "Enter a valid three-letter currency code using A–Z."
            )


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

    currency = CurrencyChoiceField(
        label="Currency",
        choices=(("", "Select a currency"), *CURRENCY_CHOICES),
        help_text="Choose the currency used for every monetary value in this dataset.",
        widget=forms.Select(attrs={"class": "form-select"}),
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
