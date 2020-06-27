from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler()

@sched.scheduled_job('interval', minutes=5)
def timed_job():
    os.system('python manage.py check_events')


sched.start()
