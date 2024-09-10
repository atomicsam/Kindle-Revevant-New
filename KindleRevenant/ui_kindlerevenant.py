# This Python file uses the following encoding: utf-8
import sys

from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QTableWidget,
    QApplication,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QHeaderView,
    QFileDialog,
    QAbstractItemView,
    QToolBar,
    QLabel,
    QMessageBox,
)
from PySide6.QtCore import QTimer

import os
import shutil
from datetime import datetime
import sqlite3
import pathlib

# only works for windows
# find alternatives for linux & macos
import win32api
import win32file

# default file locations
KINDLE_DB_LOCATION = ""
NEW_DB = "revenant.db"
EXPORT_LOCATION = ""
ANKI_FILE_DIRECTORY = r"%APPDATA%\Anki2"

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from ui_form import Ui_Ui_KindleRevenant

class Ui_KindleRevenant(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Ui_KindleRevenant()
        self.ui.setupUi(self)

        self.setWindowTitle("My App")
        self.setMinimumSize(500, 500)

        layout = QVBoxLayout()
        buttonLayout = QHBoxLayout()

        createDisplayTable(self, layout)
        print(os.path.exists(os.path.join(pathlib.Path().resolve(), NEW_DB)))
        print(os.path.join(pathlib.Path().resolve(), NEW_DB))
        if os.path.exists(os.path.join(pathlib.Path().resolve(), NEW_DB)):
            displayTable(self)
        showButtons(self, buttonLayout)
        kindleConnectedLabel = self._ToolBar()

        layout.addLayout(buttonLayout)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.timer = QTimer()
        self.timer.timeout.connect(lambda connectedLabel=kindleConnectedLabel: self.changeKindleConnectedMessage(connectedLabel))
        self.timer.start(1000)

    def selectDbLocationClicked(self):
        global KINDLE_DB_LOCATION
        KINDLE_DB_LOCATION = QFileDialog.getOpenFileName(self, "Open Kindle DB Location",
                                                  r'C:\Users\Sam\Documents\Summer Projects\PyQt\practiceapp',
                                                  'SQLite DB (*.db)')[0]

    def syncKindleClicked(self):
        global KINDLE_DB_LOCATION
        if not KINDLE_DB_LOCATION and kindleConnected()[0]:
            KINDLE_DB_LOCATION = getKindleDBPath()
            mergeDatabases()
            displayTable(self)
        elif KINDLE_DB_LOCATION:
            print(KINDLE_DB_LOCATION)
            mergeDatabases()
            displayTable(self)
        else:
            QMessageBox().warning(
                None,
                "Warning",
                "Please ensure the kindle is connected.\nAlternatively you can specify the database location manually."
            )

    def exportClicked(self):
        global EXPORT_LOCATION
        EXPORT_LOCATION = QFileDialog.getSaveFileName(self, "Export DB Location",
                                                  r'C:\Users\Sam\Documents\Summer Projects\PyQt\practiceapp',
                                                  'SQLite DB (*.db)')[0]

    def ankiLocationClicked(self):
        global ANKI_FILE_DIRECTORY
        ANKI_FILE_DIRECTORY = QFileDialog.getOpenFileName(self, "Open Kindle DB Location",
                                                  os.path.expandvars(ANKI_FILE_DIRECTORY),
                                                  'SQLite DB (*.db)')[0]

    def changeKindleConnectedMessage(self, kindleConnectedLabel):
        if kindleConnected()[0]:
            kindleConnectedLabel.setText("Kindle Connected")
            kindleConnectedLabel.setStyleSheet("font-weight: bold; text-align:left; color: green;")
        else:
            kindleConnectedLabel.setText("Kindle Disconnected")
            kindleConnectedLabel.setStyleSheet("font-weight: bold; text-align:left; color: grey;")


    def _ToolBar(self):
        if kindleConnected()[0]:
            kindleConnectedLabel = QLabel("Kindle Connected")
            kindleConnectedLabel.setStyleSheet("font-weight: bold; text-align:left; color: green;")
        else:
            kindleConnectedLabel = QLabel("Kindle Disconnected")
            kindleConnectedLabel.setStyleSheet("font-weight: bold; text-align:left; color: grey;")

        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        file_action = QAction("Options", self)
        file_action.setStatusTip("Options Menu")
        file_action.triggered.connect(self.onMyToolBarButtonClick)

        toolbar.addAction(file_action)
        toolbar.addWidget(kindleConnectedLabel)

        return kindleConnectedLabel

    def onMyToolBarButtonClick(self, s):
        print("click", s)

def mergeDatabases():
    #  a copy of the existing kindle vocab.db if revenant.db doesn't exist
    print("The kindle location is " + KINDLE_DB_LOCATION + str(os.path.isfile(KINDLE_DB_LOCATION)))
    if not KINDLE_DB_LOCATION:
        print("Kindle DB Location not set.")
    elif not os.path.isfile(KINDLE_DB_LOCATION):
        print(f"The specified kindle db location {KINDLE_DB_LOCATION} does not exist")
    elif not NEW_DB:
        print(f"The export location has not been set")
    elif not os.path.isfile(NEW_DB):
        shutil.copyfile(KINDLE_DB_LOCATION, NEW_DB)
        print("file copied")
    else:
        # if both files exist then merge the tables from the old & new database together
        copyTables(NEW_DB)

        QMessageBox.information(
            None,
            "Information",
            f"Vocabulary was successfully imported from the following location:\n{KINDLE_DB_LOCATION}"
        )

def copyTables(database_to_be_copied):
    db = sqlite3.connect(database_to_be_copied)
    db_cursor = db.cursor()

    db_cursor.execute(f"ATTACH DATABASE '{KINDLE_DB_LOCATION}' as 'Y'")

    tables_to_copy = {"BOOK_INFO", "DICT_INFO", "LOOKUPS", "METADATA", "VERSION", "WORDS"}
    for table in tables_to_copy:
        db_cursor.execute(f"INSERT OR IGNORE INTO {table} SELECT * FROM Y.{table};")

    db.commit()
    db.close()

def openDatabase():
    con = QSqlDatabase.addDatabase("QSQLITE")
    con.setDatabaseName(NEW_DB)

    if not con.open():
        QMessageBox.critical(
            None,
            "App Name - Error !"
            "Database Error: %s" % con.lastError().databaseText(),
        )
        sys.exit(1)

    return con

def displayTable(self):
    openDatabase()

    query = QSqlQuery("""SELECT word_key, stem, category, WORDS.timestamp, COUNT(word_key) AS frequency
                        FROM LOOKUPS
                        JOIN WORDS WHERE word_key == WORDS.id
                        GROUP BY word_key
                        ORDER BY COUNT(word_key) DESC
                        """
                    )

    category_text = {"0": "Learning", "1": "Mastered"}

    while query.next():
        rows = self.view.rowCount()
        self. view.setRowCount(rows + 1)
        self.view.setItem(rows, 0, QTableWidgetItem(formatWordKey(query.value(0))))
        self.view.setItem(rows, 1, QTableWidgetItem(query.value(1)))
        self.view.setItem(rows, 2, QTableWidgetItem(category_text[str(query.value(2))]))
        self.view.setItem(rows, 3, QTableWidgetItem(str(datetime.fromtimestamp(int(query.value(3)/1000)))[:10]))
        self.view.setItem(rows, 4, QTableWidgetItem(str(query.value(4))))
    self.view.resizeColumnsToContents()

    header = self.view.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
    header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
    header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)


def createDisplayTable(self, layout):
    self.view = QTableWidget()

    self.view.setColumnCount(5)
    self.view.verticalHeader().setVisible(False)
    self.view.setHorizontalHeaderLabels(["Word", "Stem", "Category", "Date", "Frequency"])
    self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

    layout.addWidget(self.view)

def formatWordKey(word):
    return word[word.find(":")+1:]

def kindleConnected():
    if sys.platform == "win32":
        try:
            drives = win32api.GetLogicalDriveStrings()
            # iterates through each drive letter
            for i in range(len(drives)//4):
                # checks if drive letter is called 'Kindle'
                currentDrive = drives[i*4:(i+1)*4]
                if win32api.GetVolumeInformation(currentDrive)[0] == "Kindle" and win32file.GetDriveType(currentDrive) == win32file.DRIVE_REMOVABLE:
                    return True, currentDrive[0]
            return False, ""
        except:
            print("Error! Can't Access Windows Drive Information")
            return False, ""
    return False, ""

def showButtons(self, layout):
    db_location_button = QPushButton("Select DB Location")
    db_location_button.clicked.connect(self.selectDbLocationClicked)
    layout.addWidget(db_location_button)

    anki_location_button = QPushButton("Select Anki Location")
    anki_location_button.clicked.connect(self.ankiLocationClicked)
    layout.addWidget(anki_location_button)

    sync_with_kindle_button = QPushButton("Sync with Kindle")
    sync_with_kindle_button.clicked.connect(self.syncKindleClicked)
    layout.addWidget(sync_with_kindle_button)

    export_button = QPushButton("Export")
    export_button.clicked.connect(self.exportClicked)
    layout.addWidget(export_button)

def getKindleDBPath():
    return os.path.join(f"{kindleConnected()[1][0]}:", "system", "vocabulary", "vocab.db")

app = QApplication(sys.argv)
w = Ui_KindleRevenant()
w.show()
app.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = Ui_KindleRevenant()
    widget.show()
    sys.exit(app.exec())
