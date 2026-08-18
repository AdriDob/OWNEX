"""Reports — native PySide6 view.

Displays generated reports with:
- Reports list table (id, title, platform, created, status, actions)
- Report preview pane (read-only)
- Generate new report action
- Export reports action
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop.native.services.mission import MissionControlData, get_mission
from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView

logger = logging.getLogger("ownex.native.views.reports")


class ReportsView(BaseView):
    SECTION = "reports"
    """Reports dashboard — generated reports list + preview."""

    def __init__(self, mission: MissionControlData | None = None, parent: QWidget | None = None) -> None:
        super().__init__(
            mission=mission,
            section="reports",
            label="Reports",
            icon="report",
            parent=parent,
        )

        # Layout principal: lista + panel de vista previa
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(8)

        # --- Lista de reports ---
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["ID", "Title", "Platform", "Created", "Status"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setFont(QFont("Inter", 8))
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

        main.addWidget(self._table, 1)

        # --- Panel de vista previa ---
        preview = QFrame()
        preview.setObjectName("section-frame")
        pl = QVBoxLayout(preview)
        pl.setContentsMargins(8, 8, 8, 8)
        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)
        self._preview_text.setFont(QFont("Inter", 9))
        self._preview_text.setPlaceholderText("Select a report to preview...")
        pl.addWidget(self._preview_text)

        main.addWidget(preview, 0)

        # --- Barra de acciones ---
        actions = QFrame()
        al = QHBoxLayout(actions)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(6)

        self._generate_btn = QPushButton("Generate Report")
        self._generate_btn.setFont(QFont("Inter", 9))
        self._generate_btn.clicked.connect(self._on_generate)

        self._export_btn = QPushButton("Export")
        self._export_btn.setFont(QFont("Inter", 9))
        self._export_btn.clicked.connect(self._on_export)

        al.addWidget(self._generate_btn)
        al.addStretch()
        al.addWidget(self._export_btn)
        main.addWidget(actions, 0)

        # Aplicar tema
        self.apply_theme()

    # -- Data loading (real data from the mission service) --------------
    def refresh(self) -> None:
        mission = getattr(self, "mission", None) or get_mission()
        try:
            reports = mission.get_reports(limit=50)
        except Exception as exc:  # noqa: BLE001
            logger.warning("reports refresh failed: %s", exc)
            reports = []
        self._table.setRowCount(max(1, len(reports)))
        if not reports:
            item = QTableWidgetItem(
                "No reports yet — generate one from a confirmed finding (backend service required)."
            )
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(0, 0, item)
            return
        for row, r in enumerate(reports):
            self._table.setItem(row, 0, QTableWidgetItem(str(r.get("id", ""))))
            self._table.setItem(row, 1, QTableWidgetItem(str(r.get("title", ""))))
            self._table.setItem(row, 2, QTableWidgetItem(str(r.get("platform", ""))))
            self._table.setItem(row, 3, QTableWidgetItem(str(r.get("created_at", ""))))
            self._table.setItem(row, 4, QTableWidgetItem(str(r.get("status", ""))))

    def _selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0 or row >= self._table.rowCount():
            return None
        item = self._table.item(row, 0)
        if item is None:
            return None
        try:
            return int(item.text())
        except ValueError:
            return None

    def _on_selection_changed(self) -> None:
        report_id = self._selected_id()
        if report_id is None:
            return
        mission = getattr(self, "mission", None) or get_mission()
        try:
            report = mission.get_report(report_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("report preview failed: %s", exc)
            report = None
        if report is None:
            self._preview_text.setPlainText("Report not available.")
            return
        content = report.get("content") or ""
        self._preview_text.setPlainText(
            f"#{report.get('id')} {report.get('title', '')}\n"
            f"Platform: {report.get('platform', '')}  Status: {report.get('status', '')}\n\n"
            f"{content}"
        )

    def _on_generate(self) -> None:
        mission = getattr(self, "mission", None) or get_mission()
        try:
            findings = [f for f in mission.get_findings() if str(f.get("status", "")) == "confirmed"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("reports generate scan failed: %s", exc)
            findings = []
        if not findings:
            QMessageBox.information(self, "Generate Report", "No confirmed findings yet — run the pipeline first.")
            return
        ids = [f["id"] for f in findings[:20] if f.get("id") is not None]
        try:
            created = mission.create_report(ids)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Generate Report", f"Could not generate report: {exc}")
            return
        if created is None:
            QMessageBox.warning(self, "Generate Report", "The backend did not produce a report.")
            return
        self.refresh()
        QMessageBox.information(self, "Generate Report", f"Report #{created.get('id')} generated.")

    def _on_export(self) -> None:
        report_id = self._selected_id()
        if report_id is None:
            QMessageBox.information(self, "Export", "Select a report row first.")
            return
        mission = getattr(self, "mission", None) or get_mission()
        try:
            path = mission.export_report(report_id, fmt="markdown")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Export", f"Could not export report: {exc}")
            return
        if path is None:
            QMessageBox.warning(self, "Export", "The backend did not return a file.")
            return
        QMessageBox.information(self, "Export", f"Report exported to:\n{path}")

    # -- Helpers de estilo --
    def apply_theme(self) -> None:
        theme = get_theme()
        ws = "background-color: " + theme.background + ";"
        sf = "background-color: " + theme.surface + ";"
        st = "border: 1px solid " + theme.stroke + ";"
        self.setStyleSheet(
            "QWidget {" + ws + "}QFrame {" + sf + "border-radius: 6px;" + st + "}QLabel {" + theme.text + ";}"
        )
