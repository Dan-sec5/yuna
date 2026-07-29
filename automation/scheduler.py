from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Callable, Dict, Any
import logging

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.jobs: Dict[str, Any] = {}
    
    def start(self):
        self.scheduler.start()
        logger.info("Scheduler iniciado")
    
    def stop(self):
        self.scheduler.shutdown()
        logger.info("Scheduler detenido")
    
    def add_cron_job(self, job_id: str, func: Callable, cron_expr: str, **kwargs):
        """Añade trabajo con expresión cron (ej: '0 9 * * 1' = lunes 9am)"""
        trigger = CronTrigger.from_crontab(cron_expr)
        job = self.scheduler.add_job(func, trigger, id=job_id, **kwargs)
        self.jobs[job_id] = job
        logger.info(f"Job cron añadido: {job_id} ({cron_expr})")
    
    def add_interval_job(self, job_id: str, func: Callable, minutes: int, **kwargs):
        """Añade trabajo cada N minutos"""
        from apscheduler.triggers.interval import IntervalTrigger
        trigger = IntervalTrigger(minutes=minutes)
        job = self.scheduler.add_job(func, trigger, id=job_id, **kwargs)
        self.jobs[job_id] = job
        logger.info(f"Job intervalo añadido: {job_id} (cada {minutes} min)")
    
    def remove_job(self, job_id: str):
        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]
            logger.info(f"Job removido: {job_id}")
    
    def list_jobs(self) -> Dict:
        return {jid: str(job.next_run_time) for jid, job in self.jobs.items()}
