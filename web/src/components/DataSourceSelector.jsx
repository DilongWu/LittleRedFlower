import React, { useState, useEffect } from 'react';
import { Database, RefreshCw, Check, X, AlertCircle } from 'lucide-react';

function DataSourceSelector() {
  const [currentSource, setCurrentSource] = useState('sina');
  const [loading, setLoading] = useState(false);
  const [testResults, setTestResults] = useState({});
  const [testing, setTesting] = useState({});
  const [showSelector, setShowSelector] = useState(false);

  useEffect(() => {
    // Fetch current data source
    fetch('/api/datasource')
      .then(res => res.json())
      .then(data => setCurrentSource(data.source))
      .catch(err => console.error('Failed to fetch data source:', err));
  }, []);

  const handleSourceChange = async (source) => {
    setLoading(true);
    try {
      const res = await fetch('/api/datasource', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source })
      });

      if (res.ok) {
        setCurrentSource(source);
        // Refresh page to reload data with new source
        window.location.reload();
      } else {
        alert('Failed to change data source');
      }
    } catch (err) {
      alert('Error changing data source: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const testSource = async (source) => {
    setTesting(prev => ({ ...prev, [source]: true }));
    try {
      const res = await fetch(`/api/datasource/test?source=${source}`);
      const result = await res.json();
      setTestResults(prev => ({ ...prev, [source]: result }));
    } catch (err) {
      setTestResults(prev => ({
        ...prev,
        [source]: { available: false, error: err.message }
      }));
    } finally {
      setTesting(prev => ({ ...prev, [source]: false }));
    }
  };

  const sources = [
    {
      id: 'sina',
      name: '新浪财经',
      description: '稳定性较好，支持A股实时行情',
      icon: '🌐'
    },
    {
      id: 'eastmoney',
      name: '东方财富',
      description: '数据更全面，包含板块、概念等',
      icon: '📊'
    }
  ];

  return (
    <div className="data-source-selector">
      <button
        className="data-source-toggle"
        onClick={() => setShowSelector(!showSelector)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 12px',
          borderRadius: '6px',
          border: '1px solid #ddd',
          background: 'white',
          cursor: 'pointer',
          fontSize: '12px',
          color: '#666'
        }}
      >
        <Database size={14} />
        <span>数据源: {currentSource === 'sina' ? '新浪' : '东方财富'}</span>
      </button>

      {showSelector && (
        <div
          className="data-source-dropdown"
          style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            marginTop: '4px',
            background: 'white',
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            zIndex: 1000,
            minWidth: '280px'
          }}
        >
          <div style={{ marginBottom: '12px', fontWeight: '600', fontSize: '14px' }}>
            选择数据源
          </div>

          {sources.map(source => (
            <div
              key={source.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px',
                borderRadius: '6px',
                marginBottom: '8px',
                border: currentSource === source.id ? '2px solid #d32f2f' : '1px solid #eee',
                background: currentSource === source.id ? '#fff5f5' : '#fafafa',
                cursor: 'pointer'
              }}
              onClick={() => handleSourceChange(source.id)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '20px' }}>{source.icon}</span>
                <div>
                  <div style={{ fontWeight: '500', fontSize: '13px' }}>
                    {source.name}
                    {currentSource === source.id && (
                      <span style={{
                        marginLeft: '8px',
                        color: '#d32f2f',
                        fontSize: '11px'
                      }}>
                        (当前)
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '11px', color: '#888' }}>
                    {source.description}
                  </div>
                </div>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  testSource(source.id);
                }}
                disabled={testing[source.id]}
                style={{
                  padding: '4px 8px',
                  borderRadius: '4px',
                  border: '1px solid #ddd',
                  background: 'white',
                  cursor: testing[source.id] ? 'not-allowed' : 'pointer',
                  fontSize: '11px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                {testing[source.id] ? (
                  <RefreshCw size={12} className="animate-spin" />
                ) : testResults[source.id] ? (
                  testResults[source.id].available ? (
                    <Check size={12} color="green" />
                  ) : (
                    <X size={12} color="red" />
                  )
                ) : (
                  '测试'
                )}
              </button>
            </div>
          ))}

          {Object.keys(testResults).length > 0 && (
            <div style={{
              marginTop: '8px',
              padding: '8px',
              background: '#f5f5f5',
              borderRadius: '4px',
              fontSize: '11px'
            }}>
              {Object.entries(testResults).map(([source, result]) => (
                <div key={source} style={{ marginBottom: '4px' }}>
                  <strong>{source === 'sina' ? '新浪' : '东方财富'}:</strong>{' '}
                  {result.available ? (
                    <span style={{ color: 'green' }}>可用 - {result.sample_data}</span>
                  ) : (
                    <span style={{ color: 'red' }}>不可用 - {result.error}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          <div style={{
            marginTop: '12px',
            padding: '8px',
            background: '#fff3cd',
            borderRadius: '4px',
            fontSize: '11px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '6px'
          }}>
            <AlertCircle size={14} color="#856404" style={{ flexShrink: 0, marginTop: '2px' }} />
            <span style={{ color: '#856404' }}>
              切换数据源后页面会自动刷新。如果某个数据源不可用，系统会显示Demo数据。
            </span>
          </div>
        </div>
      )}

      {loading && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999
        }}>
          <div style={{
            background: 'white',
            padding: '20px 40px',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <RefreshCw size={20} className="animate-spin" />
            <span>正在切换数据源...</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default DataSourceSelector;
