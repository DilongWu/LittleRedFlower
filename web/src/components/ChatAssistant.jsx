import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageCircle, X, Trash2 } from 'lucide-react';
import './ChatAssistant.css';

const ChatAssistant = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const messagesEndRef = useRef(null);

  // Quick suggestion questions
  const suggestions = [
    "今天市场情绪如何？",
    "涨停板有哪些？",
    "资金流向如何？",
    "热门板块有哪些？"
  ];

  // Load chat history from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('chat_history');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setMessages(parsed);
      } catch (e) {
        console.error('无法加载聊天历史', e);
      }
    }
  }, []);

  // Save to localStorage whenever messages change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('chat_history', JSON.stringify(messages));
    }
  }, [messages]);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Clear chat history
  const clearHistory = () => {
    setMessages([]);
    localStorage.removeItem('chat_history');
  };

  // Send message
  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
          history: messages
        })
      });

      if (!res.ok) throw new Error('请求失败');

      const data = await res.json();
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response
      }]);
    } catch (e) {
      console.error('Chat error:', e);
      setMessages(prev => [...prev, {
        role: 'error',
        content: '抱歉，发生了错误，请稍后重试。'
      }]);
    } finally {
      setLoading(false);
    }
  };

  // Handle keyboard shortcuts
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Handle suggestion click
  const handleSuggestion = (text) => {
    setInput(text);
    // Auto-send after setting input
    setTimeout(() => {
      sendMessage();
    }, 100);
  };

  return (
    <div className="chat-widget">
      {/* Floating Button */}
      {!isOpen && (
        <button
          className="chat-button"
          onClick={() => setIsOpen(true)}
          title="打开AI助手"
        >
          <MessageCircle size={24} />
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="chat-window">
          {/* Header */}
          <div className="chat-header">
            <span>AI 市场助手</span>
            <div className="chat-header-actions">
              {messages.length > 0 && (
                <button
                  className="clear-history-btn"
                  onClick={clearHistory}
                  title="清除历史"
                >
                  <Trash2 size={16} />
                </button>
              )}
              <button
                className="close-btn"
                onClick={() => setIsOpen(false)}
                title="关闭"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          {/* Messages Area */}
          <div className="chat-messages">
            {/* Show suggestions when no messages */}
            {messages.length === 0 && (
              <div className="chat-suggestions">
                <p className="suggestions-title">快捷问题：</p>
                {suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    className="suggestion-btn"
                    onClick={() => handleSuggestion(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}

            {/* Messages */}
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                <div className="message-content">
                  {msg.content}
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {loading && (
              <div className="message assistant">
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <span className="typing-text">正在思考...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="chat-input-area">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="问我关于市场的任何问题..."
              disabled={loading}
              rows={2}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="send-btn"
              title="发送"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatAssistant;
