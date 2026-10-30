from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView


class ProtectedView(APIView):
    def get(self, request):
        return Response(
            {
                "user_id": str(request.user.pk),
                "jti": request.auth.jti,
                "typ": request.auth.payload["typ"],
            }
        )


urlpatterns = [
    path("protected", ProtectedView.as_view(), name="protected"),
]
