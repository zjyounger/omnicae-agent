"""Non-blocking, evidence-preserving CalculiX process runner."""

import hashlib
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


OUTPUT_SUFFIXES = (
    ".frd",
    ".dat",
    ".sta",
    ".cvg",
    ".12d",
    ".eig",
    ".out",
    ".omnicae.log",
)


def _now():
    return datetime.now(timezone.utc).isoformat()


class CalculiXRunner:
    def __init__(self, solver_path):
        self.solver_path = str(solver_path)
        self.jobs = {}

    def start(self, deck_path):
        deck_path = Path(deck_path)
        job_id = str(uuid.uuid4())
        log_path = deck_path.with_suffix(".omnicae.log")
        output_baseline = self._snapshot_outputs(deck_path.parent, deck_path.stem)
        log_stream = open(log_path, "wb")
        process = subprocess.Popen(
            [self.solver_path, deck_path.stem],
            cwd=str(deck_path.parent),
            stdin=subprocess.DEVNULL,
            stdout=log_stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        job = {
            "job_id": job_id,
            "deck_path": str(deck_path),
            "working_directory": str(deck_path.parent),
            "job_name": deck_path.stem,
            "command": [self.solver_path, deck_path.stem],
            "pid": process.pid,
            "started_at": _now(),
            "finished_at": None,
            "return_code": None,
            "state": "running",
            "log_path": str(log_path),
            "_process": process,
            "_log_stream": log_stream,
            "_output_baseline": output_baseline,
        }
        self.jobs[job_id] = job
        return self.describe(job_id)

    def describe(self, job_id):
        job = self.jobs[job_id]
        self._poll(job)
        result = {key: value for key, value in job.items() if not key.startswith("_")}
        result["outputs"] = self._outputs(job)
        result["solver_errors"] = self._error_lines(job["log_path"])
        return result

    def list(self):
        return [self.describe(job_id) for job_id in sorted(self.jobs)]

    def cancel(self, job_id):
        job = self.jobs[job_id]
        self._poll(job)
        if job["state"] == "running":
            job["_process"].terminate()
            try:
                job["_process"].wait(timeout=10)
            except subprocess.TimeoutExpired:
                return {"job": self.describe(job_id), "terminated": False, "warning": "process did not exit within 10 s"}
            self._poll(job)
            job["state"] = "cancelled"
        return {"job": self.describe(job_id), "terminated": job["state"] != "running"}

    def close(self):
        for job in self.jobs.values():
            stream = job.get("_log_stream")
            if stream and not stream.closed:
                stream.close()

    def _poll(self, job):
        if job["state"] != "running":
            return
        return_code = job["_process"].poll()
        if return_code is None:
            return
        job["return_code"] = int(return_code)
        job["finished_at"] = _now()
        job["state"] = "succeeded" if return_code == 0 else "failed"
        stream = job["_log_stream"]
        if not stream.closed:
            stream.close()

    @classmethod
    def _outputs(cls, job):
        directory = Path(job["working_directory"])
        stem = job["job_name"]
        result = []
        baseline = job.get("_output_baseline", {})
        for suffix in OUTPUT_SUFFIXES:
            path = directory / (stem + suffix)
            if not path.is_file():
                continue
            record = cls._file_record(path)
            previous = baseline.get(str(path))
            if previous is not None and record["signature"] == previous["signature"]:
                continue
            result.append(
                {
                    "path": str(path),
                    "bytes": record["bytes"],
                    "sha256": record["sha256"],
                }
            )
        return result

    @classmethod
    def _snapshot_outputs(cls, directory, stem):
        result = {}
        directory = Path(directory)
        for suffix in OUTPUT_SUFFIXES:
            path = directory / (stem + suffix)
            if path.is_file():
                result[str(path)] = cls._file_record(path)
        return result

    @staticmethod
    def _file_record(path):
        stat = path.stat()
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        value = digest.hexdigest()
        return {
            "bytes": stat.st_size,
            "sha256": value,
            "signature": (stat.st_mtime_ns, stat.st_size, value),
        }

    @staticmethod
    def _error_lines(log_path):
        path = Path(log_path)
        if not path.is_file():
            return []
        lines = path.read_text(errors="replace").splitlines()
        needles = ("*ERROR", "ERROR", "FATAL", "nonpositive jacobian")
        return [line.strip() for line in lines if any(needle.lower() in line.lower() for needle in needles)][-50:]
