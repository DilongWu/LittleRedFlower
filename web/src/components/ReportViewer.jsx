import React from 'react';

const ReportViewer = ({ htmlContent }) => {
  if (!htmlContent) return null;

  return (
    <div 
      className="report-content"
      dangerouslySetInnerHTML={{ __html: htmlContent }} 
    />
  );
};

export default ReportViewer;
