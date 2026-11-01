import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import jpx_universe as jpx


class UniverseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.df = pd.DataFrame([
            ['20260930', '7203', 'トヨタ', 'プライム（内国株式）', '3700', '輸送用機器', '6', '自動車・輸送機', '1', 'TOPIX Core30'],
            ['20260930', '285A', 'テスト', 'グロース（内国株式）', '5250', '情報・通信業', '10', '情報通信・サービスその他', '-', '-'],
        ], columns=jpx.REQUIRED)
        stream = io.BytesIO()
        self.df.to_excel(stream, index=False)
        self.excel = stream.getvalue()

    def test_excel_validation(self):
        self.assertEqual(jpx.read_master(self.excel)['コード'].tolist(), ['7203', '285A'])
        with self.assertRaises(Exception):
            jpx.read_master(b'<html>Error</html>')

    def test_filters_and_invalid_value(self):
        self.assertEqual(jpx.select(self.df, sector33=['輸送用機器'], sizes=['TOPIX Core30']).Ticker.tolist(), ['7203.T'])
        self.assertTrue(jpx.select(self.df, sector17=['自動車・輸送機'], sizes=['-']).empty)
        self.assertEqual(len(jpx.select(self.df, sizes=['TOPIX Core30', '-'])), 2)
        with self.assertRaises(ValueError):
            jpx.select(self.df, sizes=['Core30'])

    def test_five_digit_preferred_share_preserved_only_in_master(self):
        df = self.df.copy()
        df.loc[0, 'コード'] = '25935'
        stream = io.BytesIO()
        df.to_excel(stream, index=False)
        master = jpx.read_master(stream.getvalue())
        self.assertEqual(master.iloc[0]['コード'], '25935')
        self.assertEqual(jpx.select(master).Ticker.tolist(), ['285A.T'])

    def test_manual_normalization_order_and_priority(self):
        manual = self.root / 'manual.csv'
        manual.write_text('Ticker,Name,Group\n7203.t,別名,Manual\n285a,,\n285A.T,,\n9999,独自銘柄,Watch\n', encoding='utf-8-sig')
        result = jpx.merge_manual(jpx.select(self.df, sizes=['TOPIX Core30']), [manual], self.df)
        self.assertEqual(result.Ticker.tolist(), ['7203.T', '285A.T', '9999.T'])
        self.assertEqual(result.Name.tolist(), ['トヨタ', 'テスト', '独自銘柄'])
        self.assertEqual(result.columns.tolist(), jpx.OUTPUT)

    def test_failed_download_preserves_cache_and_csv(self):
        cache, out = self.root / 'data_j.xlsx', self.root / 'out.csv'
        cache.write_bytes(self.excel)
        out.write_bytes(b'old-csv')
        for failure in [OSError('network failure'), None]:
            with patch.object(jpx, 'fetch', side_effect=failure, return_value=b'bad html'):
                self.assertEqual(jpx.main(['--cache', str(cache), '--output', str(out)]), 1)
            self.assertEqual(cache.read_bytes(), self.excel)
            self.assertEqual(out.read_bytes(), b'old-csv')

    def test_bad_manual_and_zero_result_preserve_csv(self):
        cache, out = self.root / 'data_j.xlsx', self.root / 'out.csv'
        cache.write_bytes(self.excel)
        out.write_bytes(b'old')
        manual = self.root / 'manual.csv'
        manual.write_text('Ticker\nBAD.VALUE\n', encoding='utf-8')
        common = ['--offline', '--cache', str(cache), '--output', str(out)]
        self.assertEqual(jpx.main(common + ['--manual', str(manual)]), 1)
        self.assertEqual(jpx.main(common + ['--sector17', '自動車・輸送機', '--size', '-']), 1)
        self.assertEqual(out.read_bytes(), b'old')

    def test_history_and_chart_compatible_output(self):
        cache, out = self.root / 'data_j.xlsx', self.root / 'out.csv'
        html = b'<a href="/markets/statistics-equities/misc/x/data_j.xlsx">Excel</a>'
        with patch.object(jpx, 'fetch', side_effect=[html, self.excel]):
            self.assertEqual(jpx.main(['--cache', str(cache), '--output', str(out)]), 0)
        self.assertEqual(cache.read_bytes(), self.excel)
        self.assertEqual(len(list((self.root / 'history').glob('*.xlsx'))), 1)
        chart = pd.read_csv(out, dtype={'Code': str, 'Ticker': str})
        self.assertEqual(chart.Ticker.tolist(), ['7203.T', '285A.T'])
        self.assertTrue(out.read_bytes().startswith(b'\xef\xbb\xbf'))


if __name__ == '__main__':
    unittest.main()
