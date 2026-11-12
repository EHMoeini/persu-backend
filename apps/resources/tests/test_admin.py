from django.contrib import admin
from django.test import SimpleTestCase

from apps.resources.models import Facility


class FacilityAdminTests(SimpleTestCase):
    def test_facility_is_registered_in_admin(self):
        self.assertTrue(admin.site.is_registered(Facility))
