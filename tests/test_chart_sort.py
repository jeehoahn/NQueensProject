import unittest
from analysis.chart_sort import ChartEntry, sort_chart_entries


class TestChartSort(unittest.TestCase):
    def setUp(self):
        self.rows = [
            ChartEntry('slow', 5.0, '5s', {'algorithm': 'slow', 'elapsed': 5.0, 'nodes': 400}),
            ChartEntry('partial', 0.1, '.1s', {'algorithm': 'partial', 'elapsed': 0.1}, partial=True),
            ChartEntry('fast', 2.0, '2s', {'algorithm': 'fast', 'elapsed': 2.0, 'nodes': 10}),
            ChartEntry('unknown', None, '-', {'algorithm': 'unknown', 'elapsed': None}),
        ]

    def test_good_first_runtime(self):
        self.assertEqual([r.label for r in sort_chart_entries(self.rows, 'elapsed')],
                         ['fast', 'slow', 'unknown', 'partial'])

    def test_toggle_sort_direction_still_puts_incomplete_last(self):
        self.assertEqual([r.label for r in sort_chart_entries(self.rows, 'elapsed', True)],
                         ['slow', 'fast', 'unknown', 'partial'])

    def test_sort_by_other_fields_and_unknown_last(self):
        self.assertEqual([r.label for r in sort_chart_entries(self.rows, 'nodes')],
                         ['fast', 'slow', 'unknown', 'partial'])
        self.assertEqual([r.label for r in sort_chart_entries(self.rows, 'algorithm')],
                         ['fast', 'slow', 'unknown', 'partial'])

    def test_estimation_error_ranking(self):
        rows = [
            ChartEntry('A-1', 10, '10s', {'algorithm_id': 'a', 'error': 20., 'rank': 2}),
            ChartEntry('B-1', 6, '6s', {'algorithm_id': 'b', 'error': 5., 'rank': 1}),
            ChartEntry('A-2', None, '-', {'algorithm_id': 'a', 'error': None, 'rank': None}),
        ]
        self.assertEqual([x.label for x in sort_chart_entries(rows, 'error')],
                         ['B-1', 'A-1', 'A-2'])
        visible = [x for x in rows if x.fields['algorithm_id'] == 'a']
        self.assertEqual(len(visible), 2)
