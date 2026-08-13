from threading import Lock
from app.models import JobStatus

class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, JobStatus] = {}
        self._lock = Lock()

    def create(self, file_id: str, filename: str = "") -> None:
        with self._lock:
            self._jobs[file_id] = JobStatus(file_id=file_id, status="uploaded",
                                            progress=0, message="Uploaded", filename=filename)

    def update(self, file_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs[file_id]
            self._jobs[file_id] = job.model_copy(update=fields)

    def get(self, file_id: str) -> JobStatus | None:
        with self._lock:
            return self._jobs.get(file_id)
