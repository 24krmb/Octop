"""Focused data-integrity and safe rendering checks; no live-market assertions."""
import copy
import json
import unittest
from render_report import ROOT, measure, render, timestamp


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "assets/demo.json").read_text(encoding="utf-8"))
        self.row = self.data["markets"][0]
        self.start = timestamp(self.data["requested_start"])
        self.end = timestamp(self.data["requested_end"])

    def test_return_and_chart_share_calculation(self):
        result, reason = measure(self.row, self.start, self.end)
        self.assertEqual(float(result), 3.2)
        self.assertEqual(reason, "")
        html, evidence = render(self.data)
        self.assertEqual(html.count("+3.20%"), 2)
        self.assertIn("风险提示：", evidence["risk_disclaimer"])
        self.assertIn("样式演示", html)

    def test_real_data_scenario_labels_are_not_synthetic_demo(self):
        self.data["demo"] = False
        self.data["events"] = []
        for scenario, label in (("custom_interval", "自定义区间观察"),
                                ("simulated_holiday", "仅假设国内休市")):
            self.data["scenario"] = scenario
            html, evidence = render(self.data)
            self.assertIn(label, html)
            self.assertNotIn("以下日期、价格与事件均为合成样例", html)
            self.assertEqual(evidence["scenario"], scenario)
            self.assertEqual(html.count("+3.20%"), 2)
        self.data["scenario"] = "unknown"
        with self.assertRaises(ValueError):
            render(self.data)

    def test_missing_and_zero_baseline_are_not_zero_returns(self):
        for value in (None, 0, -1, "NaN", "Infinity"):
            with self.subTest(value=value):
                self.row["base"] = value
                pct, reason = measure(self.row, self.start, self.end)
                self.assertIsNone(pct)
                self.assertTrue(reason)

    def test_time_boundaries(self):
        for field, value in [("base_time", "2025-10-01T15:00:00+08:00"),
                             ("last_time", "2025-10-04T11:00:00+08:00"),
                             ("last_time", "2025-09-30T14:59:00+08:00"),
                             ("base_time", "2025-09-30T15:00:00")]:
            row = dict(self.row, **{field: value})
            self.assertIsNone(measure(row, self.start, self.end)[0])
        row = dict(self.row, base_time="2025-09-30T06:59:00Z")
        self.assertIsNotNone(measure(row, self.start, self.end)[0])

    def test_duplicate_foreign_mapping_rejected(self):
        duplicate = copy.deepcopy(self.row)
        duplicate["domestic"] = ["沥青"]
        self.data["markets"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "重复"):
            render(self.data)

    def test_in_window_endpoints_are_ranked_without_weakening_anchor_mode(self):
        self.data["markets"] = [dict(self.row, base_time="2025-10-01T15:00:00+08:00")]
        anchor_html, anchor_evidence = render(self.data)
        self.assertNotIn('class="bar-row"', anchor_html)
        self.assertEqual(anchor_evidence["endpoint_mode"], "pre_window_anchor")
        self.data["endpoint_mode"] = "in_window"
        html, evidence = render(self.data)
        self.assertEqual(html.count("+3.20%"), 2)
        self.assertIn("窗口内首末有效原始记录", html)
        self.assertEqual(evidence["endpoint_mode"], "in_window")
        self.assertTrue(any("窗口内首末" in s for s in evidence["method_notes"]))

    def test_in_window_rejects_outside_equal_reversed_and_naive_endpoints(self):
        cases = [
            {"base_time": "2025-09-30T14:59:00+08:00"},
            {"last_time": "2025-10-04T10:01:00+08:00"},
            {"last_time": self.row["base_time"]},
            {"base_time": self.row["last_time"], "last_time": self.row["base_time"]},
            {"base_time": "2025-09-30T15:00:00"},
        ]
        for change in cases:
            with self.subTest(change=change):
                self.assertIsNone(measure(dict(self.row, **change), self.start, self.end, "in_window")[0])
        boundary = dict(self.row, base_time=self.data["requested_start"], last_time=self.data["requested_end"])
        self.assertIsNotNone(measure(boundary, self.start, self.end, "in_window")[0])
        utc_row = dict(self.row, base_time="2025-09-30T07:00:00Z")
        self.assertIsNotNone(measure(utc_row, self.start, self.end, "in_window")[0])

    def test_unknown_endpoint_mode_fails_even_without_markets(self):
        for mode in ("unknown", None):
            with self.subTest(mode=mode):
                self.data["endpoint_mode"] = mode
                self.data["markets"] = []
                with self.assertRaisesRegex(ValueError, "端点口径"):
                    render(self.data)

    def test_price_only_report_omits_empty_event_section_but_discloses_gap(self):
        self.data["events"] = []
        html, evidence = render(self.data)
        self.assertNotIn("<h2>重要事件</h2>", html)
        self.assertIn("行情版", html)
        self.assertIn("不代表观察区间内没有重要事件", html)
        self.assertIn('<span>03</span><h2>关联观察', html)
        self.assertTrue(any("未列示已核验事件" in s for s in evidence["limitations"]))
        self.assertNotIn("@@", html)

    def test_full_report_preserves_event_section_and_sequence(self):
        html, _ = render(self.data)
        self.assertIn('<span>03</span><h2>重要事件', html)
        self.assertIn('<span>04</span><h2>关联观察', html)
        self.assertNotIn("@@", html)

    def test_missing_codes_use_exchange_and_name_for_identity(self):
        first = dict(self.row, exchange="同一交易所", symbol="未提供", basis="连续合约")
        second = dict(first, name="另一品种")
        self.data["markets"] = [first, second]
        render(self.data)
        self.data["markets"].append(dict(first, domestic=["另一国内映射"]))
        with self.assertRaisesRegex(ValueError, "重复"):
            render(self.data)

    def test_no_quote_and_no_event_degrades_honestly(self):
        self.data["demo"] = False
        self.data["markets"] = []
        self.data["events"] = []
        html, _ = render(self.data)
        self.assertIn("不构成完整行情报告", html)
        self.assertIn("没有满足统一口径", html)

    def test_escape_text_and_reject_script_links(self):
        self.data["title"] = '<script>alert("x")</script>'
        html, _ = render(self.data)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.data["events"][0]["sources"] = [{"label":"恶意来源","url":"javascript:alert(1)"}]
        with self.assertRaisesRegex(ValueError, "HTTP"):
            render(self.data)

    def test_future_window_and_unlinked_real_event_rejected(self):
        self.data["generated_at"] = "2025-10-04T09:00:00+08:00"
        with self.assertRaises(ValueError):
            render(self.data)
        self.data["generated_at"] = "2025-10-04T10:00:00+08:00"
        self.data["demo"] = False
        with self.assertRaisesRegex(ValueError, "来源"):
            render(self.data)


if __name__ == "__main__":
    unittest.main()
