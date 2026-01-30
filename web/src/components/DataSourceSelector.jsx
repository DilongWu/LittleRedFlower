import React, { useState, useEffect } from 'react';
import { Database, RefreshCw, Check, X, AlertCircle, Key } from 'lucide-react';

function DataSourceSelector() {
  const [currentSource, setCurrentSource] = useState('eastmoney');
  const [availableSources, setAvailableSources] = useState(['eastmoney', 'sina', 'tushare']);
  const [tushareConfigured, setTushareConfigured] = useState(false);
  const [loading, setLoading] = useState(false);
  const [testResults, setTestResults] = useState({});
  const [testing, setTesting] = useState({});
  const [showSelector, setShowSelector] = useState(false);
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [tokenInput, setTokenInput] = useState('');
  const [savingToken, setSavingToken] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  useEffect(() => {
    // Handle window resize
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    window.addEventListener('resize', handleResize);

    // Fetch current data source
    fetch('/api/datasource')
      .then(res => res.json())
      .then(data => {
        setCurrentSource(data.source);
        if (data.available_sources) {
          setAvailableSources(data.available_sources);
        }
        setTushareConfigured(data.tushare_token_configured === true);
      })
      .catch(err => console.error('Failed to fetch data source:', err));

    // Check Tushare token status
    fetch('/api/datasource/tushare-token')
      .then(res => res.json())
      .then(data => setTushareConfigured(data.configured))
      .catch(err => console.error('Failed to check tushare token:', err));

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleSourceChange = async (source) => {
    // If trying to switch to tushare without token, show token input
    if (source === 'tushare' && !tushareConfigured) {
      setShowTokenInput(true);
      return;
    }

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
        const error = await res.json();
        alert('Failed to change data source: ' + (error.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('Error changing data source: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const saveTushareToken = async () => {
    if (!tokenInput || tokenInput.length < 10) {
      alert('请输入有效的 Tushare Token');
      return;
    }

    setSavingToken(true);
    try {
      const res = await fetch('/api/datasource/tushare-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: tokenInput })
      });

      if (res.ok) {
        setTushareConfigured(true);
        setShowTokenInput(false);
        setTokenInput('');
        alert('Token 保存成功！现在可以切换到 Tushare 数据源了。');
      } else {
        const error = await res.json();
        alert('保存失败: ' + (error.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('保存失败: ' + err.message);
    } finally {
      setSavingToken(false);
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
      id: 'eastmoney',
      name: '东方财富',
      description: '数据全面，包含板块、概念等',
      icon: '📊'
    },
    {
      id: 'sina',
      name: '新浪财经',
      description: '稳定性较好，支持A股实时行情',
      icon: '🌐'
    },
    {
      id: 'tushare',
      name: 'Tushare Pro',
      description: '专业数据源，限流少，需要Token',
      icon: '🚀',
      requiresToken: true
    }
  ];

  const getSourceDisplayName = (sourceId) => {
    const source = sources.find(s => s.id === sourceId);
    return source ? source.name : sourceId;
  };

  return (
    <div className="data-source-selector" style={{ position: 'relative' }}>
      <button
        className="data-source-toggle"
        onClick={() => setShowSelector(!showSelector)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: isMobile ? '10px 16px' : '6px 12px',
          borderRadius: '8px',
          border: '1px solid #ddd',
          background: 'white',
          cursor: 'pointer',
          fontSize: isMobile ? '14px' : '12px',
          color: '#666',
          width: isMobile ? '100%' : 'auto',
          justifyContent: 'center',
          boxSizing: 'border-box'
        }}
      >
        <Database size={isMobile ? 18 : 14} />
        <span>数据源: {getSourceDisplayName(currentSource)}</span>
      </button>

      {showSelector && (
        <>
          {/* Mobile overlay backdrop */}
          {isMobile && (
            <div
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0,0,0,0.5)',
                zIndex: 9998
              }}
              onClick={() => setShowSelector(false)}
            />
          )}

          <div
            className="data-source-dropdown"
            style={{
              position: isMobile ? 'fixed' : 'absolute',
              top: isMobile ? '50vh' : '100%',
              left: isMobile ? '50vw' : 'auto',
              right: isMobile ? 'auto' : 0,
              transform: isMobile ? 'translate(-50%, -50%)' : 'none',
              marginTop: isMobile ? 0 : '4px',
              background: 'white',
              border: '1px solid #ddd',
              borderRadius: '12px',
              padding: isMobile ? '20px' : '12px',
              boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
              zIndex: 9999,
              width: isMobile ? '90vw' : 'auto',
              minWidth: isMobile ? '0' : '320px',
              maxWidth: isMobile ? '90vw' : '400px',
              maxHeight: isMobile ? '85vh' : '80vh',
              overflowY: 'auto',
              // Prevent iOS Safari scroll issues
              WebkitOverflowScrolling: 'touch'
            }}
          >
            <div style={{
              marginBottom: '16px',
              fontWeight: '600',
              fontSize: isMobile ? '16px' : '14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <span>选择数据源</span>
              {isMobile && (
                <button
                  onClick={() => setShowSelector(false)}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '24px',
                    color: '#999',
                    padding: '0',
                    lineHeight: '1'
                  }}
                >
                  ×
                </button>
              )}
            </div>

            {sources.map(source => (
              <div
                key={source.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: isMobile ? '14px' : '10px',
                  borderRadius: '8px',
                  marginBottom: '10px',
                  border: currentSource === source.id ? '2px solid #d32f2f' : '1px solid #eee',
                  background: currentSource === source.id ? '#fff5f5' : '#fafafa',
                  cursor: 'pointer',
                  opacity: source.requiresToken && !tushareConfigured ? 0.7 : 1
                }}
                onClick={() => handleSourceChange(source.id)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontSize: isMobile ? '24px' : '20px' }}>{source.icon}</span>
                  <div>
                    <div style={{ fontWeight: '500', fontSize: isMobile ? '14px' : '13px' }}>
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
                      {source.requiresToken && !tushareConfigured && (
                        <span style={{
                          marginLeft: '8px',
                          color: '#ff9800',
                          fontSize: '11px'
                        }}>
                          (需配置Token)
                        </span>
                      )}
                      {source.requiresToken && tushareConfigured && currentSource !== source.id && (
                        <span style={{
                          marginLeft: '8px',
                          color: '#4caf50',
                          fontSize: '11px'
                        }}>
                          (已配置)
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: isMobile ? '12px' : '11px', color: '#888', marginTop: '2px' }}>
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
                    padding: isMobile ? '6px 10px' : '4px 8px',
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

            {/* Tushare Token Input */}
            {showTokenInput && (
              <div style={{
                marginTop: '16px',
                padding: isMobile ? '16px' : '12px',
                background: '#e3f2fd',
                borderRadius: '8px',
                border: '1px solid #2196f3'
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  marginBottom: '10px',
                  fontWeight: '500',
                  fontSize: isMobile ? '14px' : '13px'
                }}>
                  <Key size={16} />
                  配置 Tushare Token
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>
                  请前往 <a href="https://tushare.pro" target="_blank" rel="noopener noreferrer" style={{ color: '#2196f3' }}>tushare.pro</a> 注册并获取 Token
                </div>
                <input
                  type="text"
                  placeholder="输入你的 Tushare Token"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  style={{
                    width: '100%',
                    padding: isMobile ? '12px' : '8px',
                    borderRadius: '6px',
                    border: '1px solid #ddd',
                    fontSize: isMobile ? '14px' : '12px',
                    marginBottom: '10px',
                    boxSizing: 'border-box'
                  }}
                />
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    onClick={saveTushareToken}
                    disabled={savingToken}
                    style={{
                      flex: 1,
                      padding: isMobile ? '12px' : '8px',
                      borderRadius: '6px',
                      border: 'none',
                      background: '#2196f3',
                      color: 'white',
                      cursor: savingToken ? 'not-allowed' : 'pointer',
                      fontSize: isMobile ? '14px' : '12px',
                      fontWeight: '500'
                    }}
                  >
                    {savingToken ? '保存中...' : '保存 Token'}
                  </button>
                  <button
                    onClick={() => setShowTokenInput(false)}
                    style={{
                      padding: isMobile ? '12px 16px' : '8px 12px',
                      borderRadius: '6px',
                      border: '1px solid #ddd',
                      background: 'white',
                      cursor: 'pointer',
                      fontSize: isMobile ? '14px' : '12px'
                    }}
                  >
                    取消
                  </button>
                </div>
              </div>
            )}

            {Object.keys(testResults).length > 0 && (
              <div style={{
                marginTop: '12px',
                padding: isMobile ? '12px' : '8px',
                background: '#f5f5f5',
                borderRadius: '6px',
                fontSize: '11px'
              }}>
                {Object.entries(testResults).map(([source, result]) => (
                  <div key={source} style={{ marginBottom: '6px' }}>
                    <strong>{getSourceDisplayName(source)}:</strong>{' '}
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
              marginTop: '16px',
              padding: isMobile ? '12px' : '8px',
              background: '#fff3cd',
              borderRadius: '6px',
              fontSize: isMobile ? '12px' : '11px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px'
            }}>
              <AlertCircle size={16} color="#856404" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span style={{ color: '#856404' }}>
                切换数据源后页面会自动刷新。Tushare 数据源限流少、更稳定，推荐使用。
              </span>
            </div>
          </div>
        </>
      )}

      {loading && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999
        }}>
          <div style={{
            background: 'white',
            padding: isMobile ? '24px 32px' : '20px 40px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.2)'
          }}>
            <RefreshCw size={24} className="animate-spin" />
            <span style={{ fontSize: isMobile ? '15px' : '14px' }}>正在切换数据源...</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default DataSourceSelector;
