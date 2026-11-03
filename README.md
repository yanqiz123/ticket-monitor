# ticket-monitor 余票监控

定时查询 **Bilibili 会员购**公开项目接口，发现指定场次/票档变为可购买状态时立刻提醒你，你再去官方渠道手动下单。

## 这个工具做什么 / 不做什么

- ✅ 只做一件事：轮询公开的项目详情接口，判断票档状态，发现可购时通过控制台、日志和可选 webhook 提醒。
- ❌ 不登录任何账号，不保存 Cookie，不下单，不抢票，不使用代理，不做任何绕过平台规则的操作。
- 判断依据：接口中票档的 `sale_flag.number == 1`（可购买状态）。`num` 字段不是可靠库存数（停售票档也可能大于 0），不作为依据。

## 环境

Python 3.9+，零第三方依赖（只用标准库）。

## 使用

1. 复制配置模板并按需修改：

   ```bash
   cp config.example.json config.json
   ```

   - `targets[].project_id`：会员购项目编号，就是活动页链接 `detail.html?id=` 后面的数字。可加多个项目。
   - `targets[].watch`：只关心某些票档时填关键词（如 `["内场", "1280"]`），留空监控全部票档。
   - `interval_seconds`：查询间隔（秒），默认 30，最小钳制为 10，请勿设置得更密。
   - `stop_on_first_hit`：`true` 时首次发现可购票档、提醒后自动结束；`false` 则持续监控，同一票档只提醒一次（状态变化后才再次提醒）。
   - `webhook_url`：可选。发现余票时向该地址 POST 一段 JSON（`{"title": "余票提醒", "text": "..."}`），可对接你自己的转发服务；留空则只在控制台和 `hits.log` 里提醒。

2. 运行：

   ```bash
   python3 monitor.py            # 按 config.json 持续监控
   python3 monitor.py --once     # 只检查一次就退出（适合自测）
   ```

3. 看到提醒后，打开活动页手动购买即可。

## 礼貌使用

- 默认 30 秒间隔已足够及时；脚本对查询错误和限流做了指数退避（最长 5 分钟）。
- 请勿改小最小间隔或多开实例高频查询，给平台接口留出余量。

## 测试

```bash
python3 -m unittest discover -s tests -v
```

测试用的是脱敏后的真实接口响应样本：一个全部售罄的项目、一个含可购票档的样本，以及"已停售但 num>0 不得误报"的回归用例。

## 结构

```
monitor.py               主程序：查询、判断、提醒、轮询退避
config.example.json      配置模板
tests/test_monitor.py    解析逻辑单元测试
tests/fixture_*.json     测试样本
```
