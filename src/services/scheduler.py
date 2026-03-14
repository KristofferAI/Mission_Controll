from src.db import add_job, complete_job, list_jobs


class JobScheduler:
    """Lightweight job scheduler — assign tasks to bots and track completion."""

    def schedule(self, bot_id: int, title: str, description: str = ""):
        add_job(bot_id, title, description)

    def complete(self, job_id: int):
        complete_job(job_id)

    def all_jobs(self):
        return list_jobs()
