# 🚀 Duplicate Checker - Super Simple Guide

## ✅ What You Need (One-Time Setup)

### Step 1: Install UV (Only Once)
1. Open **PowerShell** (search for it in Windows)
2. Copy and paste this command:
   ```
   irm https://astral.sh/uv/install.ps1 | iex
   ```
3. Press Enter and wait (~1 minute)
4. Close PowerShell
5. ✅ Done! You never need to do this again.

---

## 📂 How to Use (Daily)

### Step 1: Get the Folder
1. **Download** the ZIP file from Telegram
2. **Extract** it anywhere (Desktop is fine)
3. You'll see this folder:
   ```
   DuplicateChecker/
   ├── Source/              ← PUT YOUR FILES HERE
   ├── Results/             ← OUTPUT APPEARS HERE
   ├── run_duplicate_checker.bat  ← DOUBLE-CLICK THIS
   └── (other files - don't touch)
   ```

### Step 2: Add Your Files
Put these 2 files in the **Source** folder:
- `Master_Data.xlsx` (your existing shops)
- `New_Data.xlsx` (today's new shops)

### Step 3: Run It
**Double-click** `run_duplicate_checker.bat`

That's it! 🎉

---

## 📊 Check Your Results

### After the script runs (takes ~10 seconds):

1. Open the **Results** folder
2. Open the newest Excel file
3. Read the sheets:

| Sheet Name | What It Means | What to Do |
|------------|---------------|------------|
| **📊 Summary** | Quick overview | Start here - see how many clean vs flagged |
| **✅ Convert_to_Code_P** | Clean shops (approved) | Nothing! Already added to Master_Data |
| **🚫 Flagged_Duplicates** | Suspicious shops | Review these - decide APPROVE or REJECT |
| **🔍 Detailed_Comparison** | Side-by-side details | Use this to verify flagged shops |

**Important:** Clean shops are automatically added to your Master_Data.xlsx! 
A backup is created automatically.

---

## ❓ Common Questions

### Q: Do I need to install Python?
**A:** NO! UV handles everything. Just install UV once (Step 1 above).

### Q: What if I get an error?
**A:** Check:
- Did you put files in the **Source** folder?
- Are the files named exactly `Master_Data.xlsx` and `New_Data.xlsx`?
- Is the Excel file closed (not open)?

### Q: Can I run this multiple times?
**A:** YES! Run it as many times as you want. It won't create duplicates.

### Q: Where is my old Master_Data?
**A:** A backup is created automatically in the Source folder:
- `Master_Data_backup_20250421_093045.xlsx`

### Q: What if I want to undo?
**A:** Replace Master_Data.xlsx with the backup file.

---

## 🎯 Daily Workflow (Super Simple)

```
Morning:
1. Receive New_Data.xlsx (put in Source folder)
2. Double-click run_duplicate_checker.bat
3. Wait 10 seconds
4. Open Results folder
5. Review flagged shops (5 minutes)
6. Done! Master_Data is ready for tomorrow
```

---

## 🆘 Troubleshooting

### Error: "UV is not installed"
→ Do Step 1 (Install UV) above

### Error: "Master_Data.xlsx not found"
→ Put your files in the **Source** folder (not the main folder)

### Error: "Output file is open"
→ Close the Excel file in Results folder and run again

### Script runs but no output
→ Check if Excel files have these columns:
- latitude
- longitude
- prospect_code
- cust_ID

---

## 📞 Need Help?

1. Check the error message on screen
2. Read the detailed guides in the folder:
   - **USER_GUIDE.md** (full explanations)
   - **GETTING_STARTED.md** (tutorial)
3. Contact the person who sent you this

---

## 📦 What's in This Package?

You don't need to touch these files (just know they're there):

- `run_duplicate_checker.bat` ← **DOUBLE-CLICK THIS**
- `duplicate_checker_v2.py` (the main script)
- `pyproject.toml` (UV configuration)
- `.python-version` (Python version info)
- `README.md` (this file)
- `USER_GUIDE.md` (detailed guide)
- `GETTING_STARTED.md` (tutorial)
- `CONFIG_PRESETS.py` (advanced settings)
- `VERSION_COMPARISON.md` (what's new)

**Only touch these folders:**
- `Source/` ← Put your Excel files here
- `Results/` ← Get your results here

---

## ✅ Quick Checklist

Before running:
- [ ] UV installed (only once)
- [ ] Master_Data.xlsx in Source folder
- [ ] New_Data.xlsx in Source folder
- [ ] All Excel files are closed

After running:
- [ ] Check Summary sheet
- [ ] Review Flagged_Duplicates
- [ ] Master_Data updated automatically
- [ ] Ready for next day!

---

**That's it! Super simple, right?** 😊

Just double-click `run_duplicate_checker.bat` every day!

---

Last Updated: 2025-04-21
Version: 2.0
For Non-Technical Users ✅
