"""
AI Print-on-Demand Product Wizard - Advanced Edition
Complete automation suite with templates, scheduling, analytics, and multi-shop support

===================================================================================
📐 DESIGN-FOCUSED POD WORKFLOW DOCUMENTATION
===================================================================================

This platform is an AI-powered DESIGN tool that automates the entire print-on-demand
process from design creation to product publishing. The paradigm shift:

    OLD MODEL: "Launch a new product" (e.g., design a specific mug)
    NEW MODEL: "Launch a design collection" (e.g., Cyberpunk Neon Collection)

WORKFLOW OVERVIEW:
------------------

1. DESIGN GENERATION (AI-Powered)
   └─ User provides: Theme/Style/Concept (e.g., "Retro Vaporwave Aesthetic")
   └─ AI generates: Multiple design variations (3-5 unique artworks)
   └─ Each design is: High-quality PNG/vector artwork with consistent theme
   └─ Output: Design files + metadata (prompts, colors, style tags)

2. DESIGN UPLOAD TO PRINTIFY
   └─ Design Processing: Image optimization, padding, centering
   └─ Upload via API: Base64-encoded image → Printify asset ID
   └─ Single design can be: Reused across multiple product types
   └─ Output: Printify image ID (reusable asset)

3. BLUEPRINT SELECTION (Product Templates)
   └─ Blueprint = Product type template (t-shirt, mug, hoodie, poster, etc.)
   └─ Each blueprint has: Providers (manufacturers), variants (sizes/colors)
   └─ Platform automatically: Finds best provider + available variants
   └─ Output: blueprint_id, provider_id, variant_ids

4. DESIGN APPLICATION TO PRODUCTS
   └─ Single design → Applied to MULTIPLE product blueprints
   └─ Example: "Sunset Dreams" design applied to:
       • Unisex T-Shirt (5 sizes, 10 colors) = 50 SKUs
       • Premium Hoodie (4 sizes, 8 colors) = 32 SKUs  
       • Coffee Mug (1 size, 2 finishes) = 2 SKUs
       • Poster (3 sizes) = 3 SKUs
       TOTAL: 1 design → 87 product SKUs
   └─ Process: For each product type:
       ├─ Find blueprint & provider
       ├─ Get available variants
       ├─ Build product data with design placement
       ├─ Set pricing (base cost + markup)
       └─ Create product via Printify API

5. PRODUCT CONFIGURATION
   └─ Title: SEO-optimized "{Design Name} - {Product Type}"
   └─ Description: Auto-generated from design theme
   └─ Tags: Design keywords (style, colors, mood)
   └─ Pricing: Dynamic markup (base_cost * multiplier)
   └─ Placement: Design centered, scaled to 85% (prevent cutoff)

6. PUBLISHING TO SHOPIFY
   └─ Printify publishes: Product → Shopify store integration
   └─ Auto-sync: Inventory, pricing, product details
   └─ Store displays: 87 unique products from 1 design
   └─ Order fulfillment: Automatic through Printify

7. MARKETING ASSET GENERATION
   └─ Social media flyers (9:16 format)
   └─ Lifestyle product photos (4:3 format)
   └─ Blog post images (16:9 format)
   └─ Video promotional content (15s ads)
   └─ All assets: Theme-consistent, design-focused

8. CAMPAIGN STRUCTURE
   └─ Campaign = Design Collection Launch
   └─ Contains: 3-5 designs with cohesive aesthetic
   └─ Each design applied to: 10-20 product types
   └─ Total campaign output: 300-500 product SKUs
   └─ Marketing focus: Design story, not product features

KEY CLASSES & METHODS:
---------------------

PrintifyAPI (Lines 883-1005):
  └─ upload_image(image_data, file_name) → upload_id
      • Uploads design as base64-encoded image
      • Returns reusable Printify asset ID
  
  └─ find_blueprint(product_type) → blueprint_id
      • Searches Printify catalog for product template
      • Example: "mug" → Blueprint ID 384
  
  └─ get_provider_and_variant(blueprint_id) → (provider_id, variant_id, details)
      • Finds best manufacturer and available product variants
  
  └─ create_product(shop_id, product_data) → product
      • Creates product with design applied
      • product_data includes: design placement, pricing, variants
  
  └─ publish_product(shop_id, product_id) → result
      • Publishes product to Shopify store
      • Makes product live for customer orders

WorkflowWorker (Lines 1093-1402):
  └─ Main automation thread for single product creation
  └─ _execute_workflow() - Core 9-step process:
      1. Find blueprint for product type
      2. Generate design image with AI
      3. Process image (padding, optimization)
      4. Upload to Printify
      5. Create product with design
      6. Auto-publish if enabled
      7. Save to database
      8. Generate marketing assets
      9. Package everything into ZIP

DESIGN-TO-PRODUCT FLOW:
-----------------------

User Input:
  "Create Cyberpunk Neon collection on mugs, t-shirts, hoodies"

Step 1: Generate 3 designs with Cyberpunk Neon theme
  → design_1.png, design_2.png, design_3.png

Step 2: For EACH design, create products on ALL specified types:
  
  Design 1 "Neon Skyline" →
    ├─ Upload once to Printify (upload_id_1)
    └─ Create products:
        ├─ Mug (blueprint 384) → product_id_001
        ├─ T-Shirt (blueprint 6) → product_id_002
        └─ Hoodie (blueprint 380) → product_id_003

  Design 2 "Circuit Dreams" →
    ├─ Upload once to Printify (upload_id_2)
    └─ Create products:
        ├─ Mug → product_id_004
        ├─ T-Shirt → product_id_005
        └─ Hoodie → product_id_006

  (Same for Design 3...)

Step 3: Publish all 9 products to Shopify
Step 4: Generate marketing campaign for "Cyberpunk Neon Collection"
Step 5: Create blog posts, social media, video ads about the DESIGNS

Result: 9 products in store, all marketed as cohesive design collection

BEST PRACTICES:
---------------

1. Design Quality: Generate at 1024x1024 minimum resolution
2. Design Style: Maintain consistent aesthetic within campaign
3. Product Selection: Choose complementary product types (apparel + home goods)
4. Pricing Strategy: Base cost × 2.5-3.0 markup for profit margin
5. Marketing Focus: Highlight design story, artistic vision, visual appeal
6. Campaign Timing: Launch 3-5 designs together for collection impact
7. Reuse Assets: One design → many products maximizes ROI

AUTOMATION CAPABILITIES:
-----------------------

✅ Design generation from text prompts
✅ Automatic image processing and optimization
✅ Blueprint discovery and provider selection
✅ Multi-product creation from single design
✅ Batch processing (create 100+ products unattended)
✅ Auto-publishing to Shopify
✅ Marketing asset generation (images, videos, blog posts)
✅ Campaign packaging and organization
✅ Database tracking and analytics

===================================================================================
"""
import sys
import time
import requests
import io
import base64
import zipfile
import os
import tempfile
import json
import csv
import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from api_service import PrintifyAPI, ReplicateAPI
from local_models_manager import LocalModelsManager
from database_manager import DatabaseManager
from image_manager import ImageManager
try:
    from dialogs import TemplateDialog, PriceRuleDialog, ScheduleDialog
    HAS_DIALOGS = True
except ImportError:
    HAS_DIALOGS = False
    TemplateDialog = PriceRuleDialog = ScheduleDialog = None

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, 
    QTextEdit, QSpinBox, QStatusBar, QMessageBox, QFileDialog,
    QGroupBox, QProgressBar, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QDoubleSpinBox, QListWidget, QDialog, QDialogButtonBox,
    QDateTimeEdit, QScrollArea, QFrame, QGridLayout
)
from PyQt5.QtCore import (
    QObject, pyqtSignal, QRunnable, QThreadPool, Qt, QTimer, QDateTime
)
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap

# Try to import QtChart, but make it optional
try:
    from PyQt5.QtChart import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
    HAS_CHARTS = True
except ImportError:
    HAS_CHARTS = False


# ============================================================================
# Configuration & Data Classes
# ============================================================================

# Data models are imported from data_models.py
from data_models import APIConfig, ProductTemplate, PriceRule, ProductDetails, WorkflowResult, ScheduledJob


# ============================================================================
# Local AI Models Manager
# ============================================================================

# LocalModelsManager is imported from local_models_manager.py


# ============================================================================
# Local Models Installation Dialog
# ============================================================================

# LocalModelsDialog is imported from dialogs.py
try:
    from dialogs import LocalModelsDialog
except ImportError:
    LocalModelsDialog = None

# ============================================================================

# DatabaseManager is imported from database_manager.py


# ============================================================================
# Image Manager
# ============================================================================

# ImageManager is imported from image_manager.py


# ============================================================================
# API Service Layer
# ============================================================================

# PrintifyAPI and ReplicateAPI are imported from api_service.py





# ============================================================================
# Worker Threads
# ============================================================================





    

    

    



# ============================================================================
# Dialog Windows
# ============================================================================

# TemplateDialog, PriceRuleDialog, and ScheduleDialog are imported from dialogs.py


# ============================================================================
# Main Application
# ============================================================================

class ProductWizardApp(QMainWindow):
    """Main application window with full features"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Print-on-Demand Product Wizard - Advanced Edition")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize managers
        self.db = DatabaseManager()
        self.img_manager = ImageManager()
        self.local_models = LocalModelsManager()
        self.config = None
        self.threadpool = QThreadPool()
        self.active_workers = 0
        self.completed_products = []
        
        # Setup scheduler timer
        self.scheduler_timer = QTimer()
        self.scheduler_timer.timeout.connect(self._check_scheduled_jobs)
        self.scheduler_timer.start(60000)  # Check every minute
        
        self._setup_ui()
        self._load_active_shop()
    
    def _setup_ui(self):
        """Initialize UI with tabs"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("🎨 AI POD Wizard - Advanced Edition")
        header.setFont(QFont("Arial", 20, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_main_tab(), "📦 Create Products")
        self.tabs.addTab(self._create_templates_tab(), "📋 Templates")
        self.tabs.addTab(self._create_pricing_tab(), "💰 Pricing Rules")
        self.tabs.addTab(self._create_shops_tab(), "🏪 Shops")
        self.tabs.addTab(self._create_schedule_tab(), "⏰ Scheduler")
        self.tabs.addTab(self._create_history_tab(), "📜 History")
        self.tabs.addTab(self._create_analytics_tab(), "📊 Analytics")
        layout.addWidget(self.tabs)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _create_main_tab(self) -> QWidget:
        """Create main product creation tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # API Config section
        layout.addWidget(self._create_config_section())
        
        # Product settings
        layout.addWidget(self._create_product_section())
        
        # Output log
        layout.addWidget(QLabel("Activity Log:"))
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(150)
        self.output_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.output_text)
        
        # Progress
        layout.addWidget(self._create_progress_section())
        
        # Controls
        layout.addWidget(self._create_controls())
        
        return widget
    
    def _create_config_section(self) -> QGroupBox:
        """Create API configuration section"""
        group = QGroupBox("API Configuration")
        layout = QVBoxLayout()
        
        # Mode selector
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Generation Mode:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["☁️ Cloud API (Replicate)", "🖥️ Local & Free"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo, 1)
        
        self.setup_local_btn = QPushButton("⚙️ Setup Local Models")
        self.setup_local_btn.clicked.connect(self._setup_local_models)
        self.setup_local_btn.setVisible(False)
        mode_layout.addWidget(self.setup_local_btn)
        
        layout.addLayout(mode_layout)
        
        # Cloud mode - Replicate API
        self.cloud_widget = QWidget()
        cloud_layout = QVBoxLayout(self.cloud_widget)
        cloud_layout.setContentsMargins(0, 0, 0, 0)
        
        h = QHBoxLayout()
        h.addWidget(QLabel("Replicate API Token:"))
        self.replicate_input = QLineEdit()
        self.replicate_input.setEchoMode(QLineEdit.Password)
        self.replicate_input.setPlaceholderText("Enter Replicate API token...")
        h.addWidget(self.replicate_input)
        cloud_layout.addLayout(h)
        
        layout.addWidget(self.cloud_widget)
        
        # Local mode info
        self.local_widget = QWidget()
        local_layout = QVBoxLayout(self.local_widget)
        local_layout.setContentsMargins(0, 0, 0, 0)
        
        if self.local_models.is_installed():
            local_status = QLabel("✅ Local models installed and ready!")
            local_status.setStyleSheet("color: green; font-weight: bold; padding: 10px; background: #d4edda; border-radius: 5px;")
        else:
            local_status = QLabel("⚠️ Local models not installed. Click 'Setup Local Models' to install.")
            local_status.setStyleSheet("color: #856404; font-weight: bold; padding: 10px; background: #fff3cd; border-radius: 5px;")
        
        local_status.setWordWrap(True)
        local_layout.addWidget(local_status)
        
        self.local_widget.setVisible(False)
        layout.addWidget(self.local_widget)
        
        # Load saved token
        self._load_replicate_token()
        
        group.setLayout(layout)
        return group
    
    def _on_mode_changed(self, index: int):
        """Handle mode change"""
        is_local = index == 1
        self.cloud_widget.setVisible(not is_local)
        self.local_widget.setVisible(is_local)
        self.setup_local_btn.setVisible(is_local)
    
    def _setup_local_models(self):
        """Open local models setup dialog"""
        dialog = LocalModelsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Refresh the status
            self._on_mode_changed(self.mode_combo.currentIndex())
    
    def _create_product_section(self) -> QGroupBox:
        """Create product configuration section"""
        group = QGroupBox("Product Configuration")
        layout = QVBoxLayout()
        
        # Template selector
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Use Template:"))
        self.template_combo = QComboBox()
        self.template_combo.addItem("-- No Template --")
        self._refresh_template_combo()
        self.template_combo.currentIndexChanged.connect(self._apply_template)
        h1.addWidget(self.template_combo, 1)
        layout.addLayout(h1)
        
        # Product type & price
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Product Type:"))
        self.product_type_combo = QComboBox()
        self.product_type_combo.addItems([
            "mug", "t-shirt", "poster", "hoodie", 
            "canvas", "sticker", "phone case", "tote bag"
        ])
        self.product_type_combo.currentTextChanged.connect(self._update_price_from_rules)
        h2.addWidget(self.product_type_combo, 1)
        
        h2.addWidget(QLabel("   Price ($):"))
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(5.0, 500.0)
        self.price_spin.setValue(25.0)
        self.price_spin.setSingleStep(5.0)
        h2.addWidget(self.price_spin)
        layout.addLayout(h2)
        
        # Design prompt
        layout.addWidget(QLabel("Design Prompt:"))
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("e.g., 'A watercolor fox cub in a field of sunflowers'")
        layout.addWidget(self.prompt_input)
        
        # Batch mode
        batch_group = QGroupBox("Batch Creation Mode")
        batch_layout = QVBoxLayout()
        
        self.batch_mode_check = QCheckBox("Enable Batch Mode (CSV/Text file)")
        self.batch_mode_check.toggled.connect(self._toggle_batch_mode)
        batch_layout.addWidget(self.batch_mode_check)
        
        batch_file_layout = QHBoxLayout()
        self.batch_file_input = QLineEdit()
        self.batch_file_input.setPlaceholderText("Select a CSV or text file...")
        self.batch_file_input.setEnabled(False)
        batch_file_layout.addWidget(self.batch_file_input)
        
        self.batch_browse_btn = QPushButton("Browse...")
        self.batch_browse_btn.setEnabled(False)
        self.batch_browse_btn.clicked.connect(self._browse_batch_file)
        batch_file_layout.addWidget(self.batch_browse_btn)
        batch_layout.addLayout(batch_file_layout)
        
        batch_group.setLayout(batch_layout)
        layout.addWidget(batch_group)
        
        # Quantity (single mode only)
        h3 = QHBoxLayout()
        self.quantity_label = QLabel("Number of Products:")
        h3.addWidget(self.quantity_label)
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 20)
        self.quantity_spin.setValue(1)
        h3.addWidget(self.quantity_spin)
        h3.addStretch()
        layout.addLayout(h3)
        
        # Advanced options
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QVBoxLayout()
        
        self.marketing_check = QCheckBox("Generate Marketing Assets")
        self.marketing_check.setChecked(True)
        advanced_layout.addWidget(self.marketing_check)
        
        self.auto_publish_check = QCheckBox("Auto-publish products")
        advanced_layout.addWidget(self.auto_publish_check)
        
        self.variations_check = QCheckBox("Create design variations")
        advanced_layout.addWidget(self.variations_check)
        
        # Tags
        h4 = QHBoxLayout()
        h4.addWidget(QLabel("Tags:"))
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("comma, separated, tags")
        h4.addWidget(self.tags_input)
        advanced_layout.addLayout(h4)
        
        # Collection
        h5 = QHBoxLayout()
        h5.addWidget(QLabel("Collection:"))
        self.collection_input = QLineEdit()
        self.collection_input.setPlaceholderText("Optional collection name")
        h5.addWidget(self.collection_input)
        advanced_layout.addLayout(h5)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        group.setLayout(layout)
        return group
    
    def _create_progress_section(self) -> QGroupBox:
        """Create progress section"""
        group = QGroupBox("Progress")
        layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m products")
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Idle")
        self.progress_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_label)
        
        group.setLayout(layout)
        return group
    
    def _create_controls(self) -> QWidget:
        """Create control buttons"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.start_btn = QPushButton("🚀 Start Creation Workflow")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.start_btn.clicked.connect(self._start_workflow)
        self.start_btn.setEnabled(False)
        
        self.clear_btn = QPushButton("🗑️ Clear Log")
        self.clear_btn.clicked.connect(self.output_text.clear)
        
        layout.addWidget(self.start_btn, 3)
        layout.addWidget(self.clear_btn, 1)
        
        return widget
    
    def _create_templates_tab(self) -> QWidget:
        """Create templates management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        btn_layout = QHBoxLayout()
        new_btn = QPushButton("➕ New Template")
        new_btn.clicked.connect(self._new_template)
        btn_layout.addWidget(new_btn)
        
        edit_btn = QPushButton("✏️ Edit Template")
        edit_btn.clicked.connect(self._edit_template)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ Delete Template")
        delete_btn.clicked.connect(self._delete_template)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Templates list
        self.templates_list = QListWidget()
        self._refresh_templates_list()
        layout.addWidget(self.templates_list)
        
        return widget
    
    def _create_pricing_tab(self) -> QWidget:
        """Create pricing rules tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Configure dynamic pricing rules for each product type:"))
        
        btn = QPushButton("⚙️ Configure Pricing Rules")
        btn.clicked.connect(self._configure_pricing)
        layout.addWidget(btn)
        
        # Show current rules
        self.pricing_table = QTableWidget()
        self.pricing_table.setColumnCount(3)
        self.pricing_table.setHorizontalHeaderLabels(["Product Type", "Base Price", "Markup"])
        self._refresh_pricing_table()
        layout.addWidget(self.pricing_table)
        
        return widget
    
    def _create_shops_tab(self) -> QWidget:
        """Create shops management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Instructions
        layout.addWidget(QLabel("Manage multiple Printify shops:"))
        
        # Controls
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add Shop")
        add_btn.clicked.connect(self._add_shop)
        btn_layout.addWidget(add_btn)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._refresh_shops_list)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Shops table
        self.shops_table = QTableWidget()
        self.shops_table.setColumnCount(4)
        self.shops_table.setHorizontalHeaderLabels(["Shop ID", "Shop Name", "Active", "Actions"])
        self._refresh_shops_list()
        layout.addWidget(self.shops_table)
        
        return widget
    
    def _create_schedule_tab(self) -> QWidget:
        """Create scheduler tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Schedule product creation for future dates:"))
        
        btn = QPushButton("➕ Schedule New Job")
        btn.clicked.connect(self._schedule_job)
        layout.addWidget(btn)
        
        # Scheduled jobs table
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(5)
        self.schedule_table.setHorizontalHeaderLabels([
            "Scheduled Time", "Product Type", "# Prompts", "Status", "Actions"
        ])
        self._refresh_schedule_table()
        layout.addWidget(self.schedule_table)
        
        return widget
    
    def _create_history_tab(self) -> QWidget:
        """Create history tab with image gallery"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._refresh_history)
        btn_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("📤 Export CSV")
        export_btn.clicked.connect(self._export_history)
        btn_layout.addWidget(export_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # History table with thumbnails
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Image", "Product ID", "Title", "Type", "Price", "Status", "Created"
        ])
        self.history_table.setRowHeight(0, 60)
        self._refresh_history()
        layout.addWidget(self.history_table)
        
        return widget
    
    def _create_analytics_tab(self) -> QWidget:
        """Create analytics dashboard"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Stats cards
        stats_layout = QHBoxLayout()
        
        self.total_products_label = QLabel("Total Products: 0")
        self.total_products_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 15px; background: #3498db; color: white; border-radius: 5px;")
        stats_layout.addWidget(self.total_products_label)
        
        self.total_value_label = QLabel("Total Value: $0")
        self.total_value_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 15px; background: #2ecc71; color: white; border-radius: 5px;")
        stats_layout.addWidget(self.total_value_label)
        
        self.recent_label = QLabel("Last 30 Days: 0")
        self.recent_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 15px; background: #e74c3c; color: white; border-radius: 5px;")
        stats_layout.addWidget(self.recent_label)
        
        layout.addLayout(stats_layout)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Analytics")
        refresh_btn.clicked.connect(self._refresh_analytics)
        layout.addWidget(refresh_btn)
        
        # Analytics charts
        charts_widget = QWidget()
        charts_layout = QVBoxLayout()
        charts_widget.setLayout(charts_layout)
        charts_widget.setStyleSheet("background: #ecf0f1; border-radius: 8px; padding: 15px;")
        
        charts_title = QLabel("📊 Product Performance Over Time")
        charts_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        charts_layout.addWidget(charts_title)
        
        # Create simple text-based chart
        self.chart_display = QLabel("Loading analytics...")
        self.chart_display.setWordWrap(True)
        self.chart_display.setStyleSheet("font-family: monospace; padding: 10px; background: white; border-radius: 5px;")
        charts_layout.addWidget(self.chart_display)
        
        layout.addWidget(charts_widget)
        
        self._refresh_analytics()
        
        return widget
    
    # ========================================================================
    # Event Handlers
    # ========================================================================
    
    def _load_active_shop(self):
        """Load active shop on startup"""
        shop = self.db.get_active_shop()
        if shop:
            self.config = APIConfig(shop['printify_token'], "")
            self.status_bar.showMessage(f"Active Shop: {shop['shop_name']} (ID: {shop['shop_id']})")
            self.start_btn.setEnabled(True)
    
    def _load_replicate_token(self):
        """Load saved Replicate token"""
        config_file = Path.home() / ".pod_wizard_replicate.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    self.replicate_input.setText(data.get('token', ''))
            except:
                pass
    
    def _save_replicate_token(self):
        """Save Replicate token"""
        config_file = Path.home() / ".pod_wizard_replicate.json"
        try:
            with open(config_file, 'w') as f:
                json.dump({'token': self.replicate_input.text()}, f)
        except:
            pass
    
    def _toggle_batch_mode(self, enabled: bool):
        """Toggle batch mode"""
        self.batch_file_input.setEnabled(enabled)
        self.batch_browse_btn.setEnabled(enabled)
        self.prompt_input.setEnabled(not enabled)
        self.quantity_label.setEnabled(not enabled)
        self.quantity_spin.setEnabled(not enabled)
    
    def _browse_batch_file(self):
        """Browse for batch file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Batch File", "",
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*.*)"
        )
        if file_path:
            self.batch_file_input.setText(file_path)
    
    def _apply_template(self, index: int):
        """Apply selected template"""
        if index == 0:
            return
        
        templates = self.db.get_templates()
        if index - 1 < len(templates):
            template = templates[index - 1]
            self.product_type_combo.setCurrentText(template.product_type)
            self.price_spin.setValue(template.base_price)
            self.tags_input.setText(','.join(template.tags))
            self.collection_input.setText(template.collection_name)
            self.auto_publish_check.setChecked(template.auto_publish)
            self.marketing_check.setChecked(template.generate_marketing)
    
    def _update_price_from_rules(self, product_type: str):
        """Update price based on pricing rules"""
        price = self.db.get_price_for_type(product_type)
        self.price_spin.setValue(price)
    
    def _start_workflow(self):
        """Start product creation workflow"""
        # Validate setup
        shop = self.db.get_active_shop()
        if not shop:
            QMessageBox.warning(self, "No Shop", "Please add and activate a shop first.", QMessageBox.Ok)
            return
        
        # Check mode and validate
        use_local = self.mode_combo.currentIndex() == 1
        
        if use_local:
            if not self.local_models.is_installed():
                QMessageBox.warning(
                    self, "Models Not Installed",
                    "Please install local models first using the 'Setup Local Models' button.",
                    QMessageBox.Ok
                )
                return
            
            self.config = APIConfig(
                shop['printify_token'], 
                "", 
                use_local_models=True,
                local_models_path=str(self.local_models.models_dir)
            )
        else:
            replicate_token = self.replicate_input.text().strip()
            if not replicate_token:
                QMessageBox.warning(self, "Missing Token", "Please enter your Replicate API token.", QMessageBox.Ok)
                return
            
            self._save_replicate_token()
            self.config = APIConfig(shop['printify_token'], replicate_token)
        
        # Get prompts
        if self.batch_mode_check.isChecked():
            prompts = self._load_batch_prompts()
            if not prompts:
                return
        else:
            prompt = self.prompt_input.text().strip()
            if not prompt:
                QMessageBox.warning(self, "Missing Prompt", "Please enter a design prompt.", QMessageBox.Ok)
                return
            
            quantity = self.quantity_spin.value()
            
            if self.variations_check.isChecked():
                style_modifiers = [
                    "minimalist style", "vintage retro style", 
                    "bold modern style", "watercolor artistic style",
                    "geometric abstract style", "hand-drawn illustration style"
                ]
                prompts = [f"{prompt}, {mod}" for mod in style_modifiers[:quantity]]
            else:
                prompts = [prompt] * quantity
        
        # Get settings
        product_type = self.product_type_combo.currentText()
        price = self.price_spin.value()
        create_marketing = self.marketing_check.isChecked()
        auto_publish = self.auto_publish_check.isChecked()
        tags = [t.strip() for t in self.tags_input.text().split(',') if t.strip()]
        collection = self.collection_input.text().strip()
        
        # UI updates
        self.start_btn.setEnabled(False)
        self.start_btn.setText("⏳ Processing...")
        self.completed_products = []
        self.active_workers = 0
        
        total = len(prompts)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"Starting {total} product(s)...")
        
        mode_text = "Local (Free)" if use_local else "Cloud API"
        self.log_info(f"\n{'='*60}")
        self.log_info(f"Starting workflow: {total}x '{product_type}'")
        self.log_info(f"Shop: {shop['shop_name']}")
        self.log_info(f"Mode: {mode_text}")
        self.log_info(f"{'='*60}\n")
        
        # Launch workers
        for i, prompt in enumerate(prompts):
            details = ProductDetails(prompt, product_type, price, tags, collection, shop['shop_id'])
            worker = ProductCreatorWorker(
                self.config, details, create_marketing, i + 1,
                auto_publish, self.db, self.img_manager, self.local_models
            )
            worker.signals.progress.connect(self._on_progress)
            worker.signals.result.connect(self._on_result)
            worker.signals.finished.connect(self._on_worker_finished)
            
            self.threadpool.start(worker)
            self.active_workers += 1
    
    def _load_batch_prompts(self) -> List[str]:
        """Load prompts from batch file"""
        file_path = self.batch_file_input.text().strip()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Invalid File", "Please select a valid batch file.", QMessageBox.Ok)
            return []
        
        try:
            prompts = []
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.csv'):
                    reader = csv.reader(f)
                    next(reader, None)
                    for row in reader:
                        if row and row[0].strip():
                            prompts.append(row[0].strip())
                else:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            prompts.append(line)
            
            if not prompts:
                QMessageBox.warning(self, "Empty File", "No valid prompts found.", QMessageBox.Ok)
                return []
            
            reply = QMessageBox.question(
                self, "Confirm Batch",
                f"Found {len(prompts)} prompts. Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            return prompts if reply == QMessageBox.Yes else []
            
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Could not read file:\n\n{str(e)}", QMessageBox.Ok)
            return []
    
    def _on_progress(self, message: str, item_index: int):
        """Handle progress update"""
        self.log_info(f"[Product {item_index}] {message}")
        self.progress_label.setText(f"Product {item_index}: {message}")
    
    def _on_result(self, result: WorkflowResult):
        """Handle workflow result"""
        if result.status == 'success':
            self.log_success(f"\n✅ Product {result.item_index}: {result.message}")
            self.log_info(f"   Product ID: {result.product_id}")
            self.completed_products.append(result)
            QTimer.singleShot(100, lambda: self._save_assets(result))
        else:
            self.log_error(f"\n❌ Product {result.item_index}: {result.message}")
        
        self.progress_bar.setValue(self.progress_bar.value() + 1)
    
    def _on_worker_finished(self, item_index: int):
        """Handle worker completion"""
        self.active_workers -= 1
        if self.active_workers == 0:
            self._workflow_complete()
    
    def _workflow_complete(self):
        """Handle workflow completion"""
        self.log_info(f"\n{'='*60}")
        self.log_info(f"🎉 COMPLETE! Created {len(self.completed_products)} product(s)")
        self.log_info(f"{'='*60}\n")
        
        self.start_btn.setEnabled(True)
        self.start_btn.setText("🚀 Start Creation Workflow")
        self.progress_label.setText("Complete!")
        
        self._refresh_history()
        self._refresh_analytics()
        
        if self.completed_products:
            msg = f"Successfully created {len(self.completed_products)} product(s)!"
            QMessageBox.information(self, "Workflow Complete", msg, QMessageBox.Ok)
    
    def _save_assets(self, result: WorkflowResult):
        """Prompt to save assets"""
        if not result.assets_path:
            return
        
        default_name = f"Assets_{result.product_id}.zip"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Product Assets", default_name, "ZIP Files (*.zip)"
        )
        
        if save_path:
            try:
                if os.path.exists(save_path):
                    os.remove(save_path)
                os.rename(result.assets_path, save_path)
                self.log_success(f"📦 Assets saved: {save_path}")
            except Exception as e:
                self.log_error(f"Failed to save assets: {str(e)}")
        else:
            try:
                os.remove(result.assets_path)
            except:
                pass
    
    # ========================================================================
    # Templates Management
    # ========================================================================
    
    def _new_template(self):
        """Create new template"""
        dialog = TemplateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            template = dialog.get_template()
            if template.name:
                self.db.save_template(template)
                self._refresh_templates_list()
                self._refresh_template_combo()
                QMessageBox.information(self, "Success", "Template saved!", QMessageBox.Ok)
    
    def _edit_template(self):
        """Edit selected template"""
        current = self.templates_list.currentRow()
        if current < 0:
            QMessageBox.warning(self, "No Selection", "Please select a template to edit.", QMessageBox.Ok)
            return
        
        templates = self.db.get_templates()
        if current < len(templates):
            dialog = TemplateDialog(self, templates[current])
            if dialog.exec_() == QDialog.Accepted:
                template = dialog.get_template()
                self.db.save_template(template)
                self._refresh_templates_list()
                self._refresh_template_combo()
    
    def _delete_template(self):
        """Delete selected template"""
        current = self.templates_list.currentRow()
        if current < 0:
            QMessageBox.warning(self, "No Selection", "Please select a template to delete.", QMessageBox.Ok)
            return
        
        templates = self.db.get_templates()
        if current < len(templates):
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete template '{templates[current].name}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.db.delete_template(templates[current].name)
                self._refresh_templates_list()
                self._refresh_template_combo()
    
    def _refresh_templates_list(self):
        """Refresh templates list"""
        self.templates_list.clear()
        for template in self.db.get_templates():
            self.templates_list.addItem(f"{template.name} - {template.product_type} (${template.base_price})")
    
    def _refresh_template_combo(self):
        """Refresh template combo box"""
        current = self.template_combo.currentText()
        self.template_combo.clear()
        self.template_combo.addItem("-- No Template --")
        for template in self.db.get_templates():
            self.template_combo.addItem(template.name)
        
        index = self.template_combo.findText(current)
        if index >= 0:
            self.template_combo.setCurrentIndex(index)
    
    # ========================================================================
    # Pricing Management
    # ========================================================================
    
    def _configure_pricing(self):
        """Configure pricing rules"""
        dialog = PriceRuleDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            for rule in dialog.get_rules():
                self.db.save_price_rule(rule)
            self._refresh_pricing_table()
            QMessageBox.information(self, "Success", "Pricing rules updated!", QMessageBox.Ok)
    
    def _refresh_pricing_table(self):
        """Refresh pricing table"""
        rules = self.db.get_price_rules()
        self.pricing_table.setRowCount(len(rules))
        
        for i, rule in enumerate(rules):
            self.pricing_table.setItem(i, 0, QTableWidgetItem(rule.product_type.title()))
            self.pricing_table.setItem(i, 1, QTableWidgetItem(f"${rule.base_price:.2f}"))
            self.pricing_table.setItem(i, 2, QTableWidgetItem(f"{rule.markup_percent:.0f}%"))
    
    # ========================================================================
    # Shops Management
    # ========================================================================
    
    def _add_shop(self):
        """Add new shop"""
        token, ok = QMessageBox.getText(self, "Add Shop", "Enter Printify API Token:")
        if not ok or not token.strip():
            return
        
        try:
            api = PrintifyAPI(token.strip())
            shops = api.get_shops()
            if not shops:
                raise Exception("No shops found")
            
            shop = shops[0]
            self.db.add_shop(str(shop['id']), shop['title'], token.strip())
            self._refresh_shops_list()
            QMessageBox.information(self, "Success", f"Shop '{shop['title']}' added!", QMessageBox.Ok)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add shop:\n\n{str(e)}", QMessageBox.Ok)
    
    def _refresh_shops_list(self):
        """Refresh shops list"""
        shops = self.db.get_shops()
        self.shops_table.setRowCount(len(shops))
        
        for i, shop in enumerate(shops):
            self.shops_table.setItem(i, 0, QTableWidgetItem(shop['shop_id']))
            self.shops_table.setItem(i, 1, QTableWidgetItem(shop['shop_name']))
            self.shops_table.setItem(i, 2, QTableWidgetItem("✓" if shop['is_active'] else ""))
            
            activate_btn = QPushButton("Activate" if not shop['is_active'] else "Active")
            activate_btn.setEnabled(not shop['is_active'])
            activate_btn.clicked.connect(lambda checked, sid=shop['shop_id']: self._activate_shop(sid))
            self.shops_table.setCellWidget(i, 3, activate_btn)
    
    def _activate_shop(self, shop_id: str):
        """Activate shop"""
        self.db.set_active_shop(shop_id)
        self._refresh_shops_list()
        self._load_active_shop()
    
    # ========================================================================
    # Scheduler
    # ========================================================================
    
    def _schedule_job(self):
        """Schedule new job"""
        shop = self.db.get_active_shop()
        if not shop:
            QMessageBox.warning(self, "No Shop", "Please add and activate a shop first.", QMessageBox.Ok)
            return
        
        dialog = ScheduleDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            job = dialog.get_job(shop['shop_id'])
            self.db.add_scheduled_job(job)
            self._refresh_schedule_table()
            QMessageBox.information(self, "Success", "Job scheduled!", QMessageBox.Ok)
    
    def _refresh_schedule_table(self):
        """Refresh schedule table"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM scheduled_jobs ORDER BY scheduled_time DESC LIMIT 50")
        
        rows = cursor.fetchall()
        self.schedule_table.setRowCount(len(rows))
        
        for i, row in enumerate(rows):
            self.schedule_table.setItem(i, 0, QTableWidgetItem(row[1]))
            self.schedule_table.setItem(i, 1, QTableWidgetItem(row[3]))
            prompts = json.loads(row[2])
            self.schedule_table.setItem(i, 2, QTableWidgetItem(str(len(prompts))))
            self.schedule_table.setItem(i, 3, QTableWidgetItem(row[6]))
    
    def _check_scheduled_jobs(self):
        """Check and execute pending jobs"""
        jobs = self.db.get_pending_jobs()
        for job in jobs:
            self.db.update_job_status(job.id, 'running')
            
            # Execute scheduled job
            try:
                prompts = json.loads(job.prompts)
                self.log_info(f"🚀 Executing scheduled job {job.id}: {len(prompts)} products")
                
                # Update UI to show job is running
                self.status_label.setText(f"Running scheduled job: {job.name}")
                
                # Launch batch workflow
                self._run_batch_workflow(prompts)
                
                # Update job status
                self.db.update_job_status(job.id, 'completed')
                self.log_success(f"✅ Scheduled job {job.id} completed successfully")
                
            except Exception as e:
                self.log_error(f"❌ Scheduled job {job.id} failed: {str(e)}")
                self.db.update_job_status(job.id, 'failed')
            
            # Refresh schedule table
            self._refresh_schedule_table()
    
    # ========================================================================
    # History Management
    # ========================================================================
    
    def _refresh_history(self):
        """Refresh history table"""
        products = self.db.get_products(100)
        self.history_table.setRowCount(len(products))
        
        for i, product in enumerate(products):
            # Thumbnail
            if product.get('image_path') and os.path.exists(product['image_path']):
                thumbnail = self.img_manager.get_thumbnail(product['image_path'], (50, 50))
                label = QLabel()
                label.setPixmap(thumbnail)
                label.setAlignment(Qt.AlignCenter)
                self.history_table.setCellWidget(i, 0, label)
            
            self.history_table.setItem(i, 1, QTableWidgetItem(product.get('product_id', '')))
            self.history_table.setItem(i, 2, QTableWidgetItem(product.get('title', '')[:50]))
            self.history_table.setItem(i, 3, QTableWidgetItem(product.get('product_type', '')))
            self.history_table.setItem(i, 4, QTableWidgetItem(f"${product.get('price', 0):.2f}"))
            self.history_table.setItem(i, 5, QTableWidgetItem(product.get('status', '')))
            self.history_table.setItem(i, 6, QTableWidgetItem(product.get('created_at', '')[:16]))
        
        self.history_table.resizeColumnsToContents()
    
    def _export_history(self):
        """Export history to CSV"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export History", "product_history.csv", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                products = self.db.get_products(1000)
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=products[0].keys() if products else [])
                    writer.writeheader()
                    writer.writerows(products)
                QMessageBox.information(self, "Success", "History exported!", QMessageBox.Ok)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed:\n\n{str(e)}", QMessageBox.Ok)
    
    # ========================================================================
    # Analytics
    # ========================================================================
    
    def _refresh_analytics(self):
        """Refresh analytics dashboard"""
        analytics = self.db.get_analytics()
        
        self.total_products_label.setText(f"Total Products: {analytics['total_products']}")
        self.total_value_label.setText(f"Total Value: ${analytics['total_value']:.2f}")
        self.recent_label.setText(f"Last 30 Days: {analytics['recent_count']}")
        
        # Update chart display
        try:
            products = self.db.get_all_products()
            if products:
                # Group by date and count
                from collections import defaultdict
                from datetime import datetime, timedelta
                
                date_counts = defaultdict(int)
                for p in products:
                    created = datetime.fromisoformat(p['created_at'])
                    date_key = created.strftime('%Y-%m-%d')
                    date_counts[date_key] += 1
                
                # Get last 14 days
                today = datetime.now()
                chart_lines = ["Product Creation Timeline (Last 14 Days)\n"]
                
                for i in range(13, -1, -1):
                    date = today - timedelta(days=i)
                    date_key = date.strftime('%Y-%m-%d')
                    count = date_counts.get(date_key, 0)
                    
                    # Create ASCII bar chart
                    bar = '█' * count if count > 0 else ''
                    chart_lines.append(f"{date.strftime('%m/%d')}: {bar} ({count})")
                
                self.chart_display.setText('\n'.join(chart_lines))
            else:
                self.chart_display.setText("No products yet. Create some to see analytics!")
        except Exception as e:
            self.chart_display.setText(f"Chart unavailable: {e}")
    
    # ========================================================================
    # Logging
    # ========================================================================
    
    def log_info(self, message: str):
        """Log info message"""
        self.output_text.append(message)
        self.output_text.ensureCursorVisible()
    
    def log_success(self, message: str):
        """Log success message"""
        self.output_text.setTextColor(QColor(39, 174, 96))
        self.output_text.append(message)
        self.output_text.setTextColor(QColor(0, 0, 0))
        self.output_text.ensureCursorVisible()
    
    def log_error(self, message: str):
        """Log error message"""
        self.output_text.setTextColor(QColor(231, 76, 60))
        self.output_text.append(message)
        self.output_text.setTextColor(QColor(0, 0, 0))
        self.output_text.ensureCursorVisible()


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 245))
    palette.setColor(QPalette.WindowText, QColor(33, 33, 33))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 250))
    palette.setColor(QPalette.Text, QColor(33, 33, 33))
    palette.setColor(QPalette.Button, QColor(240, 240, 245))
    palette.setColor(QPalette.ButtonText, QColor(33, 33, 33))
    palette.setColor(QPalette.Highlight, QColor(52, 152, 219))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = ProductWizardApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
