# this Python file uses the following encoding: utf-8
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
import sys
import requests
import json

# only works for windows
# find alternatives for linux & macos
if sys.platform == "win32":
    import win32api
    import win32file

# default file locations
KINDLE_DB_LOCATION = ""
NEW_DB = "revenant.db"
ANKI_FILE_DIRECTORY = r"%APPDATA%\Anki2"
COLUMNS = ["Word", "Stem", "Category", "Date", "Frequency", "Definition"]

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

        self.dbCon = None

        layout = QVBoxLayout()
        buttonLayout = QHBoxLayout()

        createDisplayTable(self, layout)

        print(os.path.exists(os.path.join(pathlib.Path().resolve(), NEW_DB)))
        print(os.path.join(pathlib.Path().resolve(), NEW_DB))
        print(os.path.isfile(NEW_DB))

        if (os.path.exists(NEW_DB)):
            displayTable(self)
        showButtons(self, buttonLayout)
        kindleConnectedLabel = self._ToolBar()

        layout.addLayout(buttonLayout)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        print(os.path.isfile(NEW_DB))
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
            mergeDatabases(self)
            displayTable(self)
        elif KINDLE_DB_LOCATION:
            print(os.path.isfile(NEW_DB))
            mergeDatabases(self)
            displayTable(self)
        else:
            QMessageBox().warning(
                None,
                "Warning",
                "Please ensure the kindle is connected.\nAlternatively you can specify the database location manually."
            )

    def exportClicked(self):
        print(pathlib.Path().resolve().__str__())
        exportLocation = QFileDialog.getSaveFileName(self, "Export DB Location",
                                                  pathlib.Path().resolve().__str__(),
                                                  'SQLite DB (*.db)')[0]
        # exportDatabase(exportLocation)

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

    def double_clicked_cell(self):
        print("Double clicked cell")

def mergeDatabases(self):
    #  a copy of the existing kindle vocab.db if revenant.db doesn't exist
    print("The kindle location is " + KINDLE_DB_LOCATION + str(os.path.isfile(KINDLE_DB_LOCATION)))
    if not KINDLE_DB_LOCATION:
        QMessageBox.warning(
            None,
            "Error",
            "The Kindle DB was not found or it's location has not been specified."
        )
    elif not os.path.isfile(KINDLE_DB_LOCATION):
        QMessageBox.warning(
            None,
            "Error",
            f"The specified kindle db location {KINDLE_DB_LOCATION} does not exist"
        )
    elif not NEW_DB:
        QMessageBox.warning(
            None,
            "Error",
            f"The export location has not been set"
        )
    elif not os.path.isfile(NEW_DB):
        shutil.copyfile(KINDLE_DB_LOCATION, NEW_DB)
        self.dbCon = openDatabase()

        createNewColumns()

        closeDatabase(self)

        numWords = getNumberRows(self)

        QMessageBox.information(
            None,
            "Information",
            f"A new Kindle Revenant DB has been created at {NEW_DB}.\n{numWords} words were successfully imported."
        )
    else:
        # if both files exist then merge the tables from the old & new database together
        currentWords = getNumberRows(self)
        copyTables(NEW_DB)
        newNumberWords = getNumberRows(self)
        numWords = newNumberWords - currentWords

        QMessageBox.information(
            None,
            "Information",
            f"{numWords} words were successfully imported from the following location:\n{KINDLE_DB_LOCATION}"
        )

def copyTables(dbToCopy):
    db = sqlite3.connect(dbToCopy)
    db_cursor = db.cursor()

    db_cursor.execute(f"ATTACH DATABASE '{KINDLE_DB_LOCATION}' as 'Y'")

    tables_to_copy = ["BOOK_INFO", "DICT_INFO", "LOOKUPS", "METADATA", "VERSION"]
    for table in tables_to_copy:
        db_cursor.execute(f"INSERT OR IGNORE INTO {table} SELECT * FROM Y.{table};")
    db_cursor.execute(f"INSERT OR IGNORE INTO WORDS(id, word, stem, lang, category, timestamp, profileid) SELECT * FROM Y.WORDS;")

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
    self.dbCon = openDatabase()

    query = QSqlQuery("""SELECT word_key, stem, category, WORDS.timestamp, COUNT(word_key) AS frequency, WORDS.definition
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
        self.view.setItem(rows, 5, QTableWidgetItem(query.value(5)))
    
    query.finish()
    closeDatabase(self)

    self.view.resizeColumnsToContents()
    header = self.view.horizontalHeader()
    for i in range(len(COLUMNS)-1):
        header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
    header.setSectionResizeMode(len(COLUMNS)-1, QHeaderView.ResizeMode.Stretch)


def createDisplayTable(self, layout):
    self.view = QTableWidget()

    self.view.setColumnCount(len(COLUMNS))
    self.view.verticalHeader().setVisible(False)
    self.view.setHorizontalHeaderLabels(COLUMNS)
    self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
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

def getNumberRows(self):
    if not os.path.isfile(NEW_DB):
        return 0

    self.dbCon = openDatabase()

    count_query = QSqlQuery("SELECT COUNT(word) FROM WORDS")
    count_query.next()
    currentWords = count_query.value(0)
    closeDatabase(self)

    return currentWords

def exportDatabase(location):
    db = sqlite3.connect(NEW_DB)
    db_cursor = db.cursor()

    db_cursor.execute("SELECT  FROM WORDS")

    tables_to_copy = {"BOOK_INFO", "DICT_INFO", "LOOKUPS", "METADATA", "VERSION", "WORDS"}
    for table in tables_to_copy:
        db_cursor.execute(f"INSERT OR IGNORE INTO {table} SELECT * FROM Y.{table};")

    db.commit()
    db.close()

def closeDatabase(self):
    self.dbCon.close()
    del self.dbCon
    QSqlDatabase.removeDatabase(QSqlDatabase.database().connectionName())

def createNewColumns():
    if not QSqlQuery("ALTER TABLE WORDS ADD COLUMN definition TEXT;"):
        print("definition column already exists")
    if not QSqlQuery("ALTER TABLE WORDS ADD COLUMN example TEXT;"):
        print("example column already exists")
    if not QSqlQuery("ALTER TABLE WORDS ADD COLUMN synonyms TEXT;"):
        print("synonyms column already exists")
    if not QSqlQuery("ALTER TABLE WORDS ADD COLUMN antonyms TEXT;"):
        print("antonyms column already exists")
    if not QSqlQuery("ALTER TABLE WORDS ADD COLUMN pronunciation TEXT;"):
        print("pronunciation column already exists")
    if not QSqlQuery("ALTER TABLE WORDS ADD COLUMN image TEXT;"):
        print("image column already exists")

def scrapeWordDefinition(word):
    response = requests.get("https://api.dictionaryapi.dev/api/v2/entries/en/" + word)
    response_text = json.loads(response.text)
    
    if type(response_text) != list:
        print("The requested word could not be found in the dictionary")

    listOfDefinitions = ""
    for word in response_text[0]["meanings"]:
        listOfDefinitions += word["partOfSpeech"] + "\n"
        for i, definition in enumerate(word["definitions"]):
            listOfDefinitions += (str(i+1) + ". " + definition['definition'] + "\n")
        listOfDefinitions += "\n"
    
    # remove the newline character from the end of the string
    return listOfDefinitions[:-1]


app = QApplication(sys.argv)
w = Ui_KindleRevenant()
w.show()
app.shutdown()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = Ui_KindleRevenant()
    widget.show()
    sys.exit(app.exec())