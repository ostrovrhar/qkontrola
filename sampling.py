import math
import os
import random
from datetime import datetime

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateTransformContext,
    QgsFeatureRequest,
    QgsMessageLog,
    QgsProject,
    QgsTask,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QSettings, QVariant

SAMPLE_SIZE_TABLE = [
    (1, 8, None),
    (9, 50, 8),
    (51, 90, 13),
    (91, 150, 20),
    (151, 280, 32),
    (281, 400, 50),
    (401, 500, 60),
    (501, 1200, 80),
    (1201, 3200, 125),
    (3201, 10000, 200),
    (10001, 35000, 315),
    (35001, 150000, 500),
    (150001, 500000, 800),
    (500001, float("inf"), 1250),
]


def lookup_sample_size(population_size):
    for lo, hi, n in SAMPLE_SIZE_TABLE:
        if lo <= population_size <= hi:
            if n is None:
                return population_size
            return n
    return 1250


def _sanitize_layer_name(name):
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
    return safe.strip("_") or "sloj"


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class SamplingTask(QgsTask):
    def __init__(
        self,
        layer,
        output_dir,
        use_stratification=False,
        strata_field=None,
        use_spatial_distribution=False,
    ):
        super().__init__("Statisti\u010dno vzor\u010denje", QgsTask.Flag.CanCancel)
        self.layer = layer
        self.output_dir = output_dir
        self.use_stratification = use_stratification
        self.strata_field = strata_field
        self.use_spatial_distribution = use_spatial_distribution
        self.result_data = None
        self.error_message = ""

    def run(self):
        try:
            total = self.layer.featureCount()
            if total is None or total < 0:
                total = 0
            sample_size = lookup_sample_size(total)
            if sample_size >= total:
                sample_size = total

            self.setProgress(5)

            all_fids = []
            strata_values = {}
            grid_cells = {}

            extent = None
            n_grid_cells = 0
            if self.use_spatial_distribution:
                extent = self.layer.extent()
                if extent and not extent.isNull():
                    n_grid_cells = min(max(sample_size * 3, 10), total)

            request = QgsFeatureRequest()
            attr_indices = []
            if self.use_stratification and self.strata_field:
                idx = self.layer.fields().lookupField(self.strata_field)
                if idx >= 0:
                    attr_indices.append(idx)
            if attr_indices:
                request.setSubsetOfAttributes(attr_indices)
            if not self.use_spatial_distribution:
                try:
                    request.setFlags(QgsFeatureRequest.Flag.NoGeometry)
                except Exception:
                    pass

            processed = 0
            for feature in self.layer.getFeatures(request):
                if self.isCanceled():
                    self.error_message = "Prekinjeno."
                    return False

                fid = feature.id()
                all_fids.append(fid)

                if self.use_stratification and self.strata_field:
                    raw = feature[self.strata_field]
                    strata_values[fid] = str(raw) if raw is not None else "NULL"

                if self.use_spatial_distribution:
                    grid_cells[fid] = self._compute_cell(
                        feature.geometry(), extent, n_grid_cells
                    )

                processed += 1
                if processed % 500 == 0:
                    self.setProgress(
                        min(20.0, 5.0 + (processed / max(1, total)) * 15.0)
                    )

            self.setProgress(25)

            if self.isCanceled():
                self.error_message = "Prekinjeno."
                return False

            if self.use_stratification and self.strata_field:
                selected_fids = self._stratified_sample(
                    all_fids, sample_size, strata_values, grid_cells
                )
                if selected_fids is None:
                    self.error_message = "Prekinjeno."
                    return False
            else:
                selected_fids = self._simple_sample(all_fids, sample_size, grid_cells)

            self.setProgress(50)

            if self.isCanceled():
                self.error_message = "Prekinjeno."
                return False

            ts = _timestamp()
            layer_name = _sanitize_layer_name(self.layer.name())
            output_path = os.path.join(
                self.output_dir, f"vzorec_{layer_name}_{ts}.gpkg"
            )
            report_path = os.path.join(
                self.output_dir, f"porocilo_vzorcenje_{layer_name}_{ts}.html"
            )

            self._create_output_layer(selected_fids, output_path)

            self.setProgress(70)

            if self.isCanceled():
                self.error_message = "Prekinjeno."
                return False

            stratum_info = {}
            if self.use_stratification and self.strata_field:
                total_by_val = {}
                for fid, val in strata_values.items():
                    total_by_val[val] = total_by_val.get(val, 0) + 1
                selected_by_val = {}
                for fid in selected_fids:
                    val = strata_values[fid]
                    selected_by_val[val] = selected_by_val.get(val, 0) + 1
                for val in sorted(total_by_val.keys()):
                    stratum_info[val] = {
                        "population": total_by_val[val],
                        "proportion": total_by_val[val] / max(1, total),
                        "sample": selected_by_val.get(val, 0),
                    }

            report_html = self._generate_report(
                total, sample_size, selected_fids, stratum_info, output_path
            )
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_html)

            self.setProgress(95)

            self.result_data = {
                "population_size": total,
                "sample_size": len(selected_fids),
                "selected_fids": selected_fids,
                "output_gpkg": output_path,
                "report_path": report_path,
                "report_html": report_html,
                "layer_name": f"{self.layer.name()}__vzorec",
                "strata_field": self.strata_field if self.use_stratification else None,
                "strata_info": stratum_info,
                "use_spatial_distribution": self.use_spatial_distribution,
            }

            self.setProgress(100)
            return True

        except Exception as exc:
            import traceback

            tb = traceback.format_exc()
            self.error_message = str(exc)
            QgsMessageLog.logMessage(
                f"Napaka pri vzor\u010denju: {exc}\n{tb}",
                "QKontrola",
                level=Qgis.Critical,
            )
            return False

    def _compute_cell(self, geom, extent, n_cells):
        if geom is None or geom.isNull() or extent is None or extent.isNull():
            return 0
        centroid = geom.centroid()
        if centroid is None or centroid.isNull():
            return 0
        pt = centroid.asPoint()

        w = extent.width()
        h = extent.height()
        if w <= 0 or h <= 0:
            return 0

        n_cols = max(1, int(math.sqrt(n_cells * (w / h))))
        n_rows = max(1, int(n_cells / n_cols))

        cell_w = w / n_cols
        cell_h = h / n_rows

        col = int((pt.x() - extent.xMinimum()) / cell_w)
        row = int((pt.y() - extent.yMinimum()) / cell_h)
        col = max(0, min(col, n_cols - 1))
        row = max(0, min(row, n_rows - 1))

        return row * n_cols + col

    def _simple_sample(self, all_fids, n, grid_cells):
        if n >= len(all_fids):
            return list(all_fids)

        if self.use_spatial_distribution and grid_cells:
            return self._spatial_spread_sample(all_fids, n, grid_cells)

        selected = random.sample(all_fids, n)
        return selected

    def _stratified_sample(self, all_fids, n, strata_values, grid_cells):
        stratum_groups = {}
        for fid in all_fids:
            val = strata_values.get(fid, "NULL")
            stratum_groups.setdefault(val, []).append(fid)

        if self.isCanceled():
            return None

        if not stratum_groups:
            return self._simple_sample(all_fids, n, grid_cells)

        total = len(all_fids)
        allocated = {}
        remaining = n
        items = sorted(stratum_groups.items(), key=lambda x: -len(x[1]))

        for val, fids_in_val in items:
            if self.isCanceled():
                return None
            raw = n * len(fids_in_val) / total
            alloc = max(1, int(round(raw)))
            alloc = min(alloc, len(fids_in_val))
            allocated[val] = alloc
            remaining -= alloc

        while remaining > 0:
            for val in [v for v, _ in items]:
                if self.isCanceled():
                    return None
                if remaining <= 0:
                    break
                available = len(stratum_groups[val]) - allocated[val]
                if available > 0:
                    allocated[val] += 1
                    remaining -= 1

        while remaining < 0:
            for val in [v for v, _ in reversed(items)]:
                if self.isCanceled():
                    return None
                if remaining >= 0:
                    break
                if allocated[val] > 1:
                    allocated[val] -= 1
                    remaining += 1

        selected = []
        for val, n_val in allocated.items():
            if self.isCanceled():
                return None
            fids_in_val = stratum_groups[val]
            if n_val <= 0:
                continue
            if self.use_spatial_distribution and grid_cells:
                cell_map = {fid: grid_cells.get(fid, 0) for fid in fids_in_val}
                val_selected = self._spatial_spread_sample(fids_in_val, n_val, cell_map)
            else:
                val_selected = random.sample(fids_in_val, min(n_val, len(fids_in_val)))
            selected.extend(val_selected)

        return selected

    def _spatial_spread_sample(self, fids, n, grid_cells):
        if n >= len(fids):
            return list(fids)

        cell_fids = {}
        for fid in fids:
            cell = grid_cells.get(fid, 0)
            cell_fids.setdefault(cell, []).append(fid)

        for cell in cell_fids:
            random.shuffle(cell_fids[cell])

        selected = []
        cells = list(cell_fids.keys())

        while len(selected) < n and cells:
            random.shuffle(cells)
            still_have = []
            for cell in cells:
                if len(selected) >= n:
                    break
                if cell_fids[cell]:
                    selected.append(cell_fids[cell].pop())
                    if cell_fids[cell]:
                        still_have.append(cell)
            cells = still_have

        if len(selected) < n:
            remaining = [f for fid_list in cell_fids.values() for f in fid_list]
            random.shuffle(remaining)
            selected.extend(remaining[: n - len(selected)])

        return selected

    def _create_output_layer(self, fids, output_path):
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

        fields = self.layer.fields()
        crs = self.layer.crs()
        geom_type = self.layer.wkbType()

        save_opts = QgsVectorFileWriter.SaveVectorOptions()
        save_opts.driverName = "GPKG"
        writer = QgsVectorFileWriter.create(
            output_path,
            fields,
            geom_type,
            crs,
            QgsCoordinateTransformContext(),
            save_opts,
        )

        if writer.hasError() or writer is None:
            QgsMessageLog.logMessage(
                f"Napaka pri ustvarjanju GPKG: {writer.errorMessage() if writer else 'unknown'}",
                "QKontrola",
            )
            return

        fid_set = set(fids)
        request = QgsFeatureRequest().setFilterFids(list(fid_set))
        feat_count = 0
        total = len(fids)

        for feature in self.layer.getFeatures(request):
            if self.isCanceled():
                break
            writer.addFeature(feature)
            feat_count += 1
            if feat_count % 500 == 0:
                self.setProgress(min(65.0, 50.0 + (feat_count / max(1, total)) * 15.0))

        del writer

        if feat_count > 0:
            layer = QgsVectorLayer(output_path, f"{self.layer.name()}__vzorec", "ogr")
            if layer and layer.isValid():
                QgsProject.instance().addMapLayer(layer)

    def _generate_report(
        self, population_size, sample_size, fids, stratum_info, output_path
    ):
        lines = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<title>Poro\u010dilo o vzor\u010denju</title>"
            "<style>"
            "body{font-family:sans-serif;max-width:800px;margin:2em auto;padding:0 1em}"
            "h1{color:#1a365d;border-bottom:2px solid #e2e8f0;padding-bottom:.5em}"
            "table{width:100%;margin:1em 0}"
            "th,td{padding:.5em;text-align:left}"
            "th{background:#f7fafc;font-weight:600}"
            ".meta{color:#4a5568;margin:.5em 0}"
            "</style></head><body>",
            "<h1>Poro\u010dilo o statisti\u010dnem vzor\u010denju</h1>",
            f"<p class='meta'>Ustvarjeno: {datetime.now().strftime('%d. %m. %Y %H:%M:%S')}</p>",
            f"<p class='meta'>Sloj: <b>{self.layer.name()}</b></p>",
            "<h2>Povzetek</h2>",
            "<table border='1' cellspacing='0' cellpadding='5'>",
            f"<tr><td>Velikost populacije</td><td style='text-align:right'>{population_size}</td></tr>",
            f"<tr><td>Velikost vzorca</td><td style='text-align:right'>{sample_size}</td></tr>",
            f"<tr><td>Dele\u017e vzor\u010denja</td><td style='text-align:right'>"
            f"{100 * sample_size / max(1, population_size):.1f}%</td></tr>",
            f"<tr><td>Metoda</td><td>"
            f"{'Stratificirano ' if self.use_stratification else 'Enostavno '}"
            f"naklju\u010dno vzor\u010denje"
            f"{' s prostorsko porazdelitvijo' if self.use_spatial_distribution else ''}"
            f"</td></tr>",
            "</table>",
        ]

        if self.use_stratification and self.strata_field and stratum_info:
            lines.append(f"<h2>Stratifikacija: {self.strata_field}</h2>")
            lines.append(
                "<table border='1' cellspacing='0' cellpadding='5'><tr>"
                "<th>Vrednost</th>"
                "<th>Populacija</th>"
                "<th>Dele\u017e</th>"
                "<th>V vzorcu</th>"
                "</tr>"
            )
            for val, info in sorted(stratum_info.items()):
                lines.append(
                    f"<tr><td>{val}</td>"
                    f"<td style='text-align:right'>{info['population']}</td>"
                    f"<td style='text-align:right'>{100 * info['proportion']:.1f}%</td>"
                    f"<td style='text-align:right'>{info['sample']}</td></tr>"
                )
            lines.append("</table>")

        lines.append("<h2>Izbrani objekti</h2>")
        lines.append(f"<p class='meta'>\u0160tevilo FID: {len(fids)}</p>")
        lines.append(
            "<details><summary>Prika\u017ei seznam FID</summary>"
            f"<p style='font-family:monospace;font-size:.9em'>{', '.join(str(f) for f in fids)}</p>"
            "</details>"
        )

        lines.append(f"<p class='meta'>Rezultat: {os.path.basename(output_path)}</p>")
        lines.append("</body></html>")

        return "\n".join(lines)


class SamplingDialog(QtWidgets.QDialog):
    def __init__(self, iface, layer, plugin_dir, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.layer = layer
        self.plugin_dir = plugin_dir
        self._task = None
        self.sampling_result = None

        self.setWindowTitle("Statisti\u010dno vzor\u010denje")
        self.setMinimumWidth(480)
        self._build_ui()
        self._update_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Layer info
        info_layout = QtWidgets.QFormLayout()
        name = self.layer.name() if self.layer else "/"
        total = self.layer.featureCount() if self.layer else 0
        info_layout.addRow("Sloj:", QtWidgets.QLabel(name))
        self.pop_label = QtWidgets.QLabel(str(total))
        info_layout.addRow("Velikost populacije v sloju:", self.pop_label)
        layout.addLayout(info_layout)

        # Stratification
        self.strat_cb = QtWidgets.QCheckBox("Stratificiran vzorec")
        layout.addWidget(self.strat_cb)

        self.strata_label = QtWidgets.QLabel("Stratifikacijski atribut:")
        self.strata_label.setEnabled(False)
        layout.addWidget(self.strata_label)

        self.strata_combo = QtWidgets.QComboBox()
        self.strata_combo.setEnabled(False)
        self._populate_strata_fields()
        layout.addWidget(self.strata_combo)

        self.strat_cb.toggled.connect(self.strata_label.setEnabled)
        self.strat_cb.toggled.connect(self.strata_combo.setEnabled)
        self.strat_cb.toggled.connect(self._update_ui)

        # Sample size preview
        self.size_label = QtWidgets.QLabel("")
        layout.addWidget(self.size_label)

        # Output directory
        dir_layout = QtWidgets.QHBoxLayout()
        dir_layout.addWidget(QtWidgets.QLabel("Izhodna mapa:"))
        self.dir_edit = QtWidgets.QLineEdit()
        self.dir_edit.setReadOnly(True)
        dir_layout.addWidget(self.dir_edit, 1)
        self.dir_btn = QtWidgets.QPushButton("Prebrskaj")
        self.dir_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(self.dir_btn)
        layout.addLayout(dir_layout)

        # Status & progress
        self.status_label = QtWidgets.QLabel("Pripravljen.")
        layout.addWidget(self.status_label)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.run_btn = QtWidgets.QPushButton("Izvedi vzor\u010denje")
        self.run_btn.clicked.connect(self._run_sampling)
        btn_layout.addWidget(self.run_btn)
        self.close_btn = QtWidgets.QPushButton("Zapri")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self._update_sample_size_preview()

    def _populate_strata_fields(self):
        self.strata_combo.clear()
        if not self.layer:
            return
        for field in self.layer.fields():
            name = field.name()
            if field.type() in (QVariant.String, QVariant.Int, QVariant.LongLong):
                self.strata_combo.addItem(name)
            elif field.type() == QVariant.Double:
                self.strata_combo.addItem(name)

    def _update_ui(self):
        self.run_btn.setEnabled(self.layer is not None)

    def _update_sample_size_preview(self):
        if not self.layer:
            self.size_label.setText("")
            return
        total = self.layer.featureCount() or 0
        n = lookup_sample_size(total)
        if n >= total:
            self.size_label.setText(f"Velikost vzorca: {n} (celotna populacija)")
        else:
            self.size_label.setText(f"Velikost vzorca: {n} od {total}")

    def _browse_dir(self):
        settings = QSettings()
        last_dir = settings.value("QKontrola/sampling_output_dir", "", type=str)
        start = os.path.dirname(last_dir) if last_dir else self.plugin_dir
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Izberi izhodno mapo", start
        )
        if path:
            self.dir_edit.setText(path)
            settings.setValue("QKontrola/sampling_output_dir", path)

    def _run_sampling(self):
        if not self.layer:
            QtWidgets.QMessageBox.warning(self, "Opozorilo", "Ni izbranega sloja.")
            return

        output_dir = self.dir_edit.text().strip()
        if not output_dir:
            QtWidgets.QMessageBox.warning(self, "Opozorilo", "Izberite izhodno mapo.")
            return

        use_strat = self.strat_cb.isChecked()
        strata_field = (
            self.strata_combo.currentText()
            if use_strat and self.strata_combo.count() > 0
            else None
        )
        use_spatial = True

        if use_strat and strata_field:
            field_index = self.layer.fields().lookupField(strata_field)
            if field_index >= 0:
                unique_vals = self.layer.uniqueValues(field_index)
                if len(unique_vals) > 100:
                    reply = QtWidgets.QMessageBox.warning(
                        self,
                        "Preve\u010d stratumov",
                        f"Stratifikacijsko polje '{strata_field}' ima "
                        f"{len(unique_vals)} unikatnih vrednosti.\n\n"
                        f"Priporo\u010dljivo je najve\u010d 100 stratumov. "
                        f"Vzor\u010denje bo zelo po\u010dasno in rezultati "
                        f"lahko niso smiselni.\n\n"
                        f"Vseeno nadaljuj?",
                        QtWidgets.QMessageBox.StandardButton.Yes
                        | QtWidgets.QMessageBox.StandardButton.No,
                        QtWidgets.QMessageBox.StandardButton.No,
                    )
                    if reply == QtWidgets.QMessageBox.StandardButton.No:
                        return

        self._task = SamplingTask(
            self.layer,
            output_dir,
            use_stratification=use_strat,
            strata_field=strata_field,
            use_spatial_distribution=use_spatial,
        )

        self._task.taskCompleted.connect(self._on_completed)
        self._task.taskTerminated.connect(self._on_terminated)
        self._task.progressChanged.connect(self._on_progress)

        self.run_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.strat_cb.setEnabled(False)
        self.strata_combo.setEnabled(False)
        self.dir_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Izvajanje vzor\u010denja ...")

        QgsApplication.taskManager().addTask(self._task)

    def _on_progress(self):
        if self._task:
            try:
                self.progress_bar.setValue(int(self._task.progress()))
            except RuntimeError:
                pass

    def _on_completed(self):
        try:
            self.run_btn.setEnabled(True)
            self.close_btn.setEnabled(True)
            self.strat_cb.setEnabled(True)
            self.strata_combo.setEnabled(self.strat_cb.isChecked())
            self.dir_btn.setEnabled(True)
            self.progress_bar.setValue(100)

            if self._task and self._task.result_data:
                rd = self._task.result_data
                self.sampling_result = rd
                self.status_label.setText(
                    f"Vzor\u010denje zaklju\u010deno. "
                    f"Izbranih {rd['sample_size']} objektov. "
                    f"Rezultat: {rd['output_gpkg']}"
                )
                QtWidgets.QMessageBox.information(
                    self,
                    "Vzor\u010denje zaklju\u010deno",
                    f"Vzor\u010denje je zaklju\u010deno.\n\n"
                    f"Izbranih objektov: {rd['sample_size']}\n"
                    f"GPKG: {rd['output_gpkg']}\n"
                    f"Poro\u010dilo: {rd['report_path']}\n\n"
                    f"Vzor\u010deni sloj ({rd['layer_name']}) je dodan med sloje "
                    f"in izbran za nadaljnjo kontrolo.",
                )
            else:
                self.status_label.setText("Vzor\u010denje zaklju\u010deno.")
        except RuntimeError:
            pass

    def _on_terminated(self):
        try:
            self.run_btn.setEnabled(True)
            self.close_btn.setEnabled(True)
            self.strat_cb.setEnabled(True)
            self.strata_combo.setEnabled(self.strat_cb.isChecked())
            self.dir_btn.setEnabled(True)
            self.progress_bar.setVisible(False)

            err = self._task.error_message if self._task else "Neznana napaka"
            self.status_label.setText(f"Napaka: {err}")
        except RuntimeError:
            pass

    def closeEvent(self, event):
        if self._task:
            try:
                self._task.taskCompleted.disconnect()
            except Exception:
                pass
            try:
                self._task.taskTerminated.disconnect()
            except Exception:
                pass
            try:
                self._task.progressChanged.disconnect()
            except Exception:
                pass
            try:
                if not self._task.finished:
                    self._task.cancel()
            except RuntimeError:
                pass
        super().closeEvent(event)
