import unittest

from brief import analyze, health, pipeline, render
from brief.models import Hotspot, RawItem
from brief.utils import fmt_traffic, lexical_sim, parse_traffic

RED = ["車禍", "選舉", "死亡"]


class T(unittest.TestCase):
    def test_traffic(self):
        self.assertEqual(parse_traffic("20,000+"), 20000)
        self.assertEqual(parse_traffic("5萬+"), 50000)
        self.assertEqual(fmt_traffic(200000), "約 20 萬+")
        self.assertEqual(fmt_traffic(3000), "約 3 千+")
        self.assertEqual(fmt_traffic(500), "")          # 不顯示精確小數字

    def test_drop_filter(self):
        items = [RawItem("線上博弈廣告", "A", "news"), RawItem("寒流來襲", "A", "news")]
        self.assertEqual([i.title for i in pipeline.drop_filter(items, ["博弈"])], ["寒流來襲"])

    def test_cluster_lexical_substring(self):
        items = [RawItem("周杰倫", "G", "news", 1, weight=1.5), RawItem("周杰倫演唱會開賣", "Y", "news", 1)]
        self.assertEqual(len(pipeline.cluster(items)), 1)
        self.assertEqual(len(pipeline.cluster([RawItem("寒流來襲", "G", "news"), RawItem("演唱會開賣", "Y", "news")])), 2)

    def test_cluster_with_embeddings(self):
        a, b, c = RawItem("寒流來襲", "G", "news"), RawItem("明天最冷 全台急凍", "Y", "news"), RawItem("演唱會開賣", "E", "news")
        emb = {"寒流來襲": [1, 0], "明天最冷 全台急凍": [0.95, 0.1], "演唱會開賣": [0, 1]}
        cl = pipeline.cluster([a, b, c], embeddings=emb)
        self.assertEqual(sorted(len(x) for x in cl), [1, 2])

    def test_more_sources_rank_higher(self):
        multi = [RawItem("事件A", "S1", "news", 5), RawItem("事件A 最新", "S2", "news", 5), RawItem("事件A 後續", "S3", "news", 5)]
        solo = [RawItem("事件B完全不同", "S1", "news", 1)]
        spots = pipeline.score_clusters(pipeline.cluster(multi + solo), "news", {})
        self.assertEqual(spots[0].topic.startswith("事件A"), True)

    def test_growth_needs_history(self):
        sp = pipeline.score_clusters([[RawItem("新話題", "S", "news")]], "news", {})
        self.assertEqual(sp[0].growth, "stable")                       # 沒昨日資料 → 不加成
        prev = {"news": [{"topic": "別的事"}]}
        sp = pipeline.score_clusters([[RawItem("新話題", "S", "news")]], "news", prev)
        self.assertEqual(sp[0].growth, "new")

    def test_light_rules(self):
        base = dict(sentiment="正面", tragedy=False, controversial=False, celeb_or_brand=False, link_possible=True)
        self.assertEqual(analyze.decide_light(base, "寒流穿搭", RED)[0], "green")
        self.assertEqual(analyze.decide_light({**base, "celeb_or_brand": True}, "某藝人", RED)[0], "yellow")
        self.assertEqual(analyze.decide_light({**base, "controversial": True}, "x", RED)[0], "yellow")
        self.assertEqual(analyze.decide_light({**base, "sentiment": "負面"}, "x", RED)[0], "yellow")
        self.assertEqual(analyze.decide_light({**base, "tragedy": True}, "x", RED)[0], "red")
        self.assertEqual(analyze.decide_light({**base, "link_possible": False}, "x", RED)[0], "red")
        # 關鍵字規則優先於 AI：AI 說沒事也要紅燈
        self.assertEqual(analyze.decide_light(base, "國道車禍", RED)[0], "red")

    def test_red_has_no_suggestions_and_yellow_has_risk(self):
        s = Hotspot("1", "國道車禍", "news")
        analyze.apply_rules(s, {"sentiment": "正面", "link_possible": True, "angles": [{"type": "幽默", "idea": "x"}],
                                "sample_post": "p"}, RED)
        self.assertEqual((s.analysis["light"], s.analysis["angles"], s.analysis["sample_post"]), ("red", [], ""))
        y = Hotspot("2", "某藝人", "news")
        analyze.apply_rules(y, {"sentiment": "中性", "link_possible": True, "celeb_or_brand": True}, RED)
        self.assertTrue(y.analysis["risk_note"])
        g = Hotspot("3", "寒流", "news")
        analyze.apply_rules(g, {"sentiment": "中性", "link_possible": True, "risk_note": "不該出現"}, RED)
        self.assertEqual(g.analysis["risk_note"], "")                 # risk_note 僅黃燈出現

    def test_health_notify_schedule(self):
        self.assertEqual([n for n in range(1, 20) if health.should_notify(n)], [3, 10, 17])

    def test_health_same_day_rerun_not_double_counted(self):
        import json, os, tempfile
        health.HEALTH = os.path.join(tempfile.mkdtemp(), "health.json")
        bad, good = {"X": {"ok": False}}, {"X": {"ok": True}}
        health.update_health(bad, "2026-10-01")
        health.update_health(bad, "2026-10-01")            # 同一天手動再跑
        self.assertEqual(json.load(open(health.HEALTH))["X"]["fail_streak"], 1)
        health.update_health(bad, "2026-10-02")
        self.assertEqual(json.load(open(health.HEALTH))["X"]["fail_streak"], 2)
        health.update_health(good, "2026-10-02")           # 同一天重跑成功 → 歸零
        self.assertEqual(json.load(open(health.HEALTH))["X"]["fail_streak"], 0)

    def test_render_failure_footer(self):
        s = Hotspot("1", "寒流", "news", sources=["Google Trends"])
        analyze.apply_rules(s, {"sentiment": "中性", "link_possible": True}, RED)
        html = render.render({"news": [s], "style": []}, "2026-10-29", "Airspace", ["Dcard"], None)
        self.assertIn("Dcard", html)
        self.assertIn("今日此區無資料", html)


if __name__ == "__main__":
    unittest.main()
