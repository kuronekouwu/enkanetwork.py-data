import os
import json
import logging
import aiohttp
import copy
import asyncio

from git import Repo

# DOWNLOAD CHUNK SIZE
CHUNK_SIZE = 5 * 2**20
RETRY_MAX = 10

LOGGER = logging.getLogger(__name__)

# HEADER 
HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.66 Safari/537.36 Edg/103.0.1264.44"
}

async def request(url: str, method: str = "GET", headers: dict = None, body: str = None) -> dict:
    _url = url.strip(" ")
    if headers is None:
        headers = {}
    if body is None:
        body = ""

    retry = 0
    async with aiohttp.ClientSession() as session:
        async with session.request(method, _url, headers={**HEADER, **headers}, data=body) as response:
            """
                From https://gist.github.com/foobarna/19c132304e140bf5031c273f6dc27ece
            """

            while True:
                if response.status >= 400:
                    LOGGER.warning(f"Failure to fetch {_url} ({response.status}) Retry {retry} / {RETRY_MAX}")
                    retry += 1
                    if retry > RETRY_MAX:
                        raise Exception(f"Failed to download {url}")

                    await asyncio.sleep(3)
                    continue
                
                break                

            data = bytearray()
            data_to_read = True
            while data_to_read:
                red = 0
                while red < CHUNK_SIZE:
                    chunk = await response.content.read(CHUNK_SIZE - red)
                   
                    if not chunk:
                        data_to_read = False
                        break

                    data.extend(chunk)
                    red += len(chunk)

            try:
                return json.loads(data)
            except Exception as e:
                print(response.status)
                print(url)
                print(data)
                raise e


async def download_json(url: str, filename: str, path: str = ".") -> None:
    LOGGER.debug(f"Fetching {filename} from GitHub...")
    response = await request(url)
    with open(os.path.join(path, filename), "w", encoding="utf-8") as f:
        f.write(json.dumps(response, ensure_ascii=False, indent=4))
    LOGGER.debug(f"{filename} saved")

async def load_commit_local():
    if os.path.exists("last_commit.txt"):
        with open("last_commit.txt", "r") as f:
            last_commit_local = f.read()
    else:
        last_commit_local = ""
    return last_commit_local

async def save_commit_local(commit_id: str):
    with open("last_commit.txt", "w") as f:
        f.write(commit_id)

async def save_data(data: dict, filename: str, delete_key: list = []) -> None:
    _data = copy.deepcopy(data)
    for key in _data:
        for _del in delete_key:
            del _data[key][_del]
            
    with open(os.path.join("exports", "data", filename), "w", encoding="utf-8") as f:
        f.write(json.dumps(_data, ensure_ascii=False, indent=4))
    LOGGER.debug(f"{filename} saved")

async def push_to_github(commit: str = "") -> None:
    repo = Repo("./")
    repo.git.add(["./exports/**/*.json"])
    repo.index.commit(commit)
    origin = repo.remote(name='origin')
    origin.push()

    LOGGER.info("Pushed to GitHub")