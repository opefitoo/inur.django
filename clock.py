from apscheduler.schedulers.blocking import BlockingScheduler
import os

scheduler = BlockingScheduler()


@scheduler.scheduled_job('interval', minutes=1)
def timed_job():
    os.system('python manage.py check_events')


scheduler.start()
