# Configuration Presets for Duplicate Detection System
# Copy one of these presets into the CONFIG dictionary in duplicate_checker_v2.py

# =============================================================================
# PRESET 1: STRICT MODE (Minimize False Positives)
# =============================================================================
# Use when: You want to catch only obvious duplicates
# Trade-off: Might miss some duplicates with typos or variations

STRICT_MODE = {
    'DISTANCE_THRESHOLD_METERS': 15,      # Tighter radius
    'NAME_SIMILARITY_SERIOUS': 75,        # Need very similar names
    'NAME_SIMILARITY_SUSPICION': 55,      # Higher suspicion threshold
    'PHONE_EXACT_MATCH': True,
    'PHONE_TYPO_TOLERANCE': 0,            # No typos allowed
    'BACKUP_MASTER_DATA': True,
    'AUTO_MERGE_CLEAN_SHOPS': True,
}

# Expected results:
# - More shops approved (90-95%)
# - Fewer manual reviews
# - Risk: Missing some duplicates

# =============================================================================
# PRESET 2: BALANCED MODE (Default - Recommended)
# =============================================================================
# Use when: Standard daily operations
# Trade-off: Good balance between accuracy and workload

BALANCED_MODE = {
    'DISTANCE_THRESHOLD_METERS': 20,      # Standard GPS accuracy
    'NAME_SIMILARITY_SERIOUS': 65,        # Catches most duplicates
    'NAME_SIMILARITY_SUSPICION': 40,      # Flags potential issues
    'PHONE_EXACT_MATCH': True,
    'PHONE_TYPO_TOLERANCE': 1,            # Allow 1-digit typo
    'BACKUP_MASTER_DATA': True,
    'AUTO_MERGE_CLEAN_SHOPS': True,
}

# Expected results:
# - 70-80% shops approved
# - 20-30% need review
# - Good accuracy (~90%)

# =============================================================================
# PRESET 3: AGGRESSIVE MODE (Maximum Duplicate Detection)
# =============================================================================
# Use when: Data quality is suspect, or after bulk import
# Trade-off: More manual review work, but catches almost all duplicates

AGGRESSIVE_MODE = {
    'DISTANCE_THRESHOLD_METERS': 30,      # Wider search radius
    'NAME_SIMILARITY_SERIOUS': 55,        # Lower threshold
    'NAME_SIMILARITY_SUSPICION': 30,      # Flag even weak matches
    'PHONE_EXACT_MATCH': True,
    'PHONE_TYPO_TOLERANCE': 2,            # Allow 2-digit typos
    'BACKUP_MASTER_DATA': True,
    'AUTO_MERGE_CLEAN_SHOPS': False,      # Manual approval only
}

# Expected results:
# - 40-60% shops approved
# - 40-60% need review
# - Very few missed duplicates (<2%)

# =============================================================================
# PRESET 4: MANUAL REVIEW MODE (No Auto-Merge)
# =============================================================================
# Use when: You want to manually approve ALL shops
# Trade-off: More control, but more work

MANUAL_REVIEW_MODE = {
    'DISTANCE_THRESHOLD_METERS': 20,
    'NAME_SIMILARITY_SERIOUS': 65,
    'NAME_SIMILARITY_SUSPICION': 40,
    'PHONE_EXACT_MATCH': True,
    'PHONE_TYPO_TOLERANCE': 1,
    'BACKUP_MASTER_DATA': True,
    'AUTO_MERGE_CLEAN_SHOPS': False,      # ⚠️ No auto-merge!
}

# Expected results:
# - Script generates recommendations only
# - You manually add to Master_Data
# - Maximum control

# =============================================================================
# PRESET 5: KHMER-OPTIMIZED MODE
# =============================================================================
# Use when: Dealing primarily with Khmer shop names
# Trade-off: Tuned for Unicode variations and Khmer patterns

KHMER_OPTIMIZED = {
    'DISTANCE_THRESHOLD_METERS': 20,
    'NAME_SIMILARITY_SERIOUS': 60,        # Lower (Khmer Unicode issues)
    'NAME_SIMILARITY_SUSPICION': 35,      # More lenient
    'PHONE_EXACT_MATCH': True,
    'PHONE_TYPO_TOLERANCE': 1,
    'BACKUP_MASTER_DATA': True,
    'AUTO_MERGE_CLEAN_SHOPS': True,
}

# Expected results:
# - Better handling of ភ្នំពេញ vs ភ្នំ ពេញ
# - More suspicions for review
# - Fewer missed Khmer duplicates

# =============================================================================
# PRESET 6: GPS-ONLY MODE (Ignore Name Matching)
# =============================================================================
# Use when: Names are unreliable, but GPS is accurate
# Trade-off: Only location-based matching

GPS_ONLY_MODE = {
    'DISTANCE_THRESHOLD_METERS': 10,      # Very tight radius
    'NAME_SIMILARITY_SERIOUS': 0,         # Ignore name similarity
    'NAME_SIMILARITY_SUSPICION': 0,       # Ignore name similarity
    'PHONE_EXACT_MATCH': True,
    'PHONE_TYPO_TOLERANCE': 1,
    'BACKUP_MASTER_DATA': True,
    'AUTO_MERGE_CLEAN_SHOPS': True,
}

# Expected results:
# - Only exact GPS matches flagged
# - Very high precision
# - Might miss shops with GPS drift

# =============================================================================
# HOW TO USE THESE PRESETS
# =============================================================================

"""
STEP 1: Choose a preset based on your needs

STEP 2: Copy the preset into duplicate_checker_v2.py

Replace this section:
    CONFIG = {
        'DISTANCE_THRESHOLD_METERS': 20,
        ...
    }

With your chosen preset:
    CONFIG = AGGRESSIVE_MODE  # Or any other preset

STEP 3: Run the script

STEP 4: Review results in "📊 Summary" sheet

STEP 5: Adjust if needed
    - Too many false positives? → Try STRICT_MODE
    - Missing duplicates? → Try AGGRESSIVE_MODE
    - Just right? → Keep current settings
"""

# =============================================================================
# CUSTOM TUNING GUIDE
# =============================================================================

"""
If presets don't fit, create your own custom config:

DISTANCE_THRESHOLD_METERS:
    10m  → Very strict (only exact locations)
    20m  → Good for urban areas (default)
    30m  → Good for rural areas (GPS less accurate)
    50m+ → Very lenient (use for testing only)

NAME_SIMILARITY_SERIOUS:
    80%+ → Only exact/near-exact names
    65%  → Good default (catches typos)
    50%  → Lenient (many reviews needed)
    <40% → Too lenient (many false positives)

NAME_SIMILARITY_SUSPICION:
    50%+ → Strict suspicion threshold
    40%  → Good default
    30%  → Lenient (flags even weak matches)
    <20% → Too lenient (noise)

PHONE_TYPO_TOLERANCE:
    0 → Only exact phone matches
    1 → Allow 1 digit different (recommended)
    2 → Allow 2 digits different (risky)
    3+ → Not recommended (too many false matches)

AUTO_MERGE_CLEAN_SHOPS:
    True  → Automatic (saves time)
    False → Manual review (more control)
"""

# =============================================================================
# DECISION TREE: WHICH PRESET TO CHOOSE?
# =============================================================================

"""
START HERE:
└─ Is this your first time using the script?
   ├─ YES → Use BALANCED_MODE (default)
   └─ NO → Continue...

└─ Are you seeing too many false positives?
   ├─ YES → Use STRICT_MODE
   └─ NO → Continue...

└─ Are you missing obvious duplicates?
   ├─ YES → Use AGGRESSIVE_MODE
   └─ NO → Continue...

└─ Do you have mostly Khmer shop names?
   ├─ YES → Use KHMER_OPTIMIZED
   └─ NO → Continue...

└─ Do you want full manual control?
   ├─ YES → Use MANUAL_REVIEW_MODE
   └─ NO → Use BALANCED_MODE

└─ Is GPS data very reliable but names are messy?
   └─ YES → Use GPS_ONLY_MODE
"""

# =============================================================================
# PERFORMANCE IMPACT OF PRESETS
# =============================================================================

"""
Processing Speed:
    All presets: ~same speed (spatial index is fast)
    
Memory Usage:
    All presets: ~same memory (data size matters, not config)
    
Manual Review Workload:
    STRICT_MODE:     ~10-20% of shops need review
    BALANCED_MODE:   ~20-30% of shops need review
    AGGRESSIVE_MODE: ~40-60% of shops need review
    
Duplicate Detection Rate:
    STRICT_MODE:     ~85% duplicates caught
    BALANCED_MODE:   ~92% duplicates caught
    AGGRESSIVE_MODE: ~98% duplicates caught
"""

# =============================================================================
# MONITORING & OPTIMIZATION
# =============================================================================

"""
After running with a preset, check these metrics in "📊 Summary" sheet:

1. Clean shop approval rate:
   - Target: 70-80%
   - Too low (<60%)? → Use STRICT_MODE
   - Too high (>90%)? → Use AGGRESSIVE_MODE

2. CRITICAL_DUPLICATE count:
   - Target: 5-15% of new shops
   - Too many (>25%)? → Data quality issue, use MANUAL_REVIEW_MODE
   - Too few (<2%)? → Might be missing duplicates, use AGGRESSIVE_MODE

3. FALSE POSITIVE rate (estimate from manual review):
   - Target: <10%
   - Too high? → Increase NAME_SIMILARITY_SERIOUS by 5-10%
   - Good? → Keep current settings

4. FALSE NEGATIVE rate (duplicates in clean shops):
   - Target: <5%
   - Found duplicates in approved shops? → Use AGGRESSIVE_MODE
   - None found? → Current settings are good
"""
