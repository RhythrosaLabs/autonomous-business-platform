"""
Spreadsheet Viewer
==================
View, edit, and analyze CSV/Excel spreadsheets with AI insights.
"""

import io
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Optional imports
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class SpreadsheetViewer:
    """Spreadsheet viewer and editor with AI analysis."""
    
    SUPPORTED_FORMATS = {
        'csv': 'Comma Separated Values',
        'xlsx': 'Excel Workbook',
        'xls': 'Excel 97-2003',
        'tsv': 'Tab Separated Values',
        'json': 'JSON Data'
    }
    
    def __init__(self, api_service=None):
        self.api_service = api_service
        self.current_df = None
        self.file_path = None
    
    def load_file(self, file_path: str, sheet_name: str = None) -> "pd.DataFrame":
        """Load spreadsheet file into DataFrame."""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas required: pip install pandas")
        
        ext = Path(file_path).suffix.lower().lstrip('.')
        
        if ext == 'csv':
            self.current_df = pd.read_csv(file_path)
        elif ext == 'tsv':
            self.current_df = pd.read_csv(file_path, sep='\t')
        elif ext in ['xlsx', 'xls']:
            if not OPENPYXL_AVAILABLE and ext == 'xlsx':
                raise ImportError("openpyxl required: pip install openpyxl")
            self.current_df = pd.read_excel(file_path, sheet_name=sheet_name)
        elif ext == 'json':
            self.current_df = pd.read_json(file_path)
        else:
            raise ValueError(f"Unsupported format: {ext}")
        
        self.file_path = file_path
        return self.current_df
    
    def load_from_bytes(self, data: bytes, filename: str, sheet_name: str = None) -> "pd.DataFrame":
        """Load spreadsheet from bytes."""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas required")
        
        ext = Path(filename).suffix.lower().lstrip('.')
        
        if ext == 'csv':
            self.current_df = pd.read_csv(io.BytesIO(data))
        elif ext == 'tsv':
            self.current_df = pd.read_csv(io.BytesIO(data), sep='\t')
        elif ext in ['xlsx', 'xls']:
            self.current_df = pd.read_excel(io.BytesIO(data), sheet_name=sheet_name)
        elif ext == 'json':
            self.current_df = pd.read_json(io.BytesIO(data))
        else:
            raise ValueError(f"Unsupported format: {ext}")
        
        return self.current_df
    
    def save_file(self, output_path: str = None, format: str = None) -> str:
        """Save DataFrame to file."""
        if self.current_df is None:
            raise ValueError("No data loaded")
        
        output_path = output_path or self.file_path
        if not output_path:
            raise ValueError("No output path specified")
        
        ext = format or Path(output_path).suffix.lower().lstrip('.')
        
        if ext == 'csv':
            self.current_df.to_csv(output_path, index=False)
        elif ext == 'tsv':
            self.current_df.to_csv(output_path, index=False, sep='\t')
        elif ext == 'xlsx':
            self.current_df.to_excel(output_path, index=False)
        elif ext == 'json':
            self.current_df.to_json(output_path, orient='records', indent=2)
        else:
            raise ValueError(f"Unsupported format: {ext}")
        
        return output_path
    
    def to_bytes(self, format: str = 'csv') -> bytes:
        """Export DataFrame to bytes."""
        if self.current_df is None:
            raise ValueError("No data loaded")
        
        buffer = io.BytesIO()
        
        if format == 'csv':
            self.current_df.to_csv(buffer, index=False)
        elif format == 'xlsx':
            self.current_df.to_excel(buffer, index=False)
        elif format == 'json':
            buffer.write(self.current_df.to_json(orient='records', indent=2).encode())
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        buffer.seek(0)
        return buffer.read()
    
    # ===== Data Operations =====
    
    def get_summary(self) -> Dict:
        """Get summary statistics of the data."""
        if self.current_df is None:
            return {}
        
        df = self.current_df
        
        return {
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'memory_usage': df.memory_usage(deep=True).sum(),
            'missing_values': df.isnull().sum().to_dict(),
            'numeric_columns': list(df.select_dtypes(include=['number']).columns),
            'text_columns': list(df.select_dtypes(include=['object']).columns),
        }
    
    def get_statistics(self) -> Dict:
        """Get detailed statistics for numeric columns."""
        if self.current_df is None:
            return {}
        
        df = self.current_df
        numeric_df = df.select_dtypes(include=['number'])
        
        if numeric_df.empty:
            return {}
        
        stats = numeric_df.describe().to_dict()
        
        # Add additional stats
        for col in numeric_df.columns:
            stats[col]['median'] = numeric_df[col].median()
            stats[col]['mode'] = numeric_df[col].mode().iloc[0] if not numeric_df[col].mode().empty else None
            stats[col]['variance'] = numeric_df[col].var()
        
        return stats
    
    def filter_data(self, column: str, operator: str, value: Any) -> "pd.DataFrame":
        """Filter data based on condition."""
        if self.current_df is None:
            raise ValueError("No data loaded")
        
        df = self.current_df
        
        if operator == '==':
            mask = df[column] == value
        elif operator == '!=':
            mask = df[column] != value
        elif operator == '>':
            mask = df[column] > value
        elif operator == '>=':
            mask = df[column] >= value
        elif operator == '<':
            mask = df[column] < value
        elif operator == '<=':
            mask = df[column] <= value
        elif operator == 'contains':
            mask = df[column].astype(str).str.contains(str(value), case=False, na=False)
        elif operator == 'starts_with':
            mask = df[column].astype(str).str.startswith(str(value))
        elif operator == 'ends_with':
            mask = df[column].astype(str).str.endswith(str(value))
        elif operator == 'is_null':
            mask = df[column].isnull()
        elif operator == 'not_null':
            mask = df[column].notnull()
        else:
            raise ValueError(f"Unknown operator: {operator}")
        
        return df[mask]
    
    def sort_data(self, column: str, ascending: bool = True) -> "pd.DataFrame":
        """Sort data by column."""
        if self.current_df is None:
            raise ValueError("No data loaded")
        
        return self.current_df.sort_values(by=column, ascending=ascending)
    
    def add_column(self, name: str, values: List = None, formula: str = None):
        """Add a new column."""
        if self.current_df is None:
            raise ValueError("No data loaded")
        
        if values is not None:
            self.current_df[name] = values
        elif formula is not None:
            # Simple formula evaluation (e.g., "col1 + col2")
            self.current_df[name] = self.current_df.eval(formula)
        else:
            self.current_df[name] = None
    
    def delete_column(self, name: str):
        """Delete a column."""
        if self.current_df is None:
            raise ValueError("No data loaded")
        
        self.current_df.drop(columns=[name], inplace=True)
    
    def rename_column(self, old_name: str, new_name: str):
        """Rename a column."""
        if self.current_df is None:
            raise ValueError("No data loaded")
        
        self.current_df.rename(columns={old_name: new_name}, inplace=True)
    
    def update_cell(self, row: int, column: str, value: Any):
        """Update a cell value."""
        if self.current_df is None:
            raise ValueError("No data loaded")
        
        self.current_df.at[row, column] = value
    
    def delete_rows(self, indices: List[int]):
        """Delete rows by index."""
        if self.current_df is None:
            raise ValueError("No data loaded")
        
        self.current_df.drop(index=indices, inplace=True)
        self.current_df.reset_index(drop=True, inplace=True)
    
    # ===== AI Analysis =====
    
    def analyze_with_ai(self, question: str) -> str:
        """Analyze data using AI."""
        if not self.api_service:
            raise ValueError("API service required for AI analysis")
        
        if self.current_df is None:
            raise ValueError("No data loaded")
        
        # Create data context
        summary = self.get_summary()
        sample = self.current_df.head(10).to_string()
        stats = self.get_statistics()
        
        context = f"""
Data Summary:
- Rows: {summary['rows']}
- Columns: {summary['columns']}
- Column names: {', '.join(summary['column_names'])}

Sample Data (first 10 rows):
{sample}

Statistics:
{json.dumps(stats, indent=2, default=str)}
"""
        
        prompt = f"""You are a data analyst. Analyze this data and answer the question.

{context}

Question: {question}

Provide a clear, insightful answer based on the data.
"""
        
        try:
            import replicate
            
            output = replicate.run(
                "anthropic/claude-sonnet-4",
                input={
                    "prompt": prompt,
                    "max_tokens": 1000
                }
            )
            
            return ''.join(output)
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            raise
    
    def generate_insights(self) -> List[str]:
        """Generate automatic insights about the data."""
        if self.current_df is None:
            return []
        
        df = self.current_df
        insights = []
        
        # Basic insights
        insights.append(f"📊 Dataset has {len(df)} rows and {len(df.columns)} columns")
        
        # Missing values
        missing = df.isnull().sum()
        if missing.any():
            cols_with_missing = missing[missing > 0]
            insights.append(f"⚠️ {len(cols_with_missing)} columns have missing values")
        else:
            insights.append("✅ No missing values in the dataset")
        
        # Numeric analysis
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            for col in numeric_cols[:3]:  # Top 3 numeric columns
                mean = df[col].mean()
                median = df[col].median()
                if abs(mean - median) / (median + 0.001) > 0.5:
                    insights.append(f"📈 '{col}' is skewed (mean: {mean:.2f}, median: {median:.2f})")
        
        # Unique values
        for col in df.columns:
            unique_ratio = df[col].nunique() / len(df)
            if unique_ratio == 1:
                insights.append(f"🔑 '{col}' might be an ID column (all unique values)")
            elif unique_ratio < 0.05:
                insights.append(f"🏷️ '{col}' might be a category ({df[col].nunique()} unique values)")
        
        # Duplicates
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            insights.append(f"🔁 Found {dup_count} duplicate rows ({dup_count/len(df)*100:.1f}%)")
        
        return insights


def render_spreadsheet_viewer_ui():
    """Render spreadsheet viewer UI in Streamlit."""
    import streamlit as st
    
    st.markdown("### 📊 Spreadsheet Viewer")
    
    if not PANDAS_AVAILABLE:
        st.error("pandas is required. Install with: pip install pandas openpyxl")
        return
    
    # Get API service
    api = None
    try:
        from platform_helpers import _get_replicate_token
        token = _get_replicate_token()
        if token:
            from api_service import ReplicateAPI
            api = ReplicateAPI(api_token=token)
    except:
        pass
    
    viewer = SpreadsheetViewer(api_service=api)
    
    # File upload
    uploaded = st.file_uploader(
        "Upload Spreadsheet",
        type=['csv', 'xlsx', 'xls', 'tsv', 'json']
    )
    
    if uploaded:
        try:
            df = viewer.load_from_bytes(uploaded.read(), uploaded.name)
            
            # Show summary
            summary = viewer.get_summary()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Rows", summary['rows'])
            with col2:
                st.metric("Columns", summary['columns'])
            with col3:
                st.metric("Numeric Cols", len(summary['numeric_columns']))
            with col4:
                st.metric("Text Cols", len(summary['text_columns']))
            
            # Tabs
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "View Data", "Statistics", "Filter & Sort", "Edit", "AI Analysis"
            ])
            
            with tab1:
                st.markdown("#### Data View")
                
                # Pagination
                rows_per_page = st.selectbox("Rows per page", [25, 50, 100, 500], index=0)
                total_pages = (len(df) - 1) // rows_per_page + 1
                page = st.number_input("Page", 1, total_pages, 1)
                
                start_idx = (page - 1) * rows_per_page
                end_idx = start_idx + rows_per_page
                
                st.dataframe(df.iloc[start_idx:end_idx], use_container_width=True)
                st.caption(f"Showing rows {start_idx+1} to {min(end_idx, len(df))} of {len(df)}")
            
            with tab2:
                st.markdown("#### Statistics")
                
                # Auto insights
                insights = viewer.generate_insights()
                with st.expander("📋 Auto-Generated Insights", expanded=True):
                    for insight in insights:
                        st.markdown(f"- {insight}")
                
                # Numeric stats
                stats = viewer.get_statistics()
                if stats:
                    st.markdown("##### Numeric Column Statistics")
                    stats_df = pd.DataFrame(stats).T
                    st.dataframe(stats_df, use_container_width=True)
                else:
                    st.info("No numeric columns found")
                
                # Value counts for categorical
                st.markdown("##### Value Counts")
                cat_col = st.selectbox("Select column", summary['text_columns'] or summary['column_names'])
                if cat_col:
                    counts = df[cat_col].value_counts().head(20)
                    st.bar_chart(counts)
            
            with tab3:
                st.markdown("#### Filter & Sort")
                
                # Filter
                st.markdown("##### Filter Data")
                filter_col = st.selectbox("Column to filter", summary['column_names'])
                filter_op = st.selectbox("Operator", [
                    '==', '!=', '>', '>=', '<', '<=',
                    'contains', 'starts_with', 'ends_with', 'is_null', 'not_null'
                ])
                
                if filter_op not in ['is_null', 'not_null']:
                    filter_val = st.text_input("Value")
                else:
                    filter_val = None
                
                if st.button("Apply Filter"):
                    try:
                        # Try to convert to number if possible
                        try:
                            filter_val = float(filter_val) if filter_val and '.' in filter_val else int(filter_val) if filter_val else filter_val
                        except:
                            pass
                        
                        filtered = viewer.filter_data(filter_col, filter_op, filter_val)
                        st.success(f"Found {len(filtered)} matching rows")
                        st.dataframe(filtered.head(100), use_container_width=True)
                    except Exception as e:
                        st.error(f"Filter failed: {e}")
                
                st.markdown("---")
                
                # Sort
                st.markdown("##### Sort Data")
                sort_col = st.selectbox("Column to sort by", summary['column_names'], key="sort_col")
                ascending = st.checkbox("Ascending", True)
                
                if st.button("Apply Sort"):
                    sorted_df = viewer.sort_data(sort_col, ascending)
                    st.dataframe(sorted_df.head(100), use_container_width=True)
            
            with tab4:
                st.markdown("#### Edit Data")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("##### Rename Column")
                    old_name = st.selectbox("Select column", summary['column_names'], key="rename_old")
                    new_name = st.text_input("New name")
                    
                    if new_name and st.button("Rename"):
                        viewer.rename_column(old_name, new_name)
                        st.success(f"Renamed '{old_name}' to '{new_name}'")
                        st.rerun()
                
                with col2:
                    st.markdown("##### Add Column")
                    add_name = st.text_input("Column name")
                    add_formula = st.text_input("Formula (e.g., col1 + col2)", placeholder="Leave empty for null values")
                    
                    if add_name and st.button("Add Column"):
                        try:
                            viewer.add_column(add_name, formula=add_formula if add_formula else None)
                            st.success(f"Added column '{add_name}'")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
                
                st.markdown("---")
                
                # Export
                st.markdown("##### Export Data")
                export_format = st.selectbox("Format", ['csv', 'xlsx', 'json'])
                
                if st.button("Export"):
                    data = viewer.to_bytes(export_format)
                    st.download_button(
                        f"Download .{export_format}",
                        data,
                        f"data.{export_format}",
                        type="primary"
                    )
            
            with tab5:
                st.markdown("#### AI Analysis")
                
                if not api:
                    st.warning("Add Replicate API key for AI analysis")
                else:
                    # Sample questions
                    st.markdown("**Sample Questions:**")
                    sample_questions = [
                        "What are the main trends in this data?",
                        "Which columns are most correlated?",
                        "What anomalies or outliers exist?",
                        "Summarize the key insights",
                        "What predictions can we make from this data?"
                    ]
                    
                    cols = st.columns(3)
                    selected_q = None
                    for i, q in enumerate(sample_questions[:3]):
                        with cols[i]:
                            if st.button(q, key=f"sample_q_{i}"):
                                selected_q = q
                    
                    question = st.text_input("Ask a question about the data", value=selected_q or "")
                    
                    if question and st.button("Analyze", type="primary"):
                        with st.spinner("Analyzing with AI..."):
                            try:
                                answer = viewer.analyze_with_ai(question)
                                st.markdown("##### Analysis Result")
                                st.markdown(answer)
                            except Exception as e:
                                st.error(f"Analysis failed: {e}")
        
        except Exception as e:
            st.error(f"Failed to load file: {e}")
    else:
        st.info("Upload a CSV, Excel, or JSON file to get started")
        
        # Example data
        if st.button("Load Example Data"):
            import numpy as np
            
            # Create sample data
            np.random.seed(42)
            data = {
                'Product': ['Widget A', 'Widget B', 'Gadget X', 'Gadget Y', 'Tool Z'] * 20,
                'Category': ['Electronics', 'Electronics', 'Home', 'Home', 'Tools'] * 20,
                'Price': np.random.uniform(10, 100, 100).round(2),
                'Quantity': np.random.randint(1, 50, 100),
                'Rating': np.random.uniform(3.0, 5.0, 100).round(1)
            }
            data['Revenue'] = [p * q for p, q in zip(data['Price'], data['Quantity'])]
            
            viewer.current_df = pd.DataFrame(data)
            st.success("Example data loaded!")
            st.rerun()
