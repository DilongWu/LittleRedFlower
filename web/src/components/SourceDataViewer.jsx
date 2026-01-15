import React, { useMemo } from 'react';

const SourceDataViewer = ({ rawData }) => {
  const sections = useMemo(() => {
    if (!rawData) return [];

    const lines = rawData.split('\n');
    const result = [];
    let currentSection = { title: '概览', rawLines: [] };

    // 1. Initial Pass: Split into High-Level Sections by 【Title】
    lines.forEach(line => {
      // Don't trim fully yet, we need indentation for step 2
      if (!line.trim()) return;

      const titleMatch = line.trim().match(/^【(.*)】$/);
      if (titleMatch) {
         if (currentSection.rawLines.length > 0) {
           result.push(currentSection);
         }
         currentSection = { title: titleMatch[1], rawLines: [] };
      } else {
         currentSection.rawLines.push(line);
      }
    });
    // Push last section
    if (currentSection.rawLines.length > 0) {
      result.push(currentSection);
    }

    // 2. Second Pass: Process Content for Sub-Grouping (e.g. Stock Items)
    return result.map(section => {
      const processedContent = [];
      let currentGroup = null;

      (section.rawLines || []).forEach(line => {
        const trimmed = line.trim();
        // Heuristic: Logic for "Stock Item" vs "Details"
        // If line starts with "- ", it's a parent item (Header of a collapsible group).
        // If line is indented (starts with spaces) OR starts with "*", it's a child.
        
        const isItemHeader = trimmed.startsWith('- ');
        
        if (isItemHeader) {
           // Close previous group
           if (currentGroup) {
             processedContent.push(currentGroup);
           }
           // Start new group
           currentGroup = { type: 'group', header: line, children: [] };
        } else {
           // Not a header. Is it a child of current group?
           // If we have an active group, almost anything following it (that isn't a new header) 
           // should probably typically be inside it, especially 'AI Analysis' lines.
           if (currentGroup) {
              currentGroup.children.push(line);
           } else {
              // No active group, just a loose line
              processedContent.push({ type: 'line', text: line });
           }
        }
      });
      
      // Push remaining group
      if (currentGroup) {
        processedContent.push(currentGroup);
      }

      return { ...section, content: processedContent };
    });

  }, [rawData]);

  if (!rawData) return <div className="empty">暂无原始数据</div>;

  return (
    <div className="source-viewer-container">
      {sections.map((section, idx) => (
        <details key={idx} className="source-section" open={idx < 2}>
          <summary className="source-summary">
            <span className="source-title">{section.title}</span>
            <span className="source-count">{section.content.length}项</span>
          </summary>
          <div className="source-content-box">
            {section.content.map((item, i) => {
               if (item.type === 'group') {
                 // Foldable Sub-Group (Default Closed as per request)
                 // If children exist, make it collapsible. If no children, just render header.
                 if (item.children.length === 0) {
                    return <div key={i} className="source-line">{item.header}</div>;
                 }
                 return (
                   <details key={i} className="source-sub-group">
                     <summary className="source-sub-summary">
                       {item.header}
                     </summary>
                     <div className="source-sub-content">
                       {item.children.map((child, ci) => (
                         <div key={ci} className="source-line indented">{child}</div>
                       ))}
                     </div>
                   </details>
                 );
               } else {
                 // Simple Line
                 return <div key={i} className="source-line">{item.text}</div>;
               }
            })}
          </div>
        </details>
      ))}
    </div>
  );
};

export default SourceDataViewer;
