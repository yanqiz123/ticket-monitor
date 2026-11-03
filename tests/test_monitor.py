import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from monitor import find_available

HERE = os.path.dirname(__file__)


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)["data"]


class TestFindAvailable(unittest.TestCase):
    def test_soldout_has_no_hits(self):
        # 真实售罄项目（Jon Steingard 上海站，全部 flag=4 已售罄）
        self.assertEqual(find_available(load("fixture_soldout.json")), [])

    def test_available_flag1_is_hit(self):
        hits = find_available(load("fixture_available.json"))
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["desc"], "180（超级早鸟票）")
        self.assertEqual(hits[0]["price_yuan"], 180.0)

    def test_watch_keyword_filter(self):
        hits = find_available(load("fixture_available.json"), watch=["VIP"])
        self.assertEqual(hits, [])
        hits = find_available(load("fixture_available.json"), watch=["早鸟"])
        self.assertEqual(len(hits), 1)

    def test_stopped_flag3_with_stock_num_is_not_hit(self):
        # 洛天依广州站实测：flag=3 已停售的票档 num 可能 >0，不能误报
        data = load("fixture_soldout.json")
        t = data["screen_list"][0]["ticket_list"][0]
        t["sale_flag"] = {"number": 3, "display_name": "已停售"}
        t["num"] = 6
        self.assertEqual(find_available(data), [])


if __name__ == "__main__":
    unittest.main()
