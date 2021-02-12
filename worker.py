import os

import redis
from rq import Worker, Queue, Connection

listen = ['high', 'default', 'low']
if 'REDISTOGO_URL' in os.environ:
    redis_url = os.environ['REDISTOGO_URL']
    #, 'redis://localhost:6379')

conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
