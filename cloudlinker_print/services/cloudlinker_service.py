import json
import requests
import logging

_logger = logging.getLogger(__name__)

BASE_URL = "https://cloudlinker.eu/api"

JOB_TYPE_PRINT = 1
JOB_TYPE_HTTP  = 2

JOB_STATUS = {
    1: "created",
    2: "launched",
    3: "pending",
    4: "completed",
    5: "failed",
}


class CloudLinkerApiError(Exception):
    """Raised when the CloudLinker API returns an error."""
    pass


class CloudLinkerService:
    """
    Wrapper around the CloudLinker REST API (https://cloudlinker.eu/api).

    Authentication: HTTP Basic Auth
        username = organization_id
        password = api_key
    """

    def __init__(self, organization_id: str, api_key: str, base_url: str = BASE_URL):
        if not organization_id or not api_key:
            raise CloudLinkerApiError("CloudLinker organization ID and API key are required.")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (organization_id, api_key)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    # ------------------------------------------------------------------
    # Connection test
    # ------------------------------------------------------------------

    def test_connection(self) -> dict:
        """GET /test — returns {"organization_id": "..."}."""
        return self._get("test")

    # ------------------------------------------------------------------
    # Clients
    # ------------------------------------------------------------------

    def get_clients(self, hostname: str = None, pagination: int = 100) -> list:
        payload = {"pagination": pagination}
        if hostname:
            payload["hostname"] = hostname
        resp = self._post("clients/list", payload)
        return resp.get("data", [])

    def create_client(self, hostname: str, ip_address: str, description: str = "") -> dict:
        payload = {"hostname": hostname, "ip_address": ip_address}
        if description:
            payload["description"] = description
        resp = self._post("clients/create", payload)
        return resp.get("data", {})

    def delete_client(self, client_id: str) -> None:
        self._post("clients/delete", {"client_id": client_id})

    # ------------------------------------------------------------------
    # Devices (printers = device_type 1)
    # ------------------------------------------------------------------

    def get_devices(self, client_id: str = None, device_type: int = 1, name: str = None) -> list:
        payload = {"device_type": device_type}
        if client_id:
            payload["client_id"] = client_id
        if name:
            payload["name"] = name
        resp = self._post("devices/list", payload)
        return resp.get("data", [])

    def create_device(self, client_id: str, name: str, device_type: int = 1) -> dict:
        payload = {"client_id": client_id, "name": name, "device_type": device_type}
        resp = self._post("devices/create", payload)
        return resp.get("data", {})

    def delete_device(self, device_id: str) -> None:
        self._post("devices/delete", {"device_id": device_id})

    # ------------------------------------------------------------------
    # Jobs — print
    # ------------------------------------------------------------------

    def create_print_job(
        self,
        client_id: str,
        device_id: str,
        document_url: str,
        copies: int = 1,
        launch_immediately: bool = True,
    ) -> dict:
        """
        POST /jobs/create with job_type=1 (PRINT_DOCUMENT).

        CloudLinker client fetches document_url directly —
        internal network URLs work fine.
        """
        payload_inner = {
            "document_type": "pdf",
            "document_url": document_url,
            "copies": str(copies),
        }
        body = {
            "client_id": client_id,
            "device_id": device_id,
            "job_type": JOB_TYPE_PRINT,
            "payload": json.dumps(payload_inner),
            "launch_immediately": launch_immediately,
        }
        resp = self._post("jobs/create", body)
        return resp.get("data", {})

    def get_job(self, job_id: str) -> dict:
        resp = self._post("jobs/get", {"job_id": job_id})
        return resp.get("data", {})

    def launch_job(self, job_id: str) -> None:
        self._post("jobs/launch", {"job_id": job_id})

    def delete_job(self, job_id: str) -> None:
        self._post("jobs/delete", {"job_id": job_id})

    def get_jobs(self, client_id: str = None, device_id: str = None,
                 job_type: int = None, status: int = None) -> list:
        payload = {}
        if client_id:
            payload["client_id"] = client_id
        if device_id:
            payload["device_id"] = device_id
        if job_type is not None:
            payload["job_type"] = job_type
        if status is not None:
            payload["status"] = status
        resp = self._post("jobs/list", payload)
        return resp.get("data", [])

    # ------------------------------------------------------------------
    # Static helpers (no auth required)
    # ------------------------------------------------------------------

    @staticmethod
    def login(base_url, email, password):
        """POST /auth/login — returns {organization_id, api_key, organization_name, plan}"""
        url = f"{base_url.rstrip('/')}/auth/login"
        try:
            resp = requests.post(url, json={"email": email, "password": password}, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            body = exc.response.json() if exc.response.content else {}
            msg = body.get("message", exc.response.text)
            raise CloudLinkerApiError(f"Login failed: {msg}") from exc
        except requests.RequestException as exc:
            raise CloudLinkerApiError(f"Connection error: {exc}") from exc

    @staticmethod
    def get_plans(base_url):
        """GET /plans — returns list of active plans"""
        url = f"{base_url.rstrip('/')}/plans"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json().get("data", [])
        except requests.HTTPError as exc:
            raise CloudLinkerApiError(f"Failed to fetch plans: {exc.response.text}") from exc
        except requests.RequestException as exc:
            raise CloudLinkerApiError(f"Connection error: {exc}") from exc

    @staticmethod
    def register(base_url, email, password, firstname, lastname, company, plan_id):
        """POST /auth/register — returns {organization_id, api_key, ...}"""
        url = f"{base_url.rstrip('/')}/auth/register"
        payload = {
            "email": email,
            "password": password,
            "firstname": firstname,
            "lastname": lastname,
            "company": company or "",
            "plan_id": plan_id,
            "referrer": "odoo",
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            body = exc.response.json() if exc.response.content else {}
            msg = body.get("message", "") or str(body.get("messages", exc.response.text))
            raise CloudLinkerApiError(f"Registration failed: {msg}") from exc
        except requests.RequestException as exc:
            raise CloudLinkerApiError(f"Connection error: {exc}") from exc

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}/{path}"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            raise CloudLinkerApiError(
                f"CloudLinker [{exc.response.status_code}]: {exc.response.text}"
            ) from exc
        except requests.RequestException as exc:
            raise CloudLinkerApiError(f"CloudLinker connection error: {exc}") from exc

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}/{path}"
        try:
            resp = self.session.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.HTTPError as exc:
            raise CloudLinkerApiError(
                f"CloudLinker [{exc.response.status_code}]: {exc.response.text}"
            ) from exc
        except requests.RequestException as exc:
            raise CloudLinkerApiError(f"CloudLinker connection error: {exc}") from exc
