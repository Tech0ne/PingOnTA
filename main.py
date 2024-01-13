from datetime import datetime
import requests
import json
import time

import sys
import os

URL = "https://api.epitest.eu/me/2023" # Yeah, they did not update for now, bozo
PING_EVERY = 5 * 60 # time in seconds for ping. If you go too high u might end up kicked, idk

DEBUG = False

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not TOKEN or not WEBHOOK_URL:
    print("Please add the TOKEN and/or the WEBHOOK_URL to your env and retry")
    sys.exit(1)

WEBHOOK_CONTENT = """{
  "content": "@everyone",
  "username": "Marvin",
  "embeds": [
    {
      "title": "New automated test on project %NAME%",
      "description": "The project %NAME% (codename %SLUG%:%MODULE%) got an automated test at %DATE%.\\nMain result : %PERCENT% % - %PREREQUIST%\\n\\nDetailed results :\\n%SKILLS%\\n\\nCoding Style :",
      "color": null,
      "fields": [
        {
          "name": "Fatal",
          "value": "%FATAL%"
        },
        {
          "name": "Major",
          "value": "%MAJOR%"
        },
        {
          "name": "Minor",
          "value": "%MINOR%"
        },
        {
          "name": "Infos",
          "value": "%INFOS%"
        }
      ],
      "footer": {
        "text": "Test ID : %RUNID%\\nTest ran at : %DATE%\\nTest ran with the following logins :\\n%LOGINS%"
      }
    }
  ],
  "attachments": []
}"""

# Both of these need to be set in your env (with the command : `export TOKEN="IDONTHAVEASOUL"``). Retreive your token in the local storage (don't laugh, don't laugh...) in the "my.epitech.eu" website, once login.

def get_json():
    r = requests.get(URL, headers={
        'Authorization': 'Bearer '+TOKEN,
        'Content-Type': 'applications/json'
    })
    if r.content:
        try:
            return r.json()
        except:
            if DEBUG:
                print("+ Invalid JSON data")
            pass
    return {}

def send_webhook(data):
    print("+ Posting webhook message")
    requests.post(WEBHOOK_URL, json=data)

def load_date(date_str: str):
    if not date_str:
        return datetime.fromtimestamp(0) # Should be old enough
    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")

def get_project_by_id(current: list, pid: str):
    for project in current:
        if not project.get("project"):
            continue
        if not project.get("project").get("module"):
            continue
        pold = project.get("project").get("module").get("code") + ':' + project.get("project").get("slug")
        if pold == pid:
            return project
    return None

def get_percents(skills: dict):
    total = 0
    passed = 0
    for res in skills.values():
        total += res.get("count") or 0
        passed += res.get("passed") or 0
    return passed * 100 / total

def get_skill_formated(skill):
    string = f"Total : {skill.get('count')}"
    if skill.get("passed") is not None:
        string += f". {skill.get('passed')} passed"
    if skill.get("crashed") is not None:
        string += f", {skill.get('crashed')} crashed"
    if skill.get("mandatoryFailed") is not None:
        string += f", {skill.get('mandatoryFailed')} mandatory failed"
    return string

def get_with_type(lst: list, type: str):
    for e in lst:
        if e.get("type") == type:
            return e.get("value")
    return None

def check_and_send_webhooks(current: list, new: list):
    for project in new:
        if not project.get("project") or not project.get("results") or not project.get("date"):
            continue
        if not project.get("project").get("module"):
            continue
        pid = project.get("project").get("module").get("code") + ':' + project.get("project").get("slug")
        if DEBUG:
            print(f"+ Checking the old project {pid}")
        old_project = get_project_by_id(current, pid)
        if not old_project:
            old_project = {"date": "2000-01-01T00:00:00Z"}
        if load_date(project["date"]) > load_date(old_project["date"]):
            # Yeah, new ta
            if DEBUG:
                print("+ New project found, crafting Webhook")
            current_whook_data = {
                "%NAME%": project.get("project").get("name"),
                "%SLUG%": project.get("project").get("slug"),
                "%MODULE%": project.get("project").get("module").get("code"),
                "%DATE%": (load_date(project.get("date")) + datetime.timedelta(hours=1)).strftime("%Y/%m/%d - %H:%M:%S"),
                "%RUNID%": project.get("results").get("testRunId"),
                "%LOGINS%": ', '.join(
                    project.get("results").get("testRunId") if type(project.get("results").get("testRunId")) == list else []
                ),
                "%PREREQUIST%": {
                    0.5: "Delivery error",
                    1: "Mandatory test failed",
                    2: "Prerequisites met"
                }[project.get("results").get("prerequisites")] or "Invalid value",
                "%PERCENT%": get_percents(project.get("results").get("skills")),
                "%SKILLS%": '\\n\\n'.join([
                    f"{exo} : {get_skill_formated(skills)}" for exo, skills in project.get("results").get("skills").items()
                ]),
                "%FATAL%": get_with_type(project.get("results").get("externalItems"), "lint.fatal"),
                "%MAJOR%": get_with_type(project.get("results").get("externalItems"), "lint.major"),
                "%MINOR%": get_with_type(project.get("results").get("externalItems"), "lint.minor"),
                "%INFOS%": get_with_type(project.get("results").get("externalItems"), "lint.info")
            }
            whook = WEBHOOK_CONTENT
            for k, v in current_whook_data.items():
                whook = whook.replace(k, str(v).replace('"', '\\"'))
            if DEBUG:
                print("+ Webhook crafted sucessfully, output JSON :")
                print(whook)
            send_webhook(json.loads(whook))


current_state = get_json()

while 1:
    time.sleep(PING_EVERY)
    if DEBUG:
        print("+ Quering the website")
    data = get_json()
    if data:
        check_and_send_webhooks(current_state, data)
    elif DEBUG:
        print("+ No data got, ignoring this time (might come from invalid TOKEN, I guess)")
    current_state = data
