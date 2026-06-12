import unittest

from taxnet.pipeline import run_pipeline

try:
    import falkordb  # noqa: F401

    FALKORDB_AVAILABLE = True
except Exception:
    FALKORDB_AVAILABLE = False


class FalkorClientImportTests(unittest.TestCase):
    def test_client_imports_or_gives_clear_error(self):
        try:
            from taxnet.falkor_engine import get_falkordb_client

            self.assertTrue(callable(get_falkordb_client))
        except RuntimeError as exc:
            self.assertIn("falkordb package is not installed", str(exc))


@unittest.skipUnless(FALKORDB_AVAILABLE, "falkordb package not installed")
class FalkorEngineTests(unittest.TestCase):
    def test_load_synthetic_graph(self):
        result = run_pipeline()
        summary = result.get("falkor_summary")
        self.assertIsNotNone(summary)
        if summary and "error" in summary:
            self.fail(f"FalkorDB load failed: {summary['error']}")
        self.assertIn("nodes", summary)
        self.assertIn("edges", summary)
        self.assertGreater(summary["nodes"], 0)
        self.assertGreater(summary["edges"], 0)

    def test_pagerank_returns_scores(self):
        from taxnet.falkor_engine import run_pagerank

        run_pipeline()
        scores = run_pagerank("taxnet")
        self.assertIsInstance(scores, dict)
        if scores:
            self.assertTrue(all(0 <= v <= 1 for v in scores.values()))

    def test_communities_returns_components(self):
        from taxnet.falkor_engine import run_communities

        run_pipeline()
        communities = run_communities("taxnet")
        self.assertIsInstance(communities, dict)

    def test_degrees_returns_counts(self):
        from taxnet.falkor_engine import run_degrees

        run_pipeline()
        degrees = run_degrees("taxnet")
        self.assertIsInstance(degrees, dict)
