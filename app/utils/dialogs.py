from typing import List
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
    QCheckBox, QDialogButtonBox, QTextEdit, QDoubleSpinBox, QTableWidget, 
    QTableWidgetItem, QDateTimeEdit, QGroupBox, QPushButton, QProgressBar, QMessageBox
)
from PyQt5.QtCore import QDateTime, Qt, QTimer
from PyQt5.QtGui import QFont
from app.services.data_models import ProductTemplate, PriceRule, ScheduledJob
from app.services.local_models_manager import LocalModelsManager

class TemplateDialog(QDialog):
    """Dialog for creating/editing templates"""
    
    def __init__(self, parent=None, template: ProductTemplate = None):
        super().__init__(parent)
        self.template = template
        self.setWindowTitle("Template Editor")
        self.setModal(True)
        self.setMinimumWidth(500)
        self._setup_ui()
        
        if template:
            self._load_template()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Name
        layout.addWidget(QLabel("Template Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., 'Minimalist Mug Collection'")
        layout.addWidget(self.name_input)
        
        # Product Type
        layout.addWidget(QLabel("Product Type:"))
        self.type_combo = QComboBox()
        self.type_combo.setEditable(True)
        self.type_combo.addItems([
            "mug", "t-shirt", "poster", "hoodie", 
            "canvas", "sticker", "phone case", "tote bag"
        ])
        layout.addWidget(self.type_combo)
        
        # Base Price
        h = QHBoxLayout()
        h.addWidget(QLabel("Base Price ($):"))
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(5.0, 500.0)
        self.price_spin.setValue(25.0)
        self.price_spin.setSingleStep(5.0)
        h.addWidget(self.price_spin)
        h.addStretch()
        layout.addLayout(h)
        
        # Prompt Template
        layout.addWidget(QLabel("Prompt Template (use {prompt} as placeholder):"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("e.g., '{prompt}, minimalist design, clean lines, modern aesthetic'")
        self.prompt_input.setMaximumHeight(80)
        layout.addWidget(self.prompt_input)
        
        # Tags
        layout.addWidget(QLabel("Tags (comma-separated):"))
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("e.g., 'art, modern, gift, unique'")
        layout.addWidget(self.tags_input)
        
        # Collection
        layout.addWidget(QLabel("Collection Name (optional):"))
        self.collection_input = QLineEdit()
        layout.addWidget(self.collection_input)
        
        # Options
        self.auto_publish_check = QCheckBox("Auto-publish products")
        layout.addWidget(self.auto_publish_check)
        
        self.marketing_check = QCheckBox("Generate marketing assets")
        self.marketing_check.setChecked(True)
        layout.addWidget(self.marketing_check)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_template(self):
        """Load template data into form"""
        self.name_input.setText(self.template.name)
        self.type_combo.setCurrentText(self.template.product_type)
        self.price_spin.setValue(self.template.base_price)
        self.prompt_input.setPlainText(self.template.prompt_template)
        self.tags_input.setText(','.join(self.template.tags))
        self.collection_input.setText(self.template.collection_name)
        self.auto_publish_check.setChecked(self.template.auto_publish)
        self.marketing_check.setChecked(self.template.generate_marketing)
    
    def get_template(self) -> ProductTemplate:
        """Get template from form"""
        return ProductTemplate(
            name=self.name_input.text().strip(),
            product_type=self.type_combo.currentText(),
            base_price=self.price_spin.value(),
            prompt_template=self.prompt_input.toPlainText().strip(),
            tags=[t.strip() for t in self.tags_input.text().split(',') if t.strip()],
            collection_name=self.collection_input.text().strip(),
            auto_publish=self.auto_publish_check.isChecked(),
            generate_marketing=self.marketing_check.isChecked()
        )


class PriceRuleDialog(QDialog):
    """Dialog for setting price rules"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dynamic Pricing Rules")
        self.setModal(True)
        self.setMinimumWidth(600)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Set base prices for each product type:"))
        
        # Table for price rules
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Product Type", "Base Price ($)", "Markup %"])
        self.table.horizontalHeader().setStretchLastSection(True)
        
        # Add common product types
        product_types = [
            "mug", "t-shirt", "poster", "hoodie", "canvas",
            "sticker", "phone case", "tote bag", "pillow"
        ]
        
        self.table.setRowCount(len(product_types))
        for i, ptype in enumerate(product_types):
            self.table.setItem(i, 0, QTableWidgetItem(ptype.title()))
            
            price_spin = QDoubleSpinBox()
            price_spin.setRange(5.0, 500.0)
            price_spin.setValue(self._get_default_price(ptype))
            price_spin.setSingleStep(5.0)
            self.table.setCellWidget(i, 1, price_spin)
            
            markup_spin = QDoubleSpinBox()
            markup_spin.setRange(0.0, 200.0)
            markup_spin.setValue(50.0)
            markup_spin.setSuffix("%")
            self.table.setCellWidget(i, 2, markup_spin)
        
        layout.addWidget(self.table)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _get_default_price(self, product_type: str) -> float:
        """Get default price for product type"""
        defaults = {
            "mug": 15.0, "t-shirt": 20.0, "poster": 12.0,
            "hoodie": 35.0, "canvas": 40.0, "sticker": 5.0,
            "phone case": 18.0, "tote bag": 22.0, "pillow": 25.0
        }
        return defaults.get(product_type, 25.0)
    
    def get_rules(self) -> List[PriceRule]:
        """Get price rules from table"""
        rules = []
        for i in range(self.table.rowCount()):
            ptype = self.table.item(i, 0).text().lower()
            price = self.table.cellWidget(i, 1).value()
            markup = self.table.cellWidget(i, 2).value()
            rules.append(PriceRule(ptype, price, markup))
        return rules


class ScheduleDialog(QDialog):
    """Dialog for scheduling jobs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schedule Product Creation")
        self.setModal(True)
        self.setMinimumWidth(500)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Date/Time
        layout.addWidget(QLabel("Schedule Date & Time:"))
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.datetime_edit.setCalendarPopup(True)
        layout.addWidget(self.datetime_edit)
        
        # Product Type
        layout.addWidget(QLabel("Product Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "mug", "t-shirt", "poster", "hoodie", 
            "canvas", "sticker", "phone case"
        ])
        layout.addWidget(self.type_combo)
        
        # Price
        h = QHBoxLayout()
        h.addWidget(QLabel("Price ($):"))
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(5.0, 500.0)
        self.price_spin.setValue(25.0)
        h.addWidget(self.price_spin)
        h.addStretch()
        layout.addLayout(h)
        
        # Prompts
        layout.addWidget(QLabel("Prompts (one per line):"))
        self.prompts_text = QTextEdit()
        self.prompts_text.setPlaceholderText("Enter prompts, one per line...")
        layout.addWidget(self.prompts_text)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_job(self, shop_id: str) -> ScheduledJob:
        """Get scheduled job from form"""
        prompts = [p.strip() for p in self.prompts_text.toPlainText().split('\n') if p.strip()]
        dt = self.datetime_edit.dateTime().toPyDateTime()
        
        return ScheduledJob(
            id=0,
            scheduled_time=dt,
            prompts=prompts,
            product_type=self.type_combo.currentText(),
            price=self.price_spin.value(),
            shop_id=shop_id
        )

class LocalModelsDialog(QDialog):
    """Dialog for local models installation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = LocalModelsManager()
        self.setWindowTitle("Local AI Models Setup")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🖥️ Run Locally & Free")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Check if already installed
        if self.manager.is_installed():
            installed_label = QLabel("✅ Local models are already installed!")
            installed_label.setStyleSheet("color: green; font-size: 14px; font-weight: bold; padding: 10px;")
            installed_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(installed_label)
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.accept)
            layout.addWidget(close_btn)
            return
        
        # Info section
        info = self.manager.get_installation_info()
        
        info_text = QLabel(
            "Download open-source AI models to run completely free, no API costs!\n\n"
            "This is a one-time setup. Once installed, you can generate unlimited images "
            "without any API charges."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("padding: 10px; background: #e8f4f8; border-radius: 5px;")
        layout.addWidget(info_text)
        
        # Requirements
        req_group = QGroupBox("Installation Requirements")
        req_layout = QVBoxLayout()
        
        req_layout.addWidget(QLabel(f"📦 Total Download Size: {info['total_size_gb']} GB"))
        req_layout.addWidget(QLabel(f"💾 Disk Space Needed: {info['disk_space_needed']}"))
        req_layout.addWidget(QLabel(f"⏱️ Estimated Time: {info['estimated_time']}"))
        
        req_group.setLayout(req_layout)
        layout.addWidget(req_group)
        
        # Models details
        models_group = QGroupBox("Models to Download")
        models_layout = QVBoxLayout()
        
        for model in info['models']:
            model_text = f"• {model['name']} ({model['size_gb']} GB)\n  {model['description']}"
            label = QLabel(model_text)
            label.setStyleSheet("padding: 5px;")
            models_layout.addWidget(label)
        
        models_group.setLayout(models_layout)
        layout.addWidget(models_group)
        
        # Progress area
        self.progress_text = QTextEdit()
        self.progress_text.setReadOnly(True)
        self.progress_text.setMaximumHeight(100)
        self.progress_text.setVisible(False)
        layout.addWidget(self.progress_text)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)
        
        # Warnings
        warning = QLabel(
            "⚠️ Important Notes:\n"
            "• Requires GPU (CUDA/Metal) for fast generation\n"
            "• Will work on CPU but much slower (2-5 minutes per image)\n"
            "• Models will be saved to ~/.pod_wizard_local_models/\n"
            "• You can delete models anytime to free up space"
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("padding: 10px; background: #fff3cd; border-radius: 5px; color: #856404;")
        layout.addWidget(warning)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.install_btn = QPushButton("🚀 Install Models (Free)")
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        self.install_btn.clicked.connect(self._start_installation)
        btn_layout.addWidget(self.install_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _start_installation(self):
        """Start model installation"""
        reply = QMessageBox.question(
            self,
            "Confirm Installation",
            f"This will download {self.manager.get_installation_info()['total_size_gb']} GB of data.\n\n"
            "Make sure you have a stable internet connection.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.install_btn.setEnabled(False)
        self.progress_text.setVisible(True)
        self.progress_bar.setVisible(True)
        
        # Run installation in thread
        from threading import Thread
        
        def install():
            success = self.manager.install_models(self._update_progress)
            if success:
                QTimer.singleShot(0, lambda: self._installation_complete())
            else:
                QTimer.singleShot(0, lambda: self._installation_failed())
        
        Thread(target=install, daemon=True).start()
    
    def _update_progress(self, message: str):
        """Update progress display"""
        QTimer.singleShot(0, lambda: self.progress_text.append(message))
    
    def _installation_complete(self):
        """Handle successful installation"""
        self.progress_bar.setVisible(False)
        QMessageBox.information(
            self,
            "Installation Complete",
            "✅ Local models installed successfully!\n\n"
            "You can now use free, unlimited image generation.",
            QMessageBox.Ok
        )
        self.accept()
    
    def _installation_failed(self):
        """Handle failed installation"""
        self.progress_bar.setVisible(False)
        self.install_btn.setEnabled(True)
        QMessageBox.critical(
            self,
            "Installation Failed",
            "❌ Model installation failed.\n\n"
            "Please check the log above for details.",
            QMessageBox.Ok
        )
