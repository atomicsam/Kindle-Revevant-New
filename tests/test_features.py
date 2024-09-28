import pytest

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
    QStatusBar,
    QToolButton,
    QMenu,
    QWidgetAction,
)

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
import ui_kindlerevenant

@pytest.fixture
def getApp(qtbot):
    test_ui = ui_kindlerevenant.Ui_KindleRevenant()
    qtbot.addWidget(test_ui)

    return test_ui

def testDBConnectionClosedAfterStarup(getApp):
    assert not hasattr(getApp, 'dbCon')

def testOpenDatabase(getApp):
    getApp.openDatabase()
    assert getApp.dbCon.connectionName() in QSqlDatabase.connectionNames()

def testDatabaseClose(getApp):
    getApp.openDatabase()
    getApp.closeDatabase()
    assert not hasattr(getApp, 'dbCon')