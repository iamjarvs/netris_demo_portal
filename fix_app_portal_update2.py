import re
from pathlib import Path

app = Path("demo-portal/static/app.js")
content = app.read_text()

old_block = """                {/* Action Submit */}
                <div className="pt-4 flex items-center justify-end">
                  <button
                    type="submit"
                    disabled={configSaving}
                    className="bg-coral-600 hover:bg-coral-700 text-white px-6 py-2.5 rounded-lg text-sm font-semibold shadow-theme-xs transition"
                  >"""

new_block = """                {/* Action Submit */}
                <div className="pt-4 flex items-center justify-end gap-3">
                  <button 
                    type="button"
                    onClick={async () => {
                      try {
                        const res = await fetch('/api/system/update', { method: 'POST' });
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.detail || data.message || "Update failed");
                        alert(data.message || "Portal updated successfully! You may need to restart the backend.");
                      } catch (e) {
                        alert("Update failed: " + e.message);
                      }
                    }} 
                    className="px-4 py-2.5 bg-gray-100 text-gray-700 border border-gray-300 rounded-lg text-sm font-semibold hover:bg-gray-200 shadow-theme-xs flex items-center gap-2"
                  >
                    <Icons.RefreshCw className="w-4 h-4" />
                    Update Demo Portal
                  </button>
                  <button
                    type="submit"
                    disabled={configSaving}
                    className="bg-coral-600 hover:bg-coral-700 text-white px-6 py-2.5 rounded-lg text-sm font-semibold shadow-theme-xs transition"
                  >"""

if old_block in content:
    content = content.replace(old_block, new_block)
    app.write_text(content)
    print("global button updated")
else:
    print("block not found")
