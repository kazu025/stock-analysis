"""監視銘柄の登録・編集・削除（標準ライブラリのみ）。

python watchlist_manager.py
python watchlist_manager.py --watchlist path/to/watchlist.csv
"""
import argparse
import csv
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

COLUMNS = ["Ticker", "Name", "Category", "Priority", "SupportLow", "SupportHigh",
           "ResistanceLow", "ResistanceHigh", "Status", "Memo", "Shares", "Cost"]
DEFAULT = Path(__file__).resolve().parent / "watchlist.csv"


def normalize_ticker(value):
    ticker = str(value).strip().upper()
    return ticker if '.' in ticker else ticker + '.T'


def read_watchlist(path):
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not {'Ticker', 'Name'}.issubset(reader.fieldnames):
            raise ValueError('監視CSVには Ticker と Name が必要です')
        return [{key: (row.get(key) or '') for key in COLUMNS} for row in reader]


def write_watchlist(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watchlist', type=Path, default=DEFAULT)
    args = parser.parse_args()
    path = args.watchlist
    rows = read_watchlist(path)
    root = tk.Tk()
    root.title('監視銘柄管理')
    root.geometry('1120x640')
    frame = ttk.Frame(root, padding=12)
    frame.pack(fill='both', expand=True)
    columns = ('Ticker', 'Name', 'Category', 'Priority', 'Status', 'Shares')
    tree = ttk.Treeview(frame, columns=columns, show='headings', height=10)
    for col, size in [('Ticker', 95), ('Name', 180), ('Category', 95), ('Priority', 70), ('Status', 250), ('Shares', 70)]:
        tree.heading(col, text=col)
        tree.column(col, width=size)
    tree.pack(fill='both', expand=True)
    fields = {}
    form = ttk.Frame(frame)
    form.pack(fill='x', pady=8)
    labels = {
        'Ticker': '銘柄コード', 'Name': '銘柄名', 'Category': '投資分類', 'Priority': '優先度',
        'SupportLow': '支持帯下限', 'SupportHigh': '支持帯上限',
        'ResistanceLow': '抵抗帯下限', 'ResistanceHigh': '抵抗帯上限',
        'Status': '状態', 'Memo': '判断メモ', 'Shares': '保有株数', 'Cost': '平均取得単価'
    }
    for i, key in enumerate(COLUMNS):
        rr, cc = divmod(i, 4)
        ttk.Label(form, text=labels[key]).grid(row=rr*2, column=cc, sticky='w', padx=5)
        var = tk.StringVar()
        if key == 'Category':
            widget = ttk.Combobox(form, textvariable=var, values=['RANGE', 'TREND', 'OTHER'], width=22)
        elif key == 'Priority':
            widget = ttk.Combobox(form, textvariable=var, values=['A', 'B', 'C'], width=22)
        else:
            widget = ttk.Entry(form, textvariable=var, width=25)
        widget.grid(row=rr*2+1, column=cc, sticky='ew', padx=5, pady=(0, 8))
        fields[key] = var
    for cc in range(4):
        form.columnconfigure(cc, weight=1)

    def refresh():
        for iid in tree.get_children():
            tree.delete(iid)
        for i, row in enumerate(rows):
            tree.insert('', 'end', iid=str(i), values=[row.get(k, '') for k in columns])

    def fill_selected(_event=None):
        selected = tree.selection()
        if selected:
            row = rows[int(selected[0])]
            for key in COLUMNS:
                fields[key].set(row.get(key, ''))

    def clear():
        for value in fields.values():
            value.set('')
        fields['Category'].set('RANGE')
        fields['Priority'].set('B')
        tree.selection_remove(tree.selection())

    def save():
        data = {key: var.get().strip() for key, var in fields.items()}
        if not data['Ticker'] or not data['Name']:
            messagebox.showerror('入力エラー', '銘柄コードと銘柄名は必須です')
            return
        data['Ticker'] = normalize_ticker(data['Ticker'])
        if data['Category'] not in ('RANGE', 'TREND', 'OTHER') or data['Priority'] not in ('A', 'B', 'C'):
            messagebox.showerror('入力エラー', '分類と優先度を選択してください')
            return
        for key in ('SupportLow','SupportHigh','ResistanceLow','ResistanceHigh','Cost'):
            if data[key]:
                try:
                    if float(data[key]) < 0: raise ValueError()
                except ValueError:
                    messagebox.showerror('入力エラー', f'{labels[key]} は0以上の数値です')
                    return
        if data['Shares']:
            try:
                if int(data['Shares']) < 0: raise ValueError()
            except ValueError:
                messagebox.showerror('入力エラー', '保有株数は0以上の整数です')
                return
        selected = tree.selection()
        index = int(selected[0]) if selected else next((i for i, item in enumerate(rows) if normalize_ticker(item['Ticker']) == data['Ticker']), None)
        if any(normalize_ticker(item['Ticker']) == data['Ticker'] for i, item in enumerate(rows) if i != index):
            messagebox.showerror('重複', '銘柄コードが既に登録されています')
            return
        if index is None:
            rows.append(data)
        else:
            rows[index] = data
        write_watchlist(path, rows)
        refresh()
        clear()

    def delete():
        selected = tree.selection()
        if not selected:
            messagebox.showinfo('削除', '削除する銘柄を選択してください')
            return
        idx = int(selected[0])
        if messagebox.askyesno('削除確認', f"{rows[idx]['Name']} を監視一覧から削除しますか？"):
            del rows[idx]
            write_watchlist(path, rows)
            refresh()
            clear()

    tree.bind('<<TreeviewSelect>>', fill_selected)
    buttons = ttk.Frame(frame)
    buttons.pack(fill='x')
    ttk.Button(buttons, text='新規入力', command=clear).pack(side='left', padx=5)
    ttk.Button(buttons, text='登録 / 更新', command=save).pack(side='left', padx=5)
    ttk.Button(buttons, text='選択行を削除', command=delete).pack(side='left', padx=5)
    ttk.Label(buttons, text=f'保存先: {path}').pack(side='left', padx=16)
    refresh()
    clear()
    root.mainloop()


if __name__ == '__main__':
    main()
