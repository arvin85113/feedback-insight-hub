from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import CustomerSignUpForm, LoginForm


class PlatformLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "accounts/login.html"

    def get_success_url(self):
        if self.request.user.is_manager:
            return reverse_lazy("feedback:dashboard")
        return reverse_lazy("feedback:home")


class PlatformLogoutView(LogoutView):
    pass


class CustomerSignUpView(CreateView):
    form_class = CustomerSignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        messages.success(self.request, "帳號建立完成，請登入後填寫正式問卷。")
        return super().form_valid(form)
