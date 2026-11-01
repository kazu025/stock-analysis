"""Designerで保存したjpx_universe.uiを使う銘柄CSV作成画面。"""
from pathlib import Path
import sys

from PySide6.QtCore import QFile, QObject, QThread, Signal, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (QApplication, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget)

import jpx_universe as core


class Loader(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, cache, offline):
        super().__init__()
        self.cache, self.offline = cache, offline

    def run(self):
        try:
            self.succeeded.emit(core.acquire(self.cache, self.offline))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class Controller(QObject):
    def __init__(self):
        super().__init__()
        self.master = None
        self.thread = None
        self.cache = core.ROOT / 'data/jpx/data_j.xlsx'
        source = QFile(str(Path(__file__).with_name('jpx_universe.ui')))
        if not source.open(QFile.OpenModeFlag.ReadOnly):
            raise RuntimeError('jpx_universe.uiを開けません')
        try:
            self.window = QUiLoader().load(source)
        finally:
            source.close()
        if self.window is None:
            raise RuntimeError('画面ファイルを読み込めません')
        self.w = {w.objectName(): w for w in self.window.findChildren(QWidget)}
        required = ['labelSourceDate', 'buttonLoadLocal', 'buttonDownload', 'listSector17',
            'listSector33', 'listSize', 'listMarket', 'buttonClearFilters', 'buttonPreview',
            'editManualCsv', 'buttonBrowseManual', 'editOutputCsv', 'buttonSaveCsv',
            'textLog', 'labelCount', 'tablePreview']
        missing = set(required) - self.w.keys()
        if missing:
            raise RuntimeError(f'画面に必要な部品がありません: {sorted(missing)}')
        self.filters = [('listSector17', '17業種区分'), ('listSector33', '33業種区分'),
                        ('listSize', '規模区分'), ('listMarket', '市場・商品区分')]
        self.arrange()
        self.w['editManualCsv'].clear()
        self.w['editManualCsv'].setPlaceholderText('任意：追加する銘柄CSV')
        self.w['editOutputCsv'].setText(str(core.ROOT / 'data/jpx/universe.csv'))
        self.w['labelSourceDate'].setText('原本基準日：未読込')
        self.w['labelCount'].setText('対象：未表示')
        self.w['textLog'].setReadOnly(True)
        self.w['buttonLoadLocal'].clicked.connect(lambda: self.load(True))
        self.w['buttonDownload'].clicked.connect(lambda: self.load(False))
        self.w['buttonClearFilters'].clicked.connect(self.clear_filters)
        self.w['buttonPreview'].clicked.connect(self.preview)
        self.w['buttonBrowseManual'].clicked.connect(self.browse_manual)
        self.w['buttonBrowseOutput'].clicked.connect(self.browse_output)
        self.w['buttonSaveCsv'].clicked.connect(self.save)
        self.model = QStandardItemModel(self)
        self.w['tablePreview'].setModel(self.model)
        self.window.closeEvent = self.close_event
        self.log('「保存済みExcelを読む」または「JPXから最新データを取得」を押してください。')

    def arrange(self):
        # 元の.uiは変更せず、既存の部品を伸縮するレイアウトに配置。
        central = self.window.centralWidget()
        if 'buttonBrowseOutput' not in self.w:
            self.w['buttonBrowseOutput'] = QPushButton('参照', central)
        if central.layout() is not None:
            return
        self.window.setWindowTitle('JPX 銘柄リスト作成')
        self.window.setMaximumWidth(16777215)
        layout = QVBoxLayout(central)
        layout.addWidget(self.w['labelSourceDate'])
        buttons = QHBoxLayout()
        for name in ['buttonLoadLocal', 'buttonDownload']:
            buttons.addWidget(self.w[name])
        buttons.addStretch()
        layout.addLayout(buttons)
        filters = QHBoxLayout()
        for name, title in self.filters:
            box = QGroupBox(title)
            inner = QVBoxLayout(box)
            inner.addWidget(self.w[name])
            filters.addWidget(box)
        layout.addLayout(filters, 2)
        layout.addWidget(QLabel('同じ区分内はOR、異なる区分間はAND。未選択は制限なし。'))
        buttons = QHBoxLayout()
        for name in ['buttonClearFilters', 'buttonPreview']:
            buttons.addWidget(self.w[name])
        buttons.addStretch()
        layout.addLayout(buttons)
        form = QFormLayout()
        for title, edit, button in [('追加CSV', 'editManualCsv', 'buttonBrowseManual'),
                                    ('保存先', 'editOutputCsv', 'buttonBrowseOutput')]:
            row = QHBoxLayout()
            row.addWidget(self.w[edit], 1)
            row.addWidget(self.w[button])
            form.addRow(title, row)
        layout.addLayout(form)
        layout.addWidget(self.w['labelCount'])
        layout.addWidget(self.w['tablePreview'], 3)
        layout.addWidget(self.w['buttonSaveCsv'])
        layout.addWidget(QLabel('処理状況'))
        layout.addWidget(self.w['textLog'], 1)

    def log(self, text):
        self.w['textLog'].appendPlainText(text)

    def error(self, text):
        self.log('エラー：' + text)
        QMessageBox.warning(self.window, '処理できませんでした', text)

    def load(self, offline):
        if self.thread is not None:
            return
        self.log('保存済みExcelを読み込み中…' if offline else 'JPXから取得中…')
        self.window.centralWidget().setEnabled(False)
        self.thread = QThread(self)
        self.worker = Loader(self.cache, offline)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.succeeded.connect(self.loaded)
        self.worker.failed.connect(self.error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.load_finished)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def loaded(self, master):
        self.master = master
        for name, column in self.filters:
            widget = self.w[name]
            old = set(self.checked(name))
            widget.clear()
            for value in sorted(master[column].unique()):
                item = QListWidgetItem(value)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if value in old else Qt.CheckState.Unchecked)
                widget.addItem(item)
        self.w['labelSourceDate'].setText(f'原本基準日：{master["日付"].max()} ／ {len(master):,}銘柄')
        self.model.clear()
        self.w['labelCount'].setText('対象：条件を選んで表示してください')
        self.log('読込完了。5桁の種類株式等は原本に保持し、CSV変換対象から除外します。')

    def load_finished(self):
        self.thread = None
        self.worker = None
        self.window.centralWidget().setEnabled(True)

    def checked(self, name):
        widget = self.w[name]
        return [widget.item(i).text() for i in range(widget.count())
                if widget.item(i).checkState() == Qt.CheckState.Checked]

    def clear_filters(self):
        for name, _ in self.filters:
            widget = self.w[name]
            for i in range(widget.count()):
                widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def result(self):
        if self.master is None:
            raise ValueError('先にExcelを読み込んでください')
        result = core.select(self.master, *(self.checked(name) for name, _ in self.filters))
        manual = self.w['editManualCsv'].text().strip()
        return core.merge_manual(result, [Path(manual)] if manual else [], self.master)

    def show_result(self, result):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(core.OUTPUT)
        for row in result.itertuples(index=False, name=None):
            items = [QStandardItem(str(value)) for value in row]
            for item in items:
                item.setEditable(False)
            self.model.appendRow(items)
        self.w['tablePreview'].resizeColumnsToContents()
        self.w['labelCount'].setText(f'対象：{len(result):,}銘柄')

    def preview(self):
        try:
            self.show_result(self.result())
            self.log('現在の条件・追加CSVで対象を表示しました。保存時も最新の条件で再計算します。')
        except Exception as exc:
            self.error(str(exc))

    def browse_manual(self):
        path, _ = QFileDialog.getOpenFileName(self.window, '追加CSVを選択', str(self.cache.parent), 'CSV (*.csv)')
        if path:
            self.w['editManualCsv'].setText(path)

    def browse_output(self):
        path, _ = QFileDialog.getSaveFileName(self.window, 'CSVの保存先', self.w['editOutputCsv'].text(), 'CSV (*.csv)')
        if path:
            self.w['editOutputCsv'].setText(path)

    def save(self):
        try:
            result = self.result()
            if result.empty:
                raise ValueError('対象が0件のため保存しません。既存CSVは保持します。')
            text = self.w['editOutputCsv'].text().strip()
            if not text:
                raise ValueError('保存先を指定してください')
            output = Path(text)
            manual = self.w['editManualCsv'].text().strip()
            if output.suffix.lower() != '.csv' or output.resolve() in [self.cache.resolve(), Path(manual).resolve()]:
                raise ValueError('原本・追加CSVとは異なる.csvファイルを指定してください')
            if output.exists() and QMessageBox.question(self.window, '上書き確認', f'{output}\nを上書きしますか？') != QMessageBox.StandardButton.Yes:
                return
            core.atomic_write(output, result.to_csv(index=False).encode('utf-8-sig'))
            self.show_result(result)
            self.log(f'保存しました：{output} ／ {len(result):,}銘柄')
        except Exception as exc:
            self.error(str(exc))

    def close_event(self, event):
        if self.thread is not None:
            self.log('取得・読込の終了後に画面を閉じてください。')
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    controller = Controller()
    controller.window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
