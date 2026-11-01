import os

from dotenv import load_dotenv
from redis import Redis
from rq import Worker

load_dotenv()
conn = Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))

if __name__ == "__main__":
    Worker(["default"], connection=conn).work()