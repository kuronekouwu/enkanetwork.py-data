import asyncio
import logging
import os
import json

from dotenv import load_dotenv

from utils import (
    request,
    download_json,
    load_commit_local,
    save_commit_local,
    save_data
)

# Load .env file
load_dotenv()

# API GitHub
GITHUB = "https://api.github.com/{PATH}"
RAW_GITHUB = "https://raw.githubusercontent.com/{PATH}"

# Logging
logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

# GITHUB 
USERNAME = os.getenv('GITHUB_USERNAME')
REPOSITORY = os.getenv('GITHUB_REPOSITORY')

# ENV
ENVKEY = [
    "AVATAR",
    "SKILLDEPOT",
    "SKILLS",
    "TALENTS",
    "ARTIFACTS",
    "WEAPONS",
    "FIGHT_PROPS",
    "NAMECARDS"
]

LANGS = {}
DATA = {}

SKILLS_DEPOT = {}
SKILLS_DATA = {}
CONSTELLATIONS = {}
ARTIFACTS = {}
WEAPONS = {}
FIGHT_PROPS = {}
NAMECARDS = {}

async def create_lang(data: dict, filename: str = "", has_key_name_hash: bool = True):
    DATA = {}
    for key in data:
        hash_map = str(data[key]["nameTextMapHash"])
        hashKey = key if not has_key_name_hash else hash_map
        
        for lang in LANGS:
            if hash_map in LANGS[lang]:
                if hashKey not in DATA:
                    DATA[hashKey] = {}
                DATA[hashKey][lang] = LANGS[lang][hash_map]
            else:
                if hash_map not in DATA:
                    DATA[hashKey] = {}
                DATA[hashKey][lang] = ""

    with open(os.path.join("exports", "langs", filename), "w", encoding="utf-8") as f:
        f.write(json.dumps(DATA, ensure_ascii=False, indent=4))

async def main():
    LOGGER.debug(f"Fetching commits from GitHub [{USERNAME}/{REPOSITORY}]")
    response = await request(GITHUB.format(PATH=f"repos/{USERNAME}/{REPOSITORY}/commits"))
    
    # Check SHA of last commit
    LOGGER.debug(f"Checking last commit on GitHub...")
    if len(response) > 0:
        last_commit = response[0]["sha"]
        LOGGER.debug(f"Last commit on GitHub: {last_commit}")
    else:
        LOGGER.debug("No commits found on GitHub...")
        last_commit = ""

    LOGGER.debug(f"Checking last commit on local...")
    last_commit_local = await load_commit_local()
    if last_commit_local == last_commit:
        LOGGER.debug(f"Not updated... exiting...")
        return

    LOGGER.debug(f"New commit found on GitHub")

    for key in ENVKEY:
        filename = os.getenv(key)
        if not filename:
            LOGGER.error(f"{key} not found in .env")
            continue

        await download_json(
            url=RAW_GITHUB.format(PATH=f"{USERNAME}/{REPOSITORY}/master/{os.getenv('FOLDER')}/{filename}"), 
            filename=filename, 
            path=os.path.join("raw", "data")
        )

    await asyncio.sleep(1)

    langPath = await request(GITHUB.format(PATH=f"repos/{USERNAME}/{REPOSITORY}/contents/{os.getenv('LANG_FOLDER')}"))
    for lang in langPath:
        await download_json(
            url=lang["download_url"],
            filename=lang["name"],
            path=os.path.join("raw", "langs")
        )

    # Load langs 
    for lang in os.listdir(os.path.join("raw", "langs")):
        with open(os.path.join("raw", "langs", lang), "r", encoding="utf-8") as f:
            _lang = lang.split(".")[0].replace("TextMap", "")
            LOGGER.debug(f"Loading {_lang}...")
            LANGS[_lang] = json.loads(f.read())

    # Load data 
    for data in os.listdir(os.path.join("raw", "data")):
        with open(os.path.join("raw", "data", data), "r", encoding="utf-8") as f:
            LOGGER.debug(f"Loading {data}...")
            DATA[data.split(".")[0]] = json.loads(f.read())

    # Load skills data
    for skillData in DATA["AvatarSkillExcelConfigData"]:
        LOGGER.debug(f"Getting skill data {skillData['id']}...")
        if skillData["skillIcon"] == "":
            LOGGER.debug(f"Skill {skillData['id']} has no icon... Skipping...")
            continue

        SKILLS_DATA[skillData["id"]] = {
            "nameTextMapHash": skillData["nameTextMapHash"],
            "skillIcon": skillData["skillIcon"],
            "costElemType": skillData.get("costElemType", ""),
        }

    await save_data(SKILLS_DATA, "skills.json", ["costElemType"])
    await create_lang(SKILLS_DATA, "skills.json")

    # Load constellations
    for talent in DATA["AvatarTalentExcelConfigData"]:
        LOGGER.debug(f"Getting constellations {talent['talentId']}...")

        CONSTELLATIONS[talent["talentId"]] = {
            "nameTextMapHash": talent["nameTextMapHash"],
            "icon": talent["icon"]
        }

    await save_data(CONSTELLATIONS, "constellations.json")
    await create_lang(CONSTELLATIONS, "constellations.json")

    # Load artifacts
    for artifact in DATA["ReliquaryExcelConfigData"]:
        LOGGER.debug(f"Getting artifact {artifact['id']}...")

        ARTIFACTS[artifact["id"]] = {
            "nameTextMapHash": artifact["nameTextMapHash"],
            "itemType": artifact["itemType"],
            "equipType": artifact["equipType"],
            "icon": artifact["icon"],
            "rankLevel": artifact["rankLevel"],
            "mainPropDepotId": artifact["mainPropDepotId"],
            "appendPropDepotId": artifact["appendPropDepotId"],
        }

    await save_data(ARTIFACTS, "artifacts.json")
    await create_lang(ARTIFACTS, "artifacts.json")

    # Load weapons
    for weapon in DATA["WeaponExcelConfigData"]:
        LOGGER.debug(f"Getting weapon {weapon['id']}...")

        WEAPONS[weapon["id"]] = {
            "nameTextMapHash": weapon["nameTextMapHash"],
            "icon": weapon["icon"],
            "awakenIcon": weapon["awakenIcon"],
            "rankLevel": weapon["rankLevel"]
        }
            
    await save_data(WEAPONS, "weapons.json")
    await create_lang(WEAPONS, "weapons.json")
    
    # Load namecard
    for namecard in filter(lambda a: "materialType" in a and a["materialType"] == "MATERIAL_NAMECARD", DATA["MaterialExcelConfigData"]):
        LOGGER.debug(f"Getting namecard {namecard['id']}...")

        NAMECARDS[namecard["id"]] = {
            "nameTextMapHash": namecard["nameTextMapHash"],
            "icon": namecard["icon"],
            "picPath": namecard["picPath"],
            "rankLevel": namecard["rankLevel"],
            "materialType": namecard["materialType"],
        }
    
    await save_data(NAMECARDS, "namecards.json")
    await create_lang(NAMECARDS, "namecards.json")


    # Load fight props
    for fight_prop in filter(lambda a: a['textMapId'].startswith("FIGHT_PROP"), DATA["ManualTextMapConfigData"]):
        LOGGER.debug(f"Getting FIGHT_PROP {fight_prop['textMapId']}...")
        FIGHT_PROPS[fight_prop["textMapId"]] = {
            "nameTextMapHash": fight_prop["textMapContentTextMapHash"],
        }
        
    await create_lang(FIGHT_PROPS, "fight_prop.json", False)

    # Prepare data (Create language)
    for skillDepot in DATA["AvatarSkillDepotExcelConfigData"]:
        LOGGER.debug(f"Getting skill depot: {skillDepot['id']}...")
        SKILLS_DEPOT[skillDepot["id"]] = skillDepot

    # Link data (Avatar)
    OUTPUT = {}
    for avatar in DATA["AvatarExcelConfigData"]:
        AVATAR = {}
        LOGGER.debug(f"Processing {avatar['id']}...")
        if avatar["skillDepotId"] == 101 or avatar["iconName"].endswith("_Kate"):
            LOGGER.debug(f"Skipping {avatar['id']}...")
            continue

        AVATAR.update({
            "nameTextMapHash": avatar["nameTextMapHash"],
            "iconName": avatar["iconName"],
            "sideIconName": avatar["sideIconName"],
            "qualityType": avatar["qualityType"],
            "costElemType": "",
            "skills": [],
        })
        
        LOGGER.debug(f"Getting skills {avatar['skillDepotId']}")
        depot = SKILLS_DEPOT.get(avatar["skillDepotId"])
        if depot and depot["id"] != 101:
            energry = SKILLS_DATA.get(depot.get("energySkill"))

            if energry:
                LOGGER.debug(f"Getting skills element {depot.get('energySkill')}")
                AVATAR.update({
                    "costElemType": energry["costElemType"]
                })

            for skill in depot["skills"]:
                if skill <= 0:
                    continue
            
                AVATAR["skills"].append(skill)

            AVATAR.update({
                "talents": depot["talents"]
            })
        
        OUTPUT[avatar["id"]] = AVATAR

    await create_lang(OUTPUT, "characters.json")    
    await save_data(OUTPUT, "characters.json")

    # Save lastest commit
    LOGGER.debug(f"Saving lastest commit...")
    await save_commit_local(last_commit)

    LOGGER.debug(f"Done!")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())