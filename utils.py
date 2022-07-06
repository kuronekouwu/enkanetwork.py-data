import os
import json
import logging
import aiohttp
import copy

# DOWNLOAD CHUNK SIZE
CHUNK_SIZE = 5 * 2**20

LOGGER = logging.getLogger(__name__)

async def request(url: str, method: str = "GET", headers: dict = None, body: str = None) -> dict:
    if headers is None:
        headers = {}
    if body is None:
        body = ""

    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers, data=body) as response:
            """
                From https://gist.github.com/foobarna/19c132304e140bf5031c273f6dc27ece
            """
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

            return json.loads(data)


async def download_json(url: str, filename: str, path: str = ".") -> None:
    LOGGER.debug(f"Fetching {filename} from GitHub...")
    response = await request(url)
    with open(os.path.join(path, filename), "w", encoding="utf-8") as f:
        f.write(json.dumps(response, ensure_ascii=False))
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
