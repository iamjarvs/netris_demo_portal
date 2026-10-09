function ConfigFormEditor({ content, format, onChange }) {
  const [items, setItems] = React.useState([]);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (!content) {
      setItems([]);
      return;
    }
    try {
      if (format === 'json') {
        const obj = JSON.parse(content);
        const parsed = Object.keys(obj).map((k, idx) => ({
          id: idx,
          type: 'kv',
          key: k,
          value: typeof obj[k] === 'string' ? obj[k] : JSON.stringify(obj[k]),
          isSecret: /password|secret|key|token|pass/i.test(k),
          show: false
        }));
        setItems(parsed);
      } else if (format === 'yaml') {
        const parsed = content.split('\n').map((line, idx) => {
          const match = line.match(/^([a-zA-Z0-9_-]+):\s*(.*)$/);
          if (match && !line.startsWith(' ')) {
            return { id: idx, type: 'kv', key: match[1], value: match[2].replace(/^["'](.*)["']$/, '$1'), isSecret: /password|secret|key|token|pass/i.test(match[1]), show: false, raw: line };
          }
          return { id: idx, type: 'raw', raw: line };
        });
        setItems(parsed);
      } else {
        // shell / env
        const parsed = content.split('\n').map((line, idx) => {
          const match = line.match(/^([a-zA-Z0-9_.-]+)=(.*)$/);
          if (match) {
            return { id: idx, type: 'kv', key: match[1], value: match[2].replace(/^["'](.*)["']$/, '$1'), isSecret: /password|secret|key|token|pass/i.test(match[1]), show: false, raw: line };
          }
          return { id: idx, type: 'raw', raw: line };
        });
        setItems(parsed);
      }
      setError(null);
    } catch (e) {
      setError("Cannot parse this file format as a form. Please use the text editor fallback.");
      setItems([{id: 0, type: 'raw', raw: content}]); // fallback
    }
  }, [content, format]);

  const handleChange = (id, newVal) => {
    const newItems = items.map(item => item.id === id ? { ...item, value: newVal } : item);
    setItems(newItems);
    
    // Serialize back to string
    let newContent = '';
    if (format === 'json') {
      try {
        const obj = JSON.parse(content || '{}');
        newItems.forEach(item => {
           if (item.type === 'kv') {
             try {
               obj[item.key] = JSON.parse(item.value);
             } catch(e) {
               obj[item.key] = item.value;
             }
           }
        });
        newContent = JSON.stringify(obj, null, 2);
      } catch (e) {
        newContent = content; // Fallback
      }
    } else if (format === 'yaml') {
      newContent = newItems.map(item => {
        if (item.type === 'kv') {
           return `${item.key}: ${item.value}`;
        }
        return item.raw;
      }).join('\n');
    } else {
      newContent = newItems.map(item => {
        if (item.type === 'kv') {
           // wrap in quotes if there are spaces
           const v = item.value.includes(' ') ? `"${item.value}"` : item.value;
           return `${item.key}=${v}`;
        }
        return item.raw;
      }).join('\n');
    }
    onChange(newContent);
  };

  const toggleShow = (id) => {
    setItems(items.map(item => item.id === id ? { ...item, show: !item.show } : item));
  };

  const kvItems = items.filter(i => i.type === 'kv');

  if (error || kvItems.length === 0) {
    return (
      <textarea 
        value={content} 
        onChange={e => onChange(e.target.value)}
        className="flex-1 w-full bg-[#1E1E1E] text-[#D4D4D4] font-mono text-sm p-4 focus:outline-none resize-none"
        spellCheck={false}
      />
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto space-y-4">
        {kvItems.map(item => (
          <div key={item.id} className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center gap-4">
            <div className="md:w-1/3 flex-shrink-0">
              <label className="block text-sm font-semibold text-gray-700 font-mono break-all">{item.key}</label>
            </div>
            <div className="flex-1 relative flex items-center">
              {item.isSecret && !item.show ? (
                <input 
                  type="password" 
                  value={item.value} 
                  onChange={(e) => handleChange(item.id, e.target.value)}
                  className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-coral-500 focus:ring-1 focus:ring-coral-500 font-mono pr-12"
                />
              ) : (
                <input 
                  type="text" 
                  value={item.value} 
                  onChange={(e) => handleChange(item.id, e.target.value)}
                  className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-coral-500 focus:ring-1 focus:ring-coral-500 font-mono pr-12 text-gray-800"
                />
              )}
              {item.isSecret && (
                <button 
                  onClick={() => toggleShow(item.id)}
                  className="absolute right-3 text-gray-400 hover:text-gray-600 text-xs font-semibold"
                >
                  {item.show ? 'HIDE' : 'SHOW'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
