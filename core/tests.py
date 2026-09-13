from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_page_loads_successfully(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome to Vendilume")
        self.assertContains(response, "See the signal inside your")
        self.assertContains(response, "Animated three-dimensional sales chart")
        self.assertContains(response, "vendilume-mark.svg")
        self.assertNotContains(response, "Analytics ready")
