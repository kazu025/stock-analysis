"""JPX原本取得 → 条件抽出 → 手入力追加 → チャート互換CSV。Python 3.10+。"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PAGE = 'https://www.jpx.co.jp/markets/statistics-equities/misc/01.html'
REQUIRED = ['日付', 'コード', '銘柄名', '市場・商品区分', '33業種コード',
            '33業種区分', '17業種コード', '17業種区分', '規模コード', '規模区分']
OUTPUT = ['Ticker', 'Name', 'Group', 'Code', 'Sector17', 'Sector33', 'Market']


def atomic_write(path: Path, data: bytes):
    """同一ディレクトリの一時ファイルが完成してから置換する。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def fetch(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'www.jpx.co.jp':
        raise ValueError('取得先はHTTPSのJPX公式サイトに限定します')
    with urlopen(Request(url, headers={'User-Agent': 'StockAnalysis-JPX/1.0'}), timeout=45) as response:
        if urlparse(response.url).hostname != 'www.jpx.co.jp':
            raise ValueError('JPX以外へのリダイレクトを拒否しました')
        return response.read()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for key, value in attrs:
                if key == 'href' and value and urlparse(value).path.endswith('/data_j.xlsx'):
                    self.urls.append(urljoin(PAGE, value))


def read_master(data: bytes):
    df = pd.read_excel(io.BytesIO(data), dtype=str, engine='openpyxl').fillna('')
    missing = set(REQUIRED) - set(df.columns)
    if missing or df.empty:
        raise ValueError(f'JPX Excelの形式が不正です。欠落列: {sorted(missing)}')
    df = df[REQUIRED].apply(lambda col: col.str.strip())
    if not df['コード'].str.fullmatch(r'(?:[0-9A-Z]{4}|[0-9]{5})').all():
        raise ValueError('JPXコードに不正な値があります')
    if df['コード'].duplicated().any() or df['銘柄名'].eq('').any():
        raise ValueError('JPXコードの重複または空の銘柄名があります')
    if not df['日付'].str.fullmatch(r'\d{8}').all():
        raise ValueError('JPX基準日の形式が不正です')
    pd.to_datetime(df['日付'], format='%Y%m%d', errors='raise')
    return df


def acquire(cache: Path, offline=False):
    if offline:
        return read_master(cache.read_bytes())
    parser = Links()
    parser.feed(fetch(PAGE).decode('utf-8'))
    urls = list(dict.fromkeys(parser.urls))
    if len(urls) != 1:
        raise ValueError('公式ページからdata_j.xlsxのリンクを一意に取得できません')
    data = fetch(urls[0])
    df = read_master(data)  # 検証完了まで既存ファイルへ書き込まない
    digest = hashlib.sha256(data).hexdigest()
    history = cache.parent / 'history' / f'data_j_{df["日付"].max()}_{digest}.xlsx'
    if not history.exists():
        atomic_write(history, data)
    # 取得元と確認時刻も履歴に保存。原本のバイト列は加工しない。
    meta = history.with_suffix('.json')
    atomic_write(meta, json.dumps({'source_page': PAGE, 'download_url': urls[0],
                 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                 'sha256': digest, 'rows': len(df)}, ensure_ascii=False, indent=2).encode('utf-8'))
    atomic_write(cache, data)
    return df


def select(df, sector17=(), sector33=(), sizes=(), markets=()):
    # 種類株式の5桁コードは原本に保持するが、4桁.Tへの機械的変換はしない。
    selected = df[df['コード'].str.fullmatch(r'[0-9A-Z]{4}')].copy()
    for column, values in [('17業種区分', sector17), ('33業種区分', sector33),
                           ('規模区分', sizes), ('市場・商品区分', markets)]:
        if values:
            invalid = set(values) - set(df[column])
            if invalid:
                raise ValueError(f'{column} に存在しない指定: {sorted(invalid)}')
            selected = selected[selected[column].isin(values)]
    result = pd.DataFrame({
        'Ticker': selected['コード'] + '.T', 'Name': selected['銘柄名'],
        'Group': selected['規模区分'], 'Code': selected['コード'],
        'Sector17': selected['17業種区分'], 'Sector33': selected['33業種区分'],
        'Market': selected['市場・商品区分'],
    })
    return result.reset_index(drop=True)


def normalize_ticker(value):
    value = str(value).strip().upper()
    if re.fullmatch(r'[0-9A-Z]{4}', value):
        value += '.T'
    if not re.fullmatch(r'[0-9A-Z]{4}\.T', value):
        raise ValueError(f'日本株Tickerが不正です: {value!r} (例: 7203.T / 285A)')
    return value


def merge_manual(result, paths, master):
    lookup = select(master).set_index('Ticker')
    frames = [result]
    for path in paths:
        manual = pd.read_csv(path, dtype=str, encoding='utf-8-sig', keep_default_na=False)
        if not ({'Ticker', 'Code'} & set(manual.columns)):
            raise ValueError(f'{path}: TickerまたはCode列が必要です')
        rows = []
        for line, row in enumerate(manual.to_dict('records'), 2):
            try:
                ticker = normalize_ticker(row.get('Ticker', '') or row.get('Code', ''))
                if row.get('Code', '') and normalize_ticker(row['Code']) != ticker:
                    raise ValueError('CodeとTickerが一致しません')
                base = lookup.loc[ticker].to_dict() if ticker in lookup.index else dict.fromkeys(OUTPUT, '')
                base.update(Ticker=ticker, Code=ticker[:-2])
                for col in ('Name', 'Group'):
                    if row.get(col, '').strip():
                        base[col] = row[col].strip()
                if not base['Name']:
                    raise ValueError('JPX未登録銘柄にはNameを指定してください')
                if not base['Group']:
                    base['Group'] = 'Manual'
                rows.append(base)
            except ValueError as exc:
                raise ValueError(f'{path}:{line}: {exc}') from exc
        frames.append(pd.DataFrame(rows, columns=OUTPUT))
    # フィルター結果を優先。手入力は指定順に追加、重複は最初の行を採用。
    return pd.concat(frames, ignore_index=True).drop_duplicates('Ticker', keep='first')[OUTPUT]


def build_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache', type=Path, default=ROOT / 'data/jpx/data_j.xlsx')
    p.add_argument('--offline', action='store_true', help='保存済みExcelのみ使用')
    p.add_argument('--list-values', action='store_true', help='絞り込み指定値を表示して終了')
    p.add_argument('--download-only', action='store_true', help='原本取得・検証のみ')
    for arg in ('sector17', 'sector33', 'size', 'market'):
        p.add_argument('--' + arg, action='append', default=[], help='完全一致、複数指定可')
    p.add_argument('--manual', action='append', type=Path, default=[], help='追加CSV、複数指定可')
    p.add_argument('--output', type=Path, default=ROOT / 'data/jpx/universe.csv')
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        # 元Excelや手入力CSVを出力先で上書きする誤操作を防止。
        protected = [args.cache, *args.manual]
        if args.output.resolve() in [p.resolve() for p in protected] or args.output.suffix.lower() != '.csv':
            raise ValueError('出力先には元データとは異なる.csvファイルを指定してください')
        df = acquire(args.cache, args.offline)
        print(f'JPX基準日: {df["日付"].max()} / {len(df)}銘柄 / 原本: {args.cache}')
        special_count = int(df['コード'].str.len().eq(5).sum())
        if special_count:
            print(f'種類株式など5桁コード {special_count}件は原本に保持し、CSV変換対象から除外します')
        if args.list_values:
            for column in ['17業種区分', '33業種区分', '規模区分', '市場・商品区分']:
                print(column + ': ' + ', '.join(sorted(df[column].unique())))
            return 0
        if args.download_only:
            return 0
        result = merge_manual(select(df, args.sector17, args.sector33, args.size, args.market), args.manual, df)
        if result.empty:
            raise ValueError('抽出結果が0件です。既存CSVを保持します')
        atomic_write(args.output, result.to_csv(index=False).encode('utf-8-sig'))
        print(f'保存: {args.output} / {len(result)}銘柄')
        return 0
    except Exception as exc:
        print(f'失敗: {exc}\n既存CSVは更新していません。必要なら --offline で明示的に再実行してください。', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
