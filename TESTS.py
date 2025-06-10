import sys
import sqlite3
import csv
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox, QComboBox, QFileDialog
)
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtCore import Qt
from openpyxl import Workbook

DB_PATH = "example.db"

# ---------------- БАЗА ДАННЫХ ---------------- #
def initialize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS dogs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, breed TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS cats (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT)")
    conn.commit()
    conn.close()


# ---------------- ТЁМНАЯ ТЕМА ---------------- #
def apply_dark_theme(app):
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#FFFFFF"))  # Белый фон
    palette.setColor(QPalette.WindowText, QColor("#000000"))  # Чёрный текст
    palette.setColor(QPalette.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.AlternateBase, QColor("#F5F5F5"))
    palette.setColor(QPalette.Text, QColor("#000000"))  # Чёрный текст в таблицах
    palette.setColor(QPalette.Button, QColor("#F0F0F0"))
    palette.setColor(QPalette.ButtonText, QColor("#000000"))
    app.setPalette(palette)


# ---------------- ИНТЕРФЕЙС ---------------- #
class DatabaseGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📋 SQLite Менеджер")
        self.setGeometry(200, 100, 950, 600)
        self.setFont(QFont("Segoe UI", 10))
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.current_table = "users"
        self.init_ui()
        self.run_select_query()

    def init_ui(self):
        top_layout = QHBoxLayout()

        self.table_selector = QComboBox()
        self.table_selector.addItems(["👤 Users", "🐶 Dogs", "🐱 Cats"])
        self.table_selector.currentTextChanged.connect(self.update_query)

        self.query_input = QLineEdit("SELECT * FROM users")
        self.query_button = QPushButton("🔍 Показать")
        self.query_button.clicked.connect(self.run_select_query)

        top_layout.addWidget(QLabel("📁 Таблица:"))
        top_layout.addWidget(self.table_selector)
        top_layout.addWidget(self.query_input)
        top_layout.addWidget(self.query_button)

        self.layout.addLayout(top_layout)

        # КНОПКИ
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("➕ Добавить")
        self.save_btn = QPushButton("💾 Сохранить изменения")
        self.csv_btn = QPushButton("📁 Экспорт в CSV")
        self.excel_btn = QPushButton("📊 Экспорт в Excel")

        self.add_btn.clicked.connect(self.add_record)
        self.save_btn.clicked.connect(self.save_edits)
        self.csv_btn.clicked.connect(self.export_csv)
        self.excel_btn.clicked.connect(self.export_excel)

        for btn in [self.add_btn, self.save_btn, self.csv_btn, self.excel_btn]:
            btn.setStyleSheet("padding: 6px;")
            btn_layout.addWidget(btn)

        self.layout.addLayout(btn_layout)

        # ТАБЛИЦА
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.SelectedClicked)
        self.layout.addWidget(self.table)

    def update_query(self, selection):
        self.current_table = selection.split()[1].lower()
        self.query_input.setText(f"SELECT * FROM {self.current_table}")
        self.run_select_query()

    def run_select_query(self):
        query = self.query_input.text()
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            self.populate_table(rows)
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def populate_table(self, rows):
        if not rows:
            # Если нет строк, получаем структуру таблицы
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns_info = cursor.fetchall()
            conn.close()

            headers = [col[1] for col in columns_info]  # Названия колонок

            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setRowCount(0)  # Нет данных, но заголовки есть
            return

        # Если строки есть — обычная обработка
        headers = rows[0].keys()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, column in enumerate(headers):
                self.table.setItem(row_index, col_index, QTableWidgetItem(str(row[column])))

    def add_record(self):
        col_count = self.table.columnCount()
        self.table.insertRow(self.table.rowCount())
        for col in range(col_count):
            self.table.setItem(self.table.rowCount() - 1, col, QTableWidgetItem(""))

    def save_edits(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]

            cursor.execute(f"DELETE FROM {self.current_table}")

            for row in range(self.table.rowCount()):
                values = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    values.append(item.text() if item else "")
                placeholders = ", ".join("?" for _ in values)
                cursor.execute(f"INSERT INTO {self.current_table} ({', '.join(headers)}) VALUES ({placeholders})", values)

            conn.commit()
            conn.close()
            QMessageBox.information(self, "Успех", "Данные успешно сохранены.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", str(e))

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить как CSV", f"{self.current_table}.csv", "CSV Files (*.csv)")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
                writer.writerow(headers)
                for row in range(self.table.rowCount()):
                    data = [self.table.item(row, col).text() if self.table.item(row, col) else "" for col in range(self.table.columnCount())]
                    writer.writerow(data)
            QMessageBox.information(self, "Готово", "CSV успешно сохранён.")

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить как Excel", f"{self.current_table}.xlsx", "Excel Files (*.xlsx)")
        if path:
            wb = Workbook()
            ws = wb.active
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            ws.append(headers)
            for row in range(self.table.rowCount()):
                data = [self.table.item(row, col).text() if self.table.item(row, col) else "" for col in range(self.table.columnCount())]
                ws.append(data)
            wb.save(path)
            QMessageBox.information(self, "Готово", "Excel успешно сохранён.")


# ---------------- ЗАПУСК ---------------- #
if __name__ == "__main__":
    initialize_database()
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    gui = DatabaseGUI()
    gui.show()
    sys.exit(app.exec_())
