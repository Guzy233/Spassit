import requests
import logging
import time
import copy
import os

url = None
payload = None
headers = None
prompts_modify_time = 0
Ndia = 0
prompts_path = "prompts.txt"


def init(config, funcs):
    global payload, prompts_modify_time, headers, url, Ndia, prompts_path

    url = config["url"]
    prompts_path = config["system"]
    Ndia = config["keep_dialog"]
    payload = copy.deepcopy(config["payload"])

    prompt = (
        open(config["system"], encoding="utf-8").read().replace("{$functions}", funcs)
    )
    prompts_modify_time = os.path.getmtime(prompts_path)

    payload["messages"].append({"role": "system", "content": prompt})
    payload["model"] = config["models"][0]

    headers = {
        "Authorization": f"Bearer {config["key"]}",
        "Content-Type": "application/json",
    }

    logging.info("LLM初始化完成,使用模型:" + config["models"][0])
    logging.info(f"-URL:{url}")
    logging.info(f"-API_KEY:{config['key'][:5] + '*' * (len(config['key']) - 8) + config['key'][-3:]}")


def call_llm_api(prompt):
    # 检查系统提示词是否有更新
    global prompts_modify_time, payload, Ndia, prompts_path
    if prompts_modify_time != os.path.getmtime(prompts_path):
        prompts_modify_time = os.path.getmtime(prompts_path)
        payload["messages"][0][
            "content"
        ] = f"{open(prompts_path, encoding='utf-8').read()}"

    payload["messages"].append({"role": "user", "content": prompt})

    # 发送请求并获取LLM的回答
    stime = time.time()
    response = requests.request("POST", url, json=payload, headers=headers)
    etime = time.time()
    content = response.json()["choices"][0]["message"]["content"]

    payload["messages"].append({"role": "assistant", "content": content})

    if len(payload["messages"]) > 1 + Ndia * 2:
        new = [payload["messages"][0]] + payload["messages"][-Ndia * 2 :]
        payload["messages"] = new

    return content, etime - stime


if __name__ == "__main__":
    print(call_llm_api("打开连点"))
