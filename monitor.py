#!/usr/bin/env python3
"""余票监控：定时查询 Bilibili 会员购公开项目接口，发现可购票档时提醒。

边界：只做公开信息查询和提醒。不登录、不保存 Cookie、不下单、不使用代理。
轮询带最小间隔与错误退避，请合理使用。
"""
import json
import random
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

API = "https://show.bilibili.com/api/ticket/project/getV2?version=134&id={pid}&page_type=0"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Referer": "https://show.bilibili.com/platform/detail.html?id={pid}",
}
MIN_INTERVAL = 10  # 秒，配置再小也会被钳制到这个下限


def now():
    return datetime.now().strftime("%H:%M:%S")


def fetch_project(project_id, timeout=15):
    req = urllib.request.Request(
        API.format(pid=project_id),
        headers={k: v.format(pid=project_id) for k, v in HEADERS.items()},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("code") != 0:
        raise RuntimeError(f"接口返回 code={payload.get('code')}")
    return payload["data"]


def find_available(data, watch=None):
    """返回可购票档列表。会员购 sale_flag.number == 1 为可购买状态。

    注意：num 字段不是可靠库存数（停售票档也可能 num>0），不作为判断依据。
    watch 为票档描述关键词列表，留空表示监控全部票档。
    """
    hits = []
    for screen in data.get("screen_list") or []:
        for t in screen.get("ticket_list") or []:
            flag = (t.get("sale_flag") or {}).get("number")
            if flag != 1:
                continue
            desc = t.get("desc", "")
            if watch and not any(k in desc for k in watch):
                continue
            hits.append({
                "project": data.get("name", ""),
                "screen": screen.get("name") or screen.get("start_time_str", ""),
                "desc": desc,
                "price_yuan": (t.get("price") or 0) / 100.0,
            })
    return hits


def notify(hits, webhook_url=""):
    lines = [f"[{now()}] 发现可购票档："]
    for h in hits:
        lines.append(f"  {h['project']} | {h['screen']} | {h['desc']} | ¥{h['price_yuan']:.0f}")
    text = "\n".join(lines)
    print("\a" + text, flush=True)
    with open("hits.log", "a", encoding="utf-8") as f:
        f.write(text + "\n")
    if webhook_url:
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps({"title": "余票提醒", "text": text}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as e:
            print(f"[{now()}] webhook 发送失败：{e}", flush=True)


def check_once(target):
    data = fetch_project(target["project_id"])
    return find_available(data, target.get("watch") or [])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    once = "--once" in sys.argv
    cfg_path = args[0] if args else "config.json"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    interval = max(MIN_INTERVAL, int(cfg.get("interval_seconds", 30)))
    stop_first = cfg.get("stop_on_first_hit", True)
    webhook = cfg.get("webhook_url", "")
    targets = cfg["targets"]
    print(f"[{now()}] 开始监控 {len(targets)} 个项目，间隔约 {interval}s"
          f"{'（单次检查）' if once else ''}", flush=True)

    seen = set()  # 已提醒过的 (项目, 场次, 票档)，只在状态变化时提醒一次
    backoff = interval
    while True:
        try:
            for target in targets:
                hits = check_once(target)
                fresh = [h for h in hits
                         if (h["project"], h["screen"], h["desc"]) not in seen]
                label = target.get("remark") or target["project_id"]
                if hits:
                    print(f"[{now()}] {label}：{len(hits)} 个票档可购", flush=True)
                else:
                    print(f"[{now()}] {label}：暂无可购票档", flush=True)
                if fresh:
                    for h in fresh:
                        seen.add((h["project"], h["screen"], h["desc"]))
                    notify(fresh, webhook)
                    if stop_first and not once:
                        print(f"[{now()}] 已提醒，监控结束（stop_on_first_hit=true）", flush=True)
                        return
            backoff = interval
            if once:
                return
        except (urllib.error.URLError, RuntimeError, TimeoutError) as e:
            print(f"[{now()}] 查询出错：{e}，退避 {backoff}s 后重试", flush=True)
            if once:
                return
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)
            continue
        time.sleep(interval * random.uniform(0.9, 1.1))


if __name__ == "__main__":
    main()
