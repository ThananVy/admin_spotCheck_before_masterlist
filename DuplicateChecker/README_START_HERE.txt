# 🚀 Duplicate Checker v2.0 - Complete Package

## ⚡ SUPER QUICK START (For Non-Technical Users)

### 1️⃣ Install UV (One-Time, 1 Minute)
Open **PowerShell** and run:
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```
Close PowerShell after it finishes.

### 2️⃣ Add Your Excel Files
Put these 2 files in the **Source** folder:
- `Master_Data.xlsx` (your existing shops)
- `New_Data.xlsx` (today's new shops)

### 3️⃣ Run It!
**Double-click:** `run_duplicate_checker.bat`

That's it! ✅

---

## 📂 What's in This Package

```
DuplicateChecker/
├── Source/                          ← PUT YOUR EXCEL FILES HERE
│   └── README_PUT_FILES_HERE.txt
├── Results/                         ← OUTPUT APPEARS HERE
├── run_duplicate_checker.bat        ← DOUBLE-CLICK THIS!
├── duplicate_checker_v2.py          ← Main script
└── (documentation files)
```

---

## ❓ Quick Questions

**Q: Do I need Python installed?**
**A:** NO! UV handles everything.

**Q: What if I get an error?**
**A:** Make sure:
- UV is installed (Step 1 above)
- Files are in Source / folder with correct names
- Excel files are closed (not open)

**Q: Where do I see results?**
**A:** Open the **Results** folder after running.

**Q: Can I run multiple times?**
**A:** YES! It won't create duplicates.

---

## 📖 Need More Help?

Read these files in order:
1. **SIMPLE_README.md** - Detailed guide for users
2. **GETTING_STARTED.md** - Tutorial with examples
3. **USER_GUIDE.md** - Complete documentation

---

## 🎯 What It Does

✅ Detects duplicate shops (by GPS location + phone + name)
✅ Auto-merges clean shops to Master_Data
✅ Creates backup automatically
✅ Saves 30+ minutes daily

---

**Questions?** Read **SIMPLE_README.md** for full instructions!

1. Open **PowerShell** (search for it in Windows)
2. Copy and paste this command:
   ```
   irm https://astral.sh/uv/install.ps1 | iex
   ```
3. Press Enter and wait (~1 minute)
4. Close PowerShell

Last Updated: 2025-04-21
Version: 2.0.0
