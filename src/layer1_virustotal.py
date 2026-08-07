"""
Layer 1 — File Reputation via VirusTotal.

Hashes/uploads a document, queries VirusTotal's aggregated engine results,
and returns a risk score in [0, 1] based on (malicious + suspicious) / total.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import requests

VT_BASE_URL = "https://www.virustotal.com/api/v3"


def _api_key() -> str:
    key = os.environ.get("VT_API_KEY")
    if not key:
        raise RuntimeError(
            "VT_API_KEY not set. Copy .env.example to .env and add your own "
            "VirusTotal API key (see https://www.virustotal.com/gui/my-apikey)."
        )
    return key


@dataclass
class VTResult:
    verdict: str
    risk_score: float
    malicious: int
    suspicious: int
    harmless: int
    undetected: int
    total_engines: int


def upload_file(file_path: str) -> str | None:
    """Upload a file to VirusTotal and return its analysis id."""
    url = f"{VT_BASE_URL}/files"
    headers = {"x-apikey": _api_key()}
    with open(file_path, "rb") as f:
        response = requests.post(url, headers=headers, files={"file": f})
    if response.status_code != 200:
        return None
    return response.json()["data"]["id"]


def get_analysis_result(analysis_id: str, max_attempts: int = 10, poll_seconds: int = 5) -> dict | None:
    """Poll VirusTotal until an uploaded file's analysis completes."""
    url = f"{VT_BASE_URL}/analyses/{analysis_id}"
    headers = {"x-apikey": _api_key()}
    for _ in range(max_attempts):
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()["data"]["attributes"]
            if data["status"] == "completed":
                return data
        time.sleep(poll_seconds)
    return None


def get_file_report(file_hash: str, max_attempts: int = 10, poll_seconds: int = 5) -> dict | None:
    """Fetch the existing report for a known file hash (SHA-256 or MD5)."""
    url = f"{VT_BASE_URL}/files/{file_hash}"
    headers = {"x-apikey": _api_key()}
    for _ in range(max_attempts):
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()["data"]["attributes"]
        if response.status_code == 404:
            # Hash not found in VT — treat as undetected, not an error.
            return {"last_analysis_stats": {"malicious": 0, "suspicious": 0, "harmless": 0, "undetected": 0}}
        time.sleep(poll_seconds)
    return None


def analyze_document(file_path: str | None = None, file_hash: str | None = None) -> VTResult | dict:
    """
    Score a document via VirusTotal, either by uploading a new file
    or by looking up an existing hash.
    """
    if file_path:
        analysis_id = upload_file(file_path)
        if not analysis_id:
            return {"error": "Upload failed"}
        result = get_analysis_result(analysis_id)
    elif file_hash:
        result = get_file_report(file_hash)
    else:
        return {"error": "No input provided"}

    if not result:
        return {"error": "Analysis not ready"}

    stats = result["last_analysis_stats"]
    malicious = stats.get("malicious", 0)
    suspicious = stats.get("suspicious", 0)
    harmless = stats.get("harmless", 0)
    undetected = stats.get("undetected", 0)
    total = malicious + suspicious + harmless + undetected

    risk_score = (malicious + suspicious) / total if total > 0 else 0.0

    if malicious > 0:
        verdict = "Malicious"
    elif suspicious > 0:
        verdict = "Suspicious"
    else:
        verdict = "Safe"

    return VTResult(
        verdict=verdict,
        risk_score=round(risk_score, 3),
        malicious=malicious,
        suspicious=suspicious,
        harmless=harmless,
        undetected=undetected,
        total_engines=total,
    )
