import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from difflib import SequenceMatcher
import warnings
from datetime import datetime
import re
from scipy.spatial import cKDTree
import os

warnings.filterwarnings('ignore')

# --- HELPER FUNCTIONS ---

def clean_coordinate(value):
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float)):
        return round(float(value), 6)
    try:
        cleaned = str(value).strip().replace(',', '')
        return round(float(cleaned), 6)
    except:
        return np.nan

def normalize_phone(phone):
    if pd.isna(phone):
        return ''
    digits = re.sub(r'\D', '', str(phone))
    return digits[-10:] if len(digits) > 10 else digits

def phone_digit_diff(phone1, phone2):
    p1 = normalize_phone(phone1)
    p2 = normalize_phone(phone2)
    if not p1 or not p2:
        return False, 999
    if len(p1) != len(p2):
        return False, 999
    diff = sum(c1 != c2 for c1, c2 in zip(p1, p2))
    if diff <= 1:
        return True, diff
    return False, diff

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate exact distance in meters between two coordinates"""
    R = 6371000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

# ✅ UPDATED: Only filter "Che" and "ចែ"
def clean_shop_name(name):
    """
    Remove only 'Che' and 'ចែ' from shop names before comparison
    These cause the most false positives
    """
    if pd.isna(name) or not name:
        return ''
    
    name = str(name).lower().strip()
    
    # Remove "Che" and "ចែ" (with spaces to avoid partial matches)
    noise_words = ['che ', 'che', 'ចែ ', 'ចែ']
    
    for noise in noise_words:
        name = name.replace(noise, '').strip()
    
    # Clean up extra spaces
    name = ' '.join(name.split()).strip()
    
    return name if name else str(name).strip()

def name_similarity(str1, str2):
    if pd.isna(str1) or pd.isna(str2):
        return 0
    # ✅ CLEAN names before comparing (removes Che/ចែ)
    s1 = clean_shop_name(str1)
    s2 = clean_shop_name(str2)
    if not s1 or not s2:
        return 0
    return SequenceMatcher(None, s1, s2).ratio() * 100

def is_new_shop(row):
    pc = row.get('prospect_code')
    if pd.isna(pc):
        return True
    pc_str = str(pc).strip().lower()
    return pc_str in ['', 'nan', 'null', 'none']

def get_shop_name(row, is_master=False, name_col='customer_name_en'):
    """
    Get shop name - dynamically uses the correct column
    Master_Data: shop_name_en → customer_name_kh
    New_File: customer_name_en → customer_name_kh
    """
    if is_master:
        # Try shop_name_en first (Master_Data)
        name = row.get('shop_name_en', '')
        if pd.isna(name) or str(name).strip() == '':
            name = row.get('customer_name_kh', '')
    else:
        # New file uses customer_name_en
        name = row.get(name_col, '')
        if pd.isna(name) or str(name).strip() == '':
            name = row.get('customer_name_kh', '')
    return str(name).strip() if name else ''

# --- MAIN FUNCTION ---

def find_duplicate_shops(yesterday_file, today_file, output_file):
    print("="*70)
    print("🚀 LOADING FILES & BUILDING KD-TREE")
    print("="*70)
    
    # Load Data
    df_yesterday = pd.read_excel(yesterday_file, dtype=str)
    df_today = pd.read_excel(today_file, dtype=str)
    
    print(f"\n📋 Master_Data columns: {list(df_yesterday.columns)}")
    print(f"📋 New_File columns: {list(df_today.columns)}")
    
    # Check required columns
    required_cols = ['latitude', 'longitude', 'prospect_code', 'cust_ID']
    for col in required_cols:
        if col not in df_yesterday.columns:
            print(f"❌ ERROR: '{col}' not found in Master_Data.xlsx")
            return
        if col not in df_today.columns:
            print(f"❌ ERROR: '{col}' not found in new.xlsx")
            return
    
    # Find phone column dynamically (handles 'Phone', 'phone', 'PHONE', etc.)
    phone_col = None
    for col in df_today.columns:
        if 'phone' in col.lower():
            phone_col = col
            break
    
    if phone_col:
        print(f"✅ Found phone column: '{phone_col}'")
    else:
        print("⚠️  WARNING: No phone column found!")
    
    # Find shop name column for new file
    name_col = None
    for col in df_today.columns:
        if 'customer_name_en' in col.lower() or 'shop_name_en' in col.lower():
            name_col = col
            break
    
    if name_col:
        print(f"✅ Found shop name column: '{name_col}'")
    else:
        print("⚠️  WARNING: No shop name column found!")
        name_col = 'customer_name_en'  # Default fallback
    
    # Clean Coordinates
    for col in ['latitude', 'longitude']:
        df_yesterday[col] = pd.to_numeric(df_yesterday[col], errors='coerce')
        df_today[col] = pd.to_numeric(df_today[col], errors='coerce')

    # Filter Master Data
    df_master_valid = df_yesterday.dropna(subset=['latitude', 'longitude']).copy()
    df_master_valid = df_master_valid.reset_index(drop=True)
    
    if df_master_valid.empty:
        print("❌ Error: Master data has no valid coordinates!")
        return

    print(f"\n   📍 Building spatial index for {len(df_master_valid)} existing shops...")
    
    mean_lat = df_master_valid['latitude'].mean()
    factor_lat = 111320 
    factor_lon = 111320 * np.cos(np.radians(mean_lat))
    
    df_master_valid['x'] = df_master_valid['latitude'] * factor_lat
    df_master_valid['y'] = df_master_valid['longitude'] * factor_lon
    
    tree_data = df_master_valid[['x', 'y']].values
    tree = cKDTree(tree_data)
    
    # Identify new shops
    print("\n🔍 Identifying new shops...")
    new_shops = df_today[df_today.apply(is_new_shop, axis=1)].copy()
    new_shops = new_shops.dropna(subset=['latitude', 'longitude']).copy()
    new_shops = new_shops.reset_index(drop=True)
    
    print(f"✅ Found {len(new_shops)} new shops to check")
    
    if new_shops.empty:
        print("No new shops to process.")
        return

    new_shops['x'] = new_shops['latitude'] * factor_lat
    new_shops['y'] = new_shops['longitude'] * factor_lon
    
    for col in ['duplicate_remark', 'matched_prospect_code', 'matched_customer_name', 'distance_meters', 'name_similarity_%']:
        new_shops[col] = ''
    
    results = []
    debug_log = []
    clean_shops = []
    
    # ✅ Track ALL new shop cust_IDs for the Review List sheet
    flagged_shop_ids = set()
    
    print(f"\n⚡ Running Spatial Search (Radius: 20m)...")
    
    nearby_indices = tree.query_ball_point(new_shops[['x', 'y']].values, r=20.0)
    
    print(f"   🔎 Found potential location matches. Processing details...")
    
    # Pre-build Phone Dictionary
    print("   📞 Building phone lookup dictionary...")
    phone_dict = {}
    for i, row in df_master_valid.iterrows():
        pn = normalize_phone(row.get(phone_col, '')) if phone_col else ''
        if pn:
            if pn not in phone_dict:
                phone_dict[pn] = []
            phone_dict[pn].append({
                'index': i,
                'shop': row
            })
    
    for i, idx_new in enumerate(new_shops.index):
        new_shop = new_shops.loc[idx_new]
        new_lat = new_shop['latitude']
        new_lon = new_shop['longitude']
        new_name = get_shop_name(new_shop, is_master=False, name_col=name_col)
        
        raw_phone = ''
        if phone_col:
            raw_phone = str(new_shop.get(phone_col, ''))
        new_phone = normalize_phone(raw_phone)
        
        new_cust_id = str(new_shop.get('cust_ID', '')).strip()
        
        remarks = []
        matched = {}
        location_found = False
        
        master_indices = nearby_indices[i]
        
        if master_indices:
            for pos_idx in master_indices:
                old_shop = df_master_valid.iloc[pos_idx]
                
                old_lat = old_shop['latitude']
                old_lon = old_shop['longitude']
                old_name = get_shop_name(old_shop, is_master=True)
                old_phone_raw = str(old_shop.get(phone_col, '')) if phone_col else ''
                old_prospect = str(old_shop.get('prospect_code', '')).strip()
                old_cust_id = str(old_shop.get('cust_ID', '')).strip()
                
                dist = haversine_distance(new_lat, new_lon, old_lat, old_lon)
                
                if pd.isna(dist) or dist > 20: 
                    continue
                
                sim = name_similarity(new_name, old_name)
                
                debug_log.append({
                    'new_name': new_name,
                    'new_cust_id': new_cust_id,
                    'new_coords': f"{new_lat:.6f},{new_lon:.6f}",
                    'old_shop_name': old_name,
                    'old_prospect': old_prospect,
                    'old_cust_id': old_cust_id,
                    'old_coords': f"{old_lat:.6f},{old_lon:.6f}",
                    'distance_m': round(dist, 3),
                    'name_similarity_%': round(sim, 2),
                    'exact_coords': (round(new_lat, 6) == round(old_lat, 6) and round(new_lon, 6) == round(old_lon, 6)),
                    'cleaned_new_name': clean_shop_name(new_name),
                    'cleaned_old_name': clean_shop_name(old_name)
                })
                
                location_found = True
                if sim >= 65:
                    remark = f"SERIOUS_DUPLICATE:{old_prospect}:dist={dist:.1f}m:sim={sim:.1f}%"
                    remark_type = 'SERIOUS'
                else:
                    remark = f"SUSPICION:{old_prospect}:dist={dist:.1f}m"
                    remark_type = 'SUSPICION'
                
                remarks.append(remark)
                
                if not matched:
                    matched = {
                        'prospect': old_prospect,
                        'cust_id': old_cust_id,
                        'name': old_name,
                        'distance': f"{dist:.1f}",
                        'similarity': f"{sim:.1f}"
                    }
                
                results.append({
                    'new_prospect_code': 'NULL',
                    'new_cust_id': new_cust_id,
                    'new_customer_name': new_name,
                    'new_phone': raw_phone,
                    'new_latitude': new_lat,
                    'new_longitude': new_lon,
                    'old_prospect_code': old_prospect,
                    'old_cust_id': old_cust_id,
                    'old_shop_name': old_name,
                    'old_phone': old_phone_raw,
                    'distance_meters': round(dist, 3),
                    'name_similarity_%': round(sim, 2),
                    'remark_type': remark_type,
                    'match_method': 'LOCATION'
                })
        
        # Phone Fallback
        if not location_found and phone_col and new_phone:
            if new_phone in phone_dict:
                for entry in phone_dict[new_phone]:
                    old_shop = entry['shop']
                    
                    old_pn_normalized = normalize_phone(entry['shop'].get(phone_col, ''))
                    is_match, diff_count = phone_digit_diff(new_phone, old_pn_normalized)
                    
                    if is_match:
                        old_prospect = str(old_shop.get('prospect_code', '')).strip()
                        old_cust_id = str(old_shop.get('cust_ID', '')).strip()
                        old_name = get_shop_name(old_shop, is_master=True)
                        
                        if diff_count == 0:
                            remark = f"PHONE_DUPLICATE:{old_prospect}"
                            remark_type = 'PHONE_DUPLICATE'
                        else:
                            remark = f"SIMILAR_PHONE:{old_prospect}(diff={diff_count})"
                            remark_type = 'SIMILAR_PHONE'
                        
                        remarks.append(remark)
                        
                        if not matched:
                            matched = {
                                'prospect': old_prospect,
                                'cust_id': old_cust_id,
                                'name': old_name,
                                'distance': 'N/A',
                                'similarity': f"{name_similarity(new_name, old_name):.1f}"
                            }
                        
                        results.append({
                            'new_prospect_code': 'NULL',
                            'new_cust_id': new_cust_id,
                            'new_customer_name': new_name,
                            'new_phone': raw_phone,
                            'new_latitude': new_lat,
                            'new_longitude': new_lon,
                            'old_prospect_code': old_prospect,
                            'old_cust_id': old_cust_id,
                            'old_shop_name': old_name,
                            'old_phone': old_shop.get(phone_col, ''),
                            'distance_meters': 'N/A',
                            'name_similarity_%': round(name_similarity(new_name, old_name), 2),
                            'remark_type': remark_type,
                            'match_method': 'PHONE',
                            'phone_diff_digits': diff_count
                        })
                        break
        
        if remarks:
            new_shops.at[idx_new, 'duplicate_remark'] = '; '.join(remarks)
            new_shops.at[idx_new, 'matched_prospect_code'] = matched.get('prospect', '')
            new_shops.at[idx_new, 'matched_customer_name'] = matched.get('name', '')
            new_shops.at[idx_new, 'distance_meters'] = matched.get('distance', '')
            new_shops.at[idx_new, 'name_similarity_%'] = matched.get('similarity', '')
            # ✅ Track this shop as flagged
            flagged_shop_ids.add(new_cust_id)
        else:
            clean_shops.append({
                'cust_ID': new_cust_id,
                'customer_name_en': new_name,
                'phone': raw_phone,
                'province': new_shop.get('province', ''),
                'district': new_shop.get('district', ''),
                'commune': new_shop.get('commune', ''),
                'latitude': new_lat,
                'longitude': new_lon,
                'recommendation': 'APPROVE - Convert to Code P',
                'status': 'CLEAN'
            })
    
    # Save Results
    results_df = pd.DataFrame(results)
    flagged = new_shops[new_shops['duplicate_remark'] != ''].copy()
    debug_df = pd.DataFrame(debug_log)
    clean_df = pd.DataFrame(clean_shops)
    
    # ✅ CREATE NEW SHEET: New_Shops_Review_List
    # This contains ALL new shops that are NOT clean (need manual review)
    review_list = new_shops.copy()
    review_list['review_status'] = review_list['cust_ID'].apply(
        lambda x: 'IN_DETAILED_COMPARISON' if x in flagged_shop_ids else 'NEEDS_REVIEW'
    )
    
    # ✅ FIX: Use detected column names dynamically
    review_cols = [
        'cust_ID', 
        name_col,
        phone_col if phone_col else 'Phone',
        'province', 
        'district', 
        'commune', 
        'latitude', 
        'longitude', 
        'duplicate_remark', 
        'matched_prospect_code', 
        'matched_customer_name', 
        'review_status'
    ]
    
    # Only include columns that actually exist
    available_review_cols = [c for c in review_cols if c in review_list.columns]
    review_list = review_list[available_review_cols]
    
    # Rename columns for cleaner output
    rename_map = {name_col: 'customer_name_en', phone_col: 'phone'} if phone_col else {name_col: 'customer_name_en'}
    rename_map = {k: v for k, v in rename_map.items() if k in review_list.columns}
    review_list = review_list.rename(columns=rename_map)
    
    # ✅ Generate SQL INSERT statements for flagged shops
    print("   📝 Generating SQL INSERT statements...")
    if not flagged.empty:
        sql_statements = []
        processed_ids = set()  # Avoid duplicates
        for _, row in flagged.iterrows():
            cust_id = str(row.get('cust_ID', '')).strip()
            if cust_id and cust_id not in processed_ids and cust_id.lower() not in ['nan', 'null', 'none', '']:
                sql = f'Insert into dbo.DQ_Customer_ID_Issue([Cust_ID],[DateTime],[Issue_Type]) values ({cust_id}, GETDATE(),"Suspect Duplicate");'
                sql_statements.append(sql)
                processed_ids.add(cust_id)
        
        sql_df = pd.DataFrame({'SQL_Insert_Statements': sql_statements})
        print(f"   ✅ Generated {len(sql_statements)} SQL INSERT statements")
    else:
        sql_df = pd.DataFrame({'SQL_Insert_Statements': ['-- No duplicates found']})
    
    print(f"\n💾 Saving to {output_file}...")
    
    # ✅ Automatically create Results folder if missing
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    if os.path.exists(output_file):
        try:
            os.remove(output_file)
        except PermissionError:
            print("   ⚠️ Warning: Could not delete existing file. Please close the output file and try again.")
            return

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Sheet 1: Flagged new shops
        (flagged if not flagged.empty else pd.DataFrame({'Message': ['No duplicates']}))\
            .to_excel(writer, sheet_name='New_Shop_Duplicates', index=False)
        
        # Sheet 2: Detailed comparison
        if not results_df.empty:
            cols = ['new_cust_id', 'old_cust_id', 'new_prospect_code', 'old_prospect_code',
                   'new_customer_name', 'old_shop_name', 'new_phone', 'old_phone',
                   'distance_meters', 'name_similarity_%', 'remark_type', 'match_method']
            available_cols = [c for c in cols if c in results_df.columns]
            results_df[available_cols].to_excel(writer, sheet_name='Detailed_Comparison', index=False)
        else:
            pd.DataFrame({'Message': ['No matches']}).to_excel(writer, sheet_name='Detailed_Comparison', index=False)
        
        # Sheet 3: Debug log
        (debug_df if not debug_df.empty else pd.DataFrame({'Message': ['No close locations']}))\
            .to_excel(writer, sheet_name='DEBUG_Within_20m', index=False)
        
        # Sheet 4: Convert to Code P (clean shops)
        (clean_df if not clean_df.empty else pd.DataFrame({'Message': ['No clean shops - all require review']}))\
            .to_excel(writer, sheet_name='Convert_to_Code_P', index=False)
        
        # Sheet 5: NEW - Review List (All new shops needing attention)
        (review_list if not review_list.empty else pd.DataFrame({'Message': ['No shops need review']}))\
            .to_excel(writer, sheet_name='New_Shops_Review_List', index=False)
        
        # Sheet 6: Summary
        pd.DataFrame({
            'Metric': [
                'Total New Shops', 
                'Flagged for Review', 
                'Clean Shops (Convert to Code P)',
                'Shops in Review List',
                'By Location', 
                'By Phone (exact)', 
                'By Phone (1 digit typo)'
            ],
            'Count': [
                len(new_shops), 
                len(flagged), 
                len(clean_df),
                len(review_list),
                len(results_df[results_df['match_method']=='LOCATION']) if not results_df.empty else 0,
                len(results_df[results_df['remark_type']=='PHONE_DUPLICATE']) if not results_df.empty else 0,
                len(results_df[results_df['remark_type']=='SIMILAR_PHONE']) if not results_df.empty else 0
            ]
        }).to_excel(writer, sheet_name='Summary', index=False)
        
        # ✅ Sheet 7: SQL INSERT Statements for DQ Issue tracking
        sql_df.to_excel(writer, sheet_name='DQ_Issue_SQL', index=False)
    
    print(f"\n✅ Done! Flagged: {len(flagged)} shops | Clean: {len(clean_df)} shops | Review List: {len(review_list)} shops")
    print(f"⚡ Performance: Spatial search completed efficiently using KDTree.")
    return flagged, results_df, debug_df, clean_df

if __name__ == "__main__":
    yesterday_file = r'Source\Master_Data.xlsx'
    today_file = r'Source\New_Data.xlsx'
    output_file = f'Results\duplicate_analysis_results_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    try:
        flagged, details, debug, clean_df = find_duplicate_shops(yesterday_file, today_file, output_file)
        
        if not flagged.empty:
            print("\n" + "="*70)
            print("⚠️  FLAGGED SHOPS:")
            print("="*70)
            for _, row in flagged.head(10).iterrows():
                phone_val = row.get('phone', row.get('Phone', 'N/A'))
                name_val = row.get('customer_name_en', row.get('shop_name_en', 'Unknown'))
                print(f"\n📍 {name_val}")
                print(f"   📞 {phone_val}")
                print(f"   ❗ {row['duplicate_remark']}")
                print(f"   → Match: {row['matched_customer_name']} (ID: {row['matched_prospect_code']})")
            
            if len(flagged) > 10:
                print(f"\n   ... and {len(flagged) - 10} more flagged shops")
        
        if not clean_df.empty:
            print("\n" + "="*70)
            print("✅ CLEAN SHOPS (Convert to Code P):")
            print("="*70)
            print(f"   Total: {len(clean_df)} shops approved")
            for _, row in clean_df.head(5).iterrows():
                print(f"   • {row['customer_name_en']} ({row['cust_ID']})")
            if len(clean_df) > 5:
                print(f"   ... and {len(clean_df) - 5} more")
        else:
            print("\n⚠️  No clean shops - all require review")
                
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()