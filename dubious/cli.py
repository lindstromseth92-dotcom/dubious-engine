import json
import sys

from dotenv import load_dotenv

from .pipeline import run

load_dotenv()
print(json.dumps(run(" ".join(sys.argv[1:])), indent=2))