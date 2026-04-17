import os

import requests

from . import local_service


class FeedbackServiceClient:
    def __init__(self):
        self.base_url = os.getenv("FEEDBACK_SERVICE_URL", "").rstrip("/")
        self.timeout = float(os.getenv("FEEDBACK_SERVICE_TIMEOUT", "5"))

    def _get(self, path, *, params=None):
        response = requests.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _post(self, path, payload):
        response = requests.post(f"{self.base_url}{path}", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_home(self):
        if self.base_url:
            try:
                return self._get("/api/home")
            except requests.RequestException:
                pass
        return local_service.get_home_payload()

    def get_customer_home(self, user):
        if self.base_url:
            try:
                return self._get(f"/api/customers/{user.id}/home")
            except requests.RequestException:
                pass
        return local_service.get_customer_home_payload(user)

    def get_customer_notifications(self, user):
        if self.base_url:
            try:
                return self._get(f"/api/customers/{user.id}/notifications")
            except requests.RequestException:
                pass
        return local_service.get_customer_notifications_payload(user)

    def get_dashboard(self):
        if self.base_url:
            try:
                return self._get("/api/dashboard")
            except requests.RequestException:
                pass
        return local_service.get_dashboard_payload()

    def get_stats(self, slug):
        if self.base_url:
            try:
                return self._get("/api/stats", params={"survey": slug})
            except requests.RequestException:
                pass
        return local_service.get_stats_payload(slug)

    def get_text_analysis(self, slug):
        if self.base_url:
            try:
                return self._get("/api/text-analysis", params={"survey": slug})
            except requests.RequestException:
                pass
        return local_service.get_text_analysis_payload(slug)

    def submit_survey(self, survey, *, user, respondent_name, respondent_email, consent_follow_up, source, answers):
        if self.base_url:
            try:
                payload = {
                    "user_id": user.id if user else None,
                    "respondent_name": respondent_name,
                    "respondent_email": respondent_email,
                    "consent_follow_up": consent_follow_up,
                    "source": source,
                    "answers": answers,
                }
                return self._post(f"/api/surveys/{survey.slug}/submissions", payload)
            except requests.RequestException:
                pass
        return local_service.submit_survey_payload(
            survey,
            user=user,
            respondent_name=respondent_name,
            respondent_email=respondent_email,
            consent_follow_up=consent_follow_up,
            source=source,
            answers=answers,
        )


service_client = FeedbackServiceClient()
