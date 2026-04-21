import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from difflib import SequenceMatcher
import warnings
from datetime import datetime
import re
from scipy.spatial import cKDTree
import os
import shutil

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

CONFIG = {
    'DISTANCE_THRESHOLD_METERS': 20,  # GPS-based duplicate detection radius
    
    # NAME SIMILARITY THRESHOLDS
    # Higher = stricter matching (fewer false positives, might miss typos)
    # Lower = looser matching (catches typos, but more false positives)
    'NAME_SIMILARITY_SERIOUS': 65,     # Strong evidence of duplicate (used with location match)
    'NAME_SIMILARITY_SUSPICION': 40,   # Low similarity but close location = needs review
    
    # PHONE MATCHING
    'PHONE_EXACT_MATCH': True,         # Require exact phone match for PHONE_DUPLICATE flag
    'PHONE_TYPO_TOLERANCE': 1,         # Allow 1-digit difference (typo detection)
    
    # OUTPUT
    'BACKUP_MASTER_DATA': True,        # Create backup before merging
    'AUTO_MERGE_CLEAN_SHOPS': True,    # Auto-add clean shops to Master_Data
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clean_coordinate(value):
    """Convert coordinate to float, handling various input formats"""
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
    """
    Normalize phone number to digits only, keeping last 10 digits
    Example: +855 12 345 678 -> 0123456789
    """
    if pd.isna(phone):
        return ''
    digits = re.sub(r'\D', '', str(phone))
    return digits[-10:] if len(digits) > 10 else digits

def phone_digit_diff(phone1, phone2):
    """
    Compare two phone numbers and count digit differences
    Returns: (is_match, difference_count)
    - Exact match: (True, 0)
    - 1-digit typo: (True, 1)
    - Different numbers: (False, 999)
    """
    p1 = normalize_phone(phone1)
    p2 = normalize_phone(phone2)
    if not p1 or not p2:
        return False, 999
    if len(p1) != len(p2):
        return False, 999
    diff = sum(c1 != c2 for c1, c2 in zip(p1, p2))
    if diff <= CONFIG['PHONE_TYPO_TOLERANCE']:
        return True, diff
    return False, diff

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate exact distance in meters between two GPS coordinates
    Uses Haversine formula for Earth's curvature
    """
    R = 6371000  # Earth radius in meters
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def clean_shop_name(name):
    """
    Remove noise words that cause false positives in Khmer shop names
    
    WHY: "Che" (ចែ) is a common prefix meaning "seller of" in Khmer
    Example: "Che Coffee" vs "Che Cake" are different shops, but
    after removing "Che", both become "Coffee" vs "Cake" which improves matching
    
    CAUTION: Only removes very common noise words to avoid over-cleaning
    """
    if pd.isna(name) or not name:
        return ''
    
    name = str(name).lower().strip()
    
    # Remove only "Che" and "ចែ" (most common false positive triggers)
    noise_words = ['che ', 'che', 'ចែ ', 'ចែ']
    
    for noise in noise_words:
        name = name.replace(noise, '').strip()
    
    # Clean up extra spaces
    name = ' '.join(name.split()).strip()
    
    return name if name else str(name).strip()

def name_similarity(str1, str2):
    """
    Calculate similarity between shop names (0-100%)
    
    ALGORITHM: SequenceMatcher uses Gestalt Pattern Matching
    - Looks for longest common substrings
    - Accounts for word order
    - Case-insensitive after cleaning
    
    THRESHOLDS (configurable):
    - 65%+ with location match = SERIOUS_DUPLICATE
    - 40-64% with location match = SUSPICION (needs manual review)
    - <40% with location match = Different shops, same location (building/plaza)
    
    EXAMPLES:
    - "ABC Coffee Shop" vs "ABC Coffee" = ~85% (likely same)
    - "ABC Coffee" vs "ABC Cake" = ~60% (suspicious, needs review)
    - "ABC Coffee" vs "XYZ Coffee" = ~45% (different shops)
    
    NOTE: Khmer names may need lower thresholds due to Unicode variations
    """
    if pd.isna(str1) or pd.isna(str2):
        return 0
    
    # Clean names before comparing (removes noise words)
    s1 = clean_shop_name(str1)
    s2 = clean_shop_name(str2)
    
    if not s1 or not s2:
        return 0
    
    return SequenceMatcher(None, s1, s2).ratio() * 100

def is_new_shop(row):
    """
    Identify if a shop is NEW (needs duplicate checking)
    NEW = prospect_code is NULL/empty/NaN
    """
    pc = row.get('prospect_code')
    if pd.isna(pc):
        return True
    pc_str = str(pc).strip().lower()
    return pc_str in ['', 'nan', 'null', 'none']

def get_shop_name(row, is_master=False, name_col='customer_name_en'):
    """
    Get shop name with fallback to Khmer name
    Priority: English name -> Khmer name
    """
    if is_master:
        # Master_Data uses 'shop_name_en'
        name = row.get('shop_name_en', '')
        if pd.isna(name) or str(name).strip() == '':
            name = row.get('customer_name_kh', '')
    else:
        # New_Data uses 'customer_name_en'
        name = row.get(name_col, '')
        if pd.isna(name) or str(name).strip() == '':
            name = row.get('customer_name_kh', '')
    return str(name).strip() if name else ''

def categorize_duplicate(distance, name_sim, match_method):
    """
    Categorize duplicate severity for better decision-making
    
    CATEGORIES:
    1. CRITICAL_DUPLICATE: Very high confidence - likely same shop
       - Exact phone match, OR
       - Close location (<5m) + high name similarity (>80%)
    
    2. SERIOUS_DUPLICATE: High confidence - needs verification
       - Location match (<20m) + good name similarity (>65%)
    
    3. SUSPICION: Moderate concern - manual review needed
       - Location match (<20m) + low name similarity (40-65%)
       - Could be different shops in same building/plaza
    
    4. PHONE_ONLY: Phone matched but no location data
       - Needs manual verification (could be data entry error)
    """
    if match_method == 'PHONE':
        return 'CRITICAL_DUPLICATE'
    
    if distance != 'N/A':
        dist = float(distance)
        if dist < 5 and name_sim > 80:
            return 'CRITICAL_DUPLICATE'
        elif name_sim >= CONFIG['NAME_SIMILARITY_SERIOUS']:
            return 'SERIOUS_DUPLICATE'
        elif name_sim >= CONFIG['NAME_SIMILARITY_SUSPICION']:
            return 'SUSPICION'
        else:
            return 'LOW_SUSPICION'
    
    return 'SUSPICION'

# ============================================================================
# MAIN DUPLICATE DETECTION FUNCTION
# ============================================================================

def find_duplicate_shops(master_file, new_file, output_file):
    """
    Main function to detect duplicate shops between Master_Data and New_Data
    
    WORKFLOW:
    1. Load both files and validate structure
    2. Build spatial index (KDTree) for fast location search
    3. Identify new shops (prospect_code = NULL)
    4. For each new shop:
       a. Search for nearby existing shops (<20m)
       b. Calculate name similarity
       c. Check phone match (if available)
       d. Categorize duplicate severity
    5. Generate output sheets:
       - Flagged duplicates (manual review needed)
       - Clean shops (auto-approve for Code P)
       - Review list with recommendations
    """
    
    print("="*70)
    print("🚀 DUPLICATE DETECTION SYSTEM v2.0")
    print("="*70)
    print(f"⚙️  Configuration:")
    print(f"   - Distance threshold: {CONFIG['DISTANCE_THRESHOLD_METERS']}m")
    print(f"   - Name similarity (SERIOUS): {CONFIG['NAME_SIMILARITY_SERIOUS']}%")
    print(f"   - Name similarity (SUSPICION): {CONFIG['NAME_SIMILARITY_SUSPICION']}%")
    print(f"   - Auto-merge clean shops: {CONFIG['AUTO_MERGE_CLEAN_SHOPS']}")
    print("="*70)
    
    # ========================================================================
    # STEP 1: LOAD AND VALIDATE DATA
    # ========================================================================
    
    print("\n📂 Loading files...")
    df_master = pd.read_excel(master_file, dtype=str)
    df_new = pd.read_excel(new_file, dtype=str)
    
    print(f"   ✅ Master_Data: {len(df_master)} shops")
    print(f"   ✅ New_Data: {len(df_new)} shops")
    
    # Check required columns
    required_cols = ['latitude', 'longitude', 'prospect_code', 'cust_ID']
    for col in required_cols:
        if col not in df_master.columns:
            print(f"   ❌ ERROR: '{col}' not found in Master_Data.xlsx")
            return None, None, None, None
        if col not in df_new.columns:
            print(f"   ❌ ERROR: '{col}' not found in New_Data.xlsx")
            return None, None, None, None
    
    # Dynamically detect column names
    phone_col = next((col for col in df_new.columns if 'phone' in col.lower()), None)
    name_col = next((col for col in df_new.columns 
                     if 'customer_name_en' in col.lower() or 'shop_name_en' in col.lower()), 
                    'customer_name_en')
    
    print(f"   📞 Phone column: {phone_col or 'NOT FOUND'}")
    print(f"   🏪 Name column: {name_col}")
    
    # Clean coordinates
    for col in ['latitude', 'longitude']:
        df_master[col] = pd.to_numeric(df_master[col], errors='coerce')
        df_new[col] = pd.to_numeric(df_new[col], errors='coerce')
    
    # ========================================================================
    # STEP 2: BUILD SPATIAL INDEX (KDTree)
    # ========================================================================
    
    print("\n🗺️  Building spatial index...")
    df_master_valid = df_master.dropna(subset=['latitude', 'longitude']).copy()
    df_master_valid = df_master_valid.reset_index(drop=True)
    
    if df_master_valid.empty:
        print("   ❌ Error: Master data has no valid coordinates!")
        return None, None, None, None
    
    # Convert GPS coordinates to meters for KDTree
    mean_lat = df_master_valid['latitude'].mean()
    factor_lat = 111320  # meters per degree latitude
    factor_lon = 111320 * np.cos(np.radians(mean_lat))  # meters per degree longitude
    
    df_master_valid['x'] = df_master_valid['latitude'] * factor_lat
    df_master_valid['y'] = df_master_valid['longitude'] * factor_lon
    
    tree_data = df_master_valid[['x', 'y']].values
    tree = cKDTree(tree_data)
    
    print(f"   ✅ Indexed {len(df_master_valid)} shops for spatial search")
    
    # ========================================================================
    # STEP 3: IDENTIFY NEW SHOPS
    # ========================================================================
    
    print("\n🆕 Identifying new shops...")
    new_shops = df_new[df_new.apply(is_new_shop, axis=1)].copy()
    new_shops = new_shops.dropna(subset=['latitude', 'longitude']).copy()
    new_shops = new_shops.reset_index(drop=True)
    
    print(f"   ✅ Found {len(new_shops)} new shops to validate")
    
    if new_shops.empty:
        print("   ℹ️  No new shops to process")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    # Convert new shop coordinates to meters
    new_shops['x'] = new_shops['latitude'] * factor_lat
    new_shops['y'] = new_shops['longitude'] * factor_lon
    
    # Initialize result columns
    for col in ['duplicate_remark', 'matched_prospect_code', 'matched_customer_name', 
                'distance_meters', 'name_similarity_%', 'category', 'recommendation']:
        new_shops[col] = ''
    
    # ========================================================================
    # STEP 4: BUILD PHONE LOOKUP DICTIONARY
    # ========================================================================
    
    phone_dict = {}
    if phone_col:
        print("   📞 Building phone lookup index...")
        for i, row in df_master_valid.iterrows():
            pn = normalize_phone(row.get(phone_col, ''))
            if pn:
                if pn not in phone_dict:
                    phone_dict[pn] = []
                phone_dict[pn].append({
                    'index': i,
                    'shop': row
                })
        print(f"   ✅ Indexed {len(phone_dict)} unique phone numbers")
    
    # ========================================================================
    # STEP 5: PERFORM DUPLICATE DETECTION
    # ========================================================================
    
    print(f"\n🔍 Scanning for duplicates (radius: {CONFIG['DISTANCE_THRESHOLD_METERS']}m)...")
    
    results = []
    debug_log = []
    clean_shops = []
    flagged_shop_ids = set()
    
    # Spatial search: find all shops within threshold distance
    nearby_indices = tree.query_ball_point(
        new_shops[['x', 'y']].values, 
        r=CONFIG['DISTANCE_THRESHOLD_METERS']
    )
    
    # Process each new shop
    for i, idx_new in enumerate(new_shops.index):
        new_shop = new_shops.loc[idx_new]
        new_lat = new_shop['latitude']
        new_lon = new_shop['longitude']
        new_name = get_shop_name(new_shop, is_master=False, name_col=name_col)
        new_cust_id = str(new_shop.get('cust_ID', '')).strip()
        
        raw_phone = str(new_shop.get(phone_col, '')) if phone_col else ''
        new_phone = normalize_phone(raw_phone)
        
        remarks = []
        matched = {}
        location_found = False
        
        # ---------------------------------------------------------------------
        # LOCATION-BASED MATCHING
        # ---------------------------------------------------------------------
        
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
                
                # Calculate exact distance
                dist = haversine_distance(new_lat, new_lon, old_lat, old_lon)
                
                if pd.isna(dist) or dist > CONFIG['DISTANCE_THRESHOLD_METERS']:
                    continue
                
                # Calculate name similarity
                sim = name_similarity(new_name, old_name)
                
                # Log for debugging
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
                    'exact_coords': (round(new_lat, 6) == round(old_lat, 6) and 
                                   round(new_lon, 6) == round(old_lon, 6)),
                    'cleaned_new_name': clean_shop_name(new_name),
                    'cleaned_old_name': clean_shop_name(old_name)
                })
                
                location_found = True
                
                # Categorize based on similarity
                if sim >= CONFIG['NAME_SIMILARITY_SERIOUS']:
                    remark = f"SERIOUS_DUPLICATE:{old_prospect}:dist={dist:.1f}m:sim={sim:.1f}%"
                    remark_type = 'SERIOUS_DUPLICATE'
                elif sim >= CONFIG['NAME_SIMILARITY_SUSPICION']:
                    remark = f"SUSPICION:{old_prospect}:dist={dist:.1f}m:sim={sim:.1f}%"
                    remark_type = 'SUSPICION'
                else:
                    remark = f"LOW_SUSPICION:{old_prospect}:dist={dist:.1f}m:sim={sim:.1f}%"
                    remark_type = 'LOW_SUSPICION'
                
                remarks.append(remark)
                
                # Store first match for summary
                if not matched:
                    matched = {
                        'prospect': old_prospect,
                        'cust_id': old_cust_id,
                        'name': old_name,
                        'distance': f"{dist:.1f}",
                        'similarity': f"{sim:.1f}",
                        'category': remark_type
                    }
                
                # Store detailed result
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
                    'match_method': 'LOCATION',
                    'category': categorize_duplicate(f"{dist:.1f}", sim, 'LOCATION')
                })
        
        # ---------------------------------------------------------------------
        # PHONE-BASED MATCHING (fallback if no location match)
        # ---------------------------------------------------------------------
        
        if not location_found and phone_col and new_phone:
            if new_phone in phone_dict:
                for entry in phone_dict[new_phone]:
                    old_shop = entry['shop']
                    
                    old_pn_normalized = normalize_phone(old_shop.get(phone_col, ''))
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
                                'similarity': f"{name_similarity(new_name, old_name):.1f}",
                                'category': 'CRITICAL_DUPLICATE'
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
                            'phone_diff_digits': diff_count,
                            'category': 'CRITICAL_DUPLICATE'
                        })
                        break
        
        # ---------------------------------------------------------------------
        # CATEGORIZE SHOP
        # ---------------------------------------------------------------------
        
        if remarks:
            # Shop has potential duplicates - flag for review
            new_shops.at[idx_new, 'duplicate_remark'] = '; '.join(remarks)
            new_shops.at[idx_new, 'matched_prospect_code'] = matched.get('prospect', '')
            new_shops.at[idx_new, 'matched_customer_name'] = matched.get('name', '')
            new_shops.at[idx_new, 'distance_meters'] = matched.get('distance', '')
            new_shops.at[idx_new, 'name_similarity_%'] = matched.get('similarity', '')
            new_shops.at[idx_new, 'category'] = matched.get('category', '')
            
            # Recommendation based on category
            category = matched.get('category', '')
            if category in ['CRITICAL_DUPLICATE', 'SERIOUS_DUPLICATE']:
                new_shops.at[idx_new, 'recommendation'] = '🚫 REJECT - Likely Duplicate'
            else:
                new_shops.at[idx_new, 'recommendation'] = '⚠️ MANUAL REVIEW REQUIRED'
            
            flagged_shop_ids.add(new_cust_id)
        else:
            # Clean shop - approve for Code P conversion
            clean_shops.append({
                'cust_ID': new_cust_id,
                'customer_name_en': new_name,
                'phone': raw_phone,
                'province': new_shop.get('province', ''),
                'district': new_shop.get('district', ''),
                'commune': new_shop.get('commune', ''),
                'latitude': new_lat,
                'longitude': new_lon,
                'recommendation': '✅ APPROVE - Convert to Code P',
                'status': 'CLEAN'
            })
    
    # ========================================================================
    # STEP 6: GENERATE OUTPUT DATAFRAMES
    # ========================================================================
    
    print(f"   ✅ Scan complete!")
    
    results_df = pd.DataFrame(results)
    flagged = new_shops[new_shops['duplicate_remark'] != ''].copy()
    debug_df = pd.DataFrame(debug_log)
    clean_df = pd.DataFrame(clean_shops)
    
    # Create review list (all new shops with status)
    review_list = new_shops.copy()
    review_list['review_status'] = review_list['cust_ID'].apply(
        lambda x: 'FLAGGED_AS_DUPLICATE' if x in flagged_shop_ids else 'CLEAN_APPROVED'
    )
    
    # Select columns for review list
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
        'category',
        'recommendation',
        'review_status'
    ]
    
    available_review_cols = [c for c in review_cols if c in review_list.columns]
    review_list = review_list[available_review_cols]
    
    # Rename for cleaner output
    rename_map = {name_col: 'customer_name_en'}
    if phone_col:
        rename_map[phone_col] = 'phone'
    rename_map = {k: v for k, v in rename_map.items() if k in review_list.columns}
    review_list = review_list.rename(columns=rename_map)
    
    # ========================================================================
    # STEP 7: GENERATE SQL STATEMENTS
    # ========================================================================
    
    print("   📝 Generating SQL statements...")
    if not flagged.empty:
        sql_statements = []
        processed_ids = set()
        for _, row in flagged.iterrows():
            cust_id = str(row.get('cust_ID', '')).strip()
            if cust_id and cust_id not in processed_ids and cust_id.lower() not in ['nan', 'null', 'none', '']:
                sql = f'Insert into dbo.DQ_Customer_ID_Issue([Cust_ID],[DateTime],[Issue_Type]) values ({cust_id}, GETDATE(),"Suspect Duplicate");'
                sql_statements.append(sql)
                processed_ids.add(cust_id)
        
        sql_df = pd.DataFrame({'SQL_Insert_Statements': sql_statements})
        print(f"   ✅ Generated {len(sql_statements)} SQL statements")
    else:
        sql_df = pd.DataFrame({'SQL_Insert_Statements': ['-- No duplicates found']})
    
    # ========================================================================
    # STEP 8: SAVE OUTPUT FILE
    # ========================================================================
    
    print(f"\n💾 Saving results to {output_file}...")
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    if os.path.exists(output_file):
        try:
            os.remove(output_file)
        except PermissionError:
            print("   ⚠️ Warning: Output file is open. Please close it and try again.")
            return flagged, results_df, debug_df, clean_df
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Sheet 1: Summary Dashboard
        summary_data = {
            'Metric': [
                'Total New Shops Submitted',
                '✅ Clean Shops (Approved for Code P)',
                '🚫 Critical Duplicates (Reject)',
                '⚠️ Suspicious (Manual Review)',
                '📊 Total Flagged for Review',
                '',
                'Detection Method Breakdown:',
                '  - Location-based matches (<20m)',
                '  - Phone exact matches',
                '  - Phone similar (1-digit typo)',
                '',
                'Category Breakdown:',
                '  - CRITICAL_DUPLICATE',
                '  - SERIOUS_DUPLICATE',
                '  - SUSPICION',
                '  - LOW_SUSPICION'
            ],
            'Count': [
                len(new_shops),
                len(clean_df),
                len(results_df[results_df['category']=='CRITICAL_DUPLICATE']) if not results_df.empty else 0,
                len(results_df[results_df['category'].isin(['SUSPICION', 'LOW_SUSPICION'])]) if not results_df.empty else 0,
                len(flagged),
                '',
                '',
                len(results_df[results_df['match_method']=='LOCATION']) if not results_df.empty else 0,
                len(results_df[results_df['remark_type']=='PHONE_DUPLICATE']) if not results_df.empty else 0,
                len(results_df[results_df['remark_type']=='SIMILAR_PHONE']) if not results_df.empty else 0,
                '',
                '',
                len(results_df[results_df['category']=='CRITICAL_DUPLICATE']) if not results_df.empty else 0,
                len(results_df[results_df['category']=='SERIOUS_DUPLICATE']) if not results_df.empty else 0,
                len(results_df[results_df['category']=='SUSPICION']) if not results_df.empty else 0,
                len(results_df[results_df['category']=='LOW_SUSPICION']) if not results_df.empty else 0
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='📊 Summary', index=False)
        
        # Sheet 2: Clean Shops (Ready for Code P)
        (clean_df if not clean_df.empty else pd.DataFrame({'Message': ['No clean shops - all require review']}))\
            .to_excel(writer, sheet_name='✅ Convert_to_Code_P', index=False)
        
        # Sheet 3: Flagged Duplicates
        (flagged if not flagged.empty else pd.DataFrame({'Message': ['No duplicates found']}))\
            .to_excel(writer, sheet_name='🚫 Flagged_Duplicates', index=False)
        
        # Sheet 4: Detailed Comparison
        if not results_df.empty:
            cols = ['category', 'new_cust_id', 'old_cust_id', 'new_prospect_code', 'old_prospect_code',
                   'new_customer_name', 'old_shop_name', 'new_phone', 'old_phone',
                   'distance_meters', 'name_similarity_%', 'remark_type', 'match_method']
            available_cols = [c for c in cols if c in results_df.columns]
            results_df[available_cols].sort_values('category').to_excel(writer, sheet_name='🔍 Detailed_Comparison', index=False)
        else:
            pd.DataFrame({'Message': ['No matches found']}).to_excel(writer, sheet_name='🔍 Detailed_Comparison', index=False)
        
        # Sheet 5: Review List (All new shops)
        (review_list if not review_list.empty else pd.DataFrame({'Message': ['No shops to review']}))\
            .to_excel(writer, sheet_name='📋 Review_List', index=False)
        
        # Sheet 6: Debug Log
        (debug_df if not debug_df.empty else pd.DataFrame({'Message': ['No close locations found']}))\
            .to_excel(writer, sheet_name='🔧 DEBUG_Within_20m', index=False)
        
        # Sheet 7: SQL Statements
        sql_df.to_excel(writer, sheet_name='💾 DQ_Issue_SQL', index=False)
    
    print(f"   ✅ File saved successfully!")
    
    # ========================================================================
    # STEP 9: AUTO-MERGE CLEAN SHOPS TO MASTER DATA (Optional)
    # ========================================================================
    
    if CONFIG['AUTO_MERGE_CLEAN_SHOPS'] and not clean_df.empty:
        print(f"\n🔄 Auto-merging {len(clean_df)} clean shops to Master_Data...")
        
        # Backup original Master_Data
        if CONFIG['BACKUP_MASTER_DATA']:
            backup_file = master_file.replace('.xlsx', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')
            shutil.copy2(master_file, backup_file)
            print(f"   💾 Backup created: {backup_file}")
        
        # Get clean shop IDs
        clean_ids = set(clean_df['cust_ID'].astype(str))
        
        # Get full rows from New_Data for clean shops
        approved_shops = df_new[df_new['cust_ID'].astype(str).isin(clean_ids)].copy()
        
        # Append to Master_Data
        df_master_updated = pd.concat([df_master, approved_shops], ignore_index=True)
        
        # Save updated Master_Data
        df_master_updated.to_excel(master_file, index=False)
        print(f"   ✅ Master_Data updated: {len(df_master)} → {len(df_master_updated)} shops")
        print(f"   📈 Added {len(approved_shops)} new shops")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    
    print("\n" + "="*70)
    print("✅ DUPLICATE DETECTION COMPLETE")
    print("="*70)
    print(f"📊 Results:")
    print(f"   • Total new shops: {len(new_shops)}")
    print(f"   • ✅ Clean (approved): {len(clean_df)}")
    print(f"   • 🚫 Flagged (review needed): {len(flagged)}")
    print(f"   • 📁 Output: {output_file}")
    
    if CONFIG['AUTO_MERGE_CLEAN_SHOPS'] and not clean_df.empty:
        print(f"\n🔄 Auto-merge:")
        print(f"   • {len(clean_df)} shops added to Master_Data")
    
    print("="*70 + "\n")
    
    return flagged, results_df, debug_df, clean_df

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # File paths
    master_file = r'Source\Master_Data.xlsx'
    new_file = r'Source\New_Data.xlsx'
    output_file = f'Results\duplicate_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    try:
        # Run duplicate detection
        flagged, details, debug, clean_df = find_duplicate_shops(master_file, new_file, output_file)
        
        # Print sample flagged shops
        if flagged is not None and not flagged.empty:
            print("\n" + "="*70)
            print("⚠️  SAMPLE FLAGGED SHOPS (First 5):")
            print("="*70)
            for _, row in flagged.head(5).iterrows():
                phone_val = row.get('phone', row.get('Phone', 'N/A'))
                name_val = row.get('customer_name_en', row.get('shop_name_en', 'Unknown'))
                print(f"\n📍 {name_val}")
                print(f"   ID: {row.get('cust_ID', 'N/A')}")
                print(f"   📞 {phone_val}")
                print(f"   🏷️ Category: {row.get('category', 'N/A')}")
                print(f"   ❗ {row['duplicate_remark']}")
                print(f"   → Match: {row['matched_customer_name']} (Code: {row['matched_prospect_code']})")
                print(f"   💡 Recommendation: {row.get('recommendation', 'N/A')}")
            
            if len(flagged) > 5:
                print(f"\n   ... and {len(flagged) - 5} more flagged shops (see Excel file)")
        
        # Print sample clean shops
        if clean_df is not None and not clean_df.empty:
            print("\n" + "="*70)
            print("✅ SAMPLE CLEAN SHOPS (First 5):")
            print("="*70)
            for _, row in clean_df.head(5).iterrows():
                print(f"   • {row['customer_name_en']} ({row['cust_ID']})")
            if len(clean_df) > 5:
                print(f"   ... and {len(clean_df) - 5} more clean shops")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
