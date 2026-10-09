from pathlib import Path

app = Path("demo-portal/static/app.js")
content = app.read_text()

old_icons = """const Icons = {"""
new_icons = """const Icons = {
  RefreshCw: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),"""

content = content.replace(old_icons, new_icons)
app.write_text(content)
print("Icons fixed")
