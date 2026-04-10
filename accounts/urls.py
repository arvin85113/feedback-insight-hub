from django.urls import path

from .views import CustomerSignUpView, PlatformLoginView, PlatformLogoutView

app_name = "accounts"

urlpatterns = [
    path("login/", PlatformLoginView.as_view(), name="login"),
    path("logout/", PlatformLogoutView.as_view(), name="logout"),
    path("signup/", CustomerSignUpView.as_view(), name="signup"),
]
