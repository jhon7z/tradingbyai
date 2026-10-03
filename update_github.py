import subprocess

commands = [
    "git init",
    "git config user.name jhon7z",
    "git config user.email jhon7z@users.noreply.github.com",
    "git remote remove origin",
    "git remote add origin https://github.com/jhon7z/tradingbyai.git",
    "git branch -M main",
    "git add .",
    'git commit -m "feat: Update XAUUSD MT5 Bot with 9Router AI"',
    "git push -f origin main"
]

print("🚀 Memulai upload ke GitHub...")
for cmd in commands:
    print(f"> {cmd}")
    subprocess.run(cmd, shell=True)

print("\n🎉 SELESAI! Silakan buka https://github.com/jhon7z/tradingbyai")