import os
from src.story_pack import make_pack
if __name__ == "__main__": make_pack(os.environ["JOB_ID"], os.environ["TOPIC_TITLE"])
