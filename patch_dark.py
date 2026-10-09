import sys

with open('./demo-portal/static/app.js', 'r') as f:
    content = f.read()

target1 = """    <div className="flex-1 overflow-y-auto bg-gray-50 p-6">"""
new1 = """    <div className="flex-1 overflow-y-auto bg-transparent p-6">"""

target2 = """          <div key={item.id} className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center gap-4">"""
new2 = """          <div key={item.id} className="bg-gray-900/50 p-4 rounded-xl border border-gray-800 shadow-sm flex flex-col md:flex-row md:items-center gap-4">"""

target3 = """              <label className="block text-sm font-semibold text-gray-700 font-mono break-all">{item.key}</label>"""
new3 = """              <label className="block text-sm font-semibold text-gray-300 font-mono break-all">{item.key}</label>"""

target4 = """                  className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-coral-500 focus:ring-1 focus:ring-coral-500 font-mono pr-12"
"""
new4 = """                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-coral-500 focus:ring-1 focus:ring-coral-500 font-mono pr-12"
"""

target5 = """                  className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-coral-500 focus:ring-1 focus:ring-coral-500 font-mono pr-12 text-gray-800"
"""
new5 = """                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-coral-500 focus:ring-1 focus:ring-coral-500 font-mono pr-12"
"""

target6 = """                  className="absolute right-3 text-gray-400 hover:text-gray-600 text-xs font-semibold"
"""
new6 = """                  className="absolute right-3 text-gray-500 hover:text-gray-300 text-xs font-semibold"
"""

content = content.replace(target1, new1)
content = content.replace(target2, new2)
content = content.replace(target3, new3)
content = content.replace(target4, new4)
content = content.replace(target5, new5)
content = content.replace(target6, new6)

with open('./demo-portal/static/app.js', 'w') as f:
    f.write(content)
