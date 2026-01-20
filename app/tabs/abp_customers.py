from app.tabs.abp_imports_common import (
    st, Path, json, datetime, logging, setup_logger
)

logger = setup_logger(__name__)

def render_customers_tab():
    """
    Renders the Customers & Mailing List tab (Tab 13).
    """
    st.markdown('<div class="main-header">👥 Customers & Mailing List</div>', unsafe_allow_html=True)
    st.markdown("### Manage your customer database and email subscribers")
    
    # Local mailing list storage
    # Note: We use the parent directory of this file, assuming it's in the same dir as the main app
    MAILING_LIST_FILE = Path(__file__).parent / "mailing_list.json"
    
    def load_mailing_list_main():
        if MAILING_LIST_FILE.exists():
            try:
                with open(MAILING_LIST_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {"subscribers": [], "last_sync": None}
        return {"subscribers": [], "last_sync": None}
    
    def save_mailing_list_main(data):
        with open(MAILING_LIST_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    mailing_data = load_mailing_list_main()
    
    cust_tabs = st.tabs(["📊 Dashboard", "📧 Mailing List", "🛒 Shopify Sync", "➕ Add Subscribers"])
    
    with cust_tabs[0]:
        st.markdown("### 📊 Customer Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        local_count = len(mailing_data.get('subscribers', []))
        marketing_count = len([s for s in mailing_data.get('subscribers', []) if s.get('accepts_marketing', True)])
        
        # Try Shopify
        shopify_count = 0
        try:
            from shopify_service import ShopifyAPI
            shopify_svc = ShopifyAPI()
            if shopify_svc.connected:
                shopify_count = shopify_svc.get_customer_count()
        except:
            pass
        
        with col1:
            st.metric("📧 Mailing List", local_count)
        with col2:
            st.metric("🛒 Shopify Customers", shopify_count)
        with col3:
            st.metric("✅ Marketing Opt-in", marketing_count)
        with col4:
            last_sync = mailing_data.get('last_sync')
            st.metric("🔄 Last Sync", last_sync[:10] if last_sync else "Never")
    
    with cust_tabs[1]:
        st.markdown("### 📧 Mailing List")
        
        subscribers = mailing_data.get('subscribers', [])
        
        if subscribers:
            import pandas as pd
            df = pd.DataFrame(subscribers)
            
            # Filter
            search = st.text_input("🔍 Search", key="cust_search_main")
            if search:
                df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
            
            st.dataframe(df, use_container_width=True, height=400)
            
            # Export
            if st.button("📥 Export CSV", key="export_csv_main"):
                csv = df.to_csv(index=False)
                st.download_button("Download CSV", csv, "mailing_list.csv", "text/csv")
        else:
            st.info("No subscribers yet. Add them manually or sync from Shopify!")
    
    with cust_tabs[2]:
        st.markdown("### 🛒 Sync from Shopify")
        
        try:
            from shopify_service import ShopifyAPI
            shopify_svc = ShopifyAPI()
            
            if shopify_svc.connected:
                st.success("✅ Shopify connected")
                
                # Sync options
                sync_col1, sync_col2 = st.columns(2)
                with sync_col1:
                    marketing_only = st.checkbox("Marketing subscribers only", value=True, key="marketing_only_sync")
                with sync_col2:
                    sync_limit = st.number_input("Max customers", min_value=10, max_value=1000, value=250, step=50)
                
                if st.button("🔄 Sync Customers Now", type="primary", key="sync_shopify_main"):
                    try:
                        with st.spinner("Syncing customers from Shopify..."):
                            customers = shopify_svc.get_all_customers(limit=sync_limit)
                            
                            if not customers:
                                st.warning("No customers found")
                            else:
                                existing_emails = {s['email'].lower() for s in mailing_data.get('subscribers', [])}
                                new_count = 0
                                updated_count = 0
                                
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                for idx, customer in enumerate(customers):
                                    progress = (idx + 1) / len(customers)
                                    progress_bar.progress(progress)
                                    status_text.text(f"Processing {idx + 1}/{len(customers)}...")
                                    
                                    email = customer.get('email', '').lower()
                                    if not email:
                                        continue
                                    
                                    if marketing_only and not customer.get('accepts_marketing', False):
                                        continue
                                    
                                    subscriber_data = {
                                        'email': email,
                                        'first_name': customer.get('first_name', ''),
                                        'last_name': customer.get('last_name', ''),
                                        'accepts_marketing': customer.get('accepts_marketing', False),
                                        'source': 'shopify',
                                        'shopify_id': customer.get('id'),
                                        'orders_count': customer.get('orders_count', 0),
                                        'total_spent': customer.get('total_spent', '0.00'),
                                        'tags': customer.get('tags', ''),
                                        'added_date': datetime.now().isoformat(),
                                        'last_sync': datetime.now().isoformat()
                                    }
                                    
                                    if email not in existing_emails:
                                        mailing_data['subscribers'].append(subscriber_data)
                                        existing_emails.add(email)
                                        new_count += 1
                                    else:
                                        for sub in mailing_data['subscribers']:
                                            if sub['email'].lower() == email:
                                                sub.update(subscriber_data)
                                                updated_count += 1
                                                break
                                
                                progress_bar.empty()
                                status_text.empty()
                                
                                mailing_data['last_sync'] = datetime.now().isoformat()
                                mailing_data['shopify_sync_count'] = mailing_data.get('shopify_sync_count', 0) + 1
                                save_mailing_list_main(mailing_data)
                                
                                st.success(f"✅ Added {new_count} new, updated {updated_count} existing")
                                if new_count > 0 or updated_count > 0:
                                    st.rerun()
                    
                    except Exception as e:
                        st.error(f"Sync failed: {str(e)}")
                        logger.error(f"Shopify sync error: {e}", exc_info=True)
                
                if mailing_data.get('last_sync'):
                    st.caption(f"Last synced: {mailing_data['last_sync'][:19]}")
            else:
                st.warning("⚠️ Shopify not connected. Add credentials in Settings → Integrations.")
        except ImportError as e:
            st.error(f"⚠️ Shopify service not available: {e}")
            st.info("Install shopify_service.py")
    
    with cust_tabs[3]:
        st.markdown("### ➕ Add Subscribers")
        
        add_method = st.radio("Add method:", ["Single", "Bulk Paste", "CSV Upload"], horizontal=True, key="add_method_main")
        
        if add_method == "Single":
            col1, col2 = st.columns(2)
            with col1:
                new_email = st.text_input("Email", key="new_email_main")
                new_fname = st.text_input("First Name", key="new_fname_main")
            with col2:
                new_lname = st.text_input("Last Name", key="new_lname_main")
                accepts_marketing = st.checkbox("Accepts Marketing", value=True, key="accepts_mkt_main")
            
            if st.button("➕ Add Subscriber", type="primary", key="add_single_main"):
                if new_email:
                    mailing_data['subscribers'].append({
                        'email': new_email,
                        'first_name': new_fname,
                        'last_name': new_lname,
                        'accepts_marketing': accepts_marketing,
                        'source': 'manual',
                        'added_date': datetime.now().isoformat()
                    })
                    save_mailing_list_main(mailing_data)
                    st.success(f"✅ Added {new_email}")
                    st.rerun()
        
        elif add_method == "Bulk Paste":
            bulk_emails = st.text_area("Paste emails (one per line)", key="bulk_emails_main", height=150)
            
            if st.button("➕ Add All", type="primary", key="add_bulk_main"):
                emails = [e.strip() for e in bulk_emails.split('\n') if '@' in e]
                for email in emails:
                    if email:
                        mailing_data['subscribers'].append({
                            'email': email,
                            'accepts_marketing': True,
                            'source': 'bulk_import',
                            'added_date': datetime.now().isoformat()
                        })
                save_mailing_list_main(mailing_data)
                st.success(f"✅ Added {len(emails)} subscribers")
                st.rerun()
        
        else:  # CSV Upload
            csv_file = st.file_uploader("Upload CSV (must have 'email' column)", type=['csv'], key="csv_upload_main")
            if csv_file:
                import pandas as pd
                df = pd.read_csv(csv_file)
                if 'email' in df.columns:
                    emails = df['email'].dropna().tolist()
                    for email in emails:
                        mailing_data['subscribers'].append({
                            'email': str(email),
                            'accepts_marketing': True,
                            'source': 'csv_import',
                            'added_date': datetime.now().isoformat()
                        })
                    save_mailing_list_main(mailing_data)
                    st.success(f"✅ Imported {len(emails)} subscribers")
                    st.rerun()
                else:
                    st.error("CSV must have an 'email' column")
