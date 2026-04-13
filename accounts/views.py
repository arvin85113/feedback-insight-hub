from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import CustomerPreferenceForm, CustomerSignUpForm, LoginForm


class PlatformLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "accounts/login.html"

    def get_success_url(self):
        if self.request.user.is_manager:
            return reverse_lazy("feedback:dashboard")
        return reverse_lazy("feedback:customer-home")


class PlatformLogoutView(LogoutView):
    pass


class CustomerSignUpView(CreateView):
    form_class = CustomerSignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        messages.success(self.request, "註冊完成，現在可以登入查看你的問卷紀錄與通知設定。")
        return super().form_valid(form)


@login_required
def customer_preferences_view(request):
    if request.user.is_manager:
        return redirect("feedback:dashboard")

    if request.method == "POST":
        form = CustomerPreferenceForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "個人資料與通知偏好已更新。")
            return redirect("accounts:preferences")
    else:
        form = CustomerPreferenceForm(instance=request.user)

    return render(request, "accounts/preferences.html", {"form": form})
