---
name: chart-mobile-implementation
description: Guide for implementing responsive chart components with mobile support. Use when building or updating chart pages that need to work on both desktop and mobile devices.
argument-hint: <component-or-page-path>
---

# Chart Mobile Implementation Skill

Implements responsive chart components and pages that work seamlessly across desktop and mobile devices.

## When to Use This Skill

- Creating new chart pages (BingNRT, MSN QoR, etc.)
- Adding mobile support to existing chart pages
- Implementing responsive filter systems
- Building chart components with mobile optimizations
- User asks to "make charts mobile-friendly" or "add responsive charts"
- Need to implement zoom, export, or mobile controls for charts

## Core Principles

1. **Unified Experience**: Single component for both mobile and desktop (no separate Mobile files)
2. **Helper Functions**: Reusable functions configure ECharts for mobile
3. **Two Architecture Patterns**: Choose based on page structure
4. **Mobile Filter System**: Toggle button + expandable Card layout
5. **ChartMobileWrapper**: Shared component for consistent mobile/desktop layout

## Quick Decision: Which Pattern?

### Pattern A (DEFAULT - RECOMMENDED)
**Use when**: Charts render directly without individual Card wrappers

✅ ChartMobileWrapper handles Card creation automatically
✅ Minimal page-level code
✅ Set `hideChartTitle={false}` or omit (default)

**Example**: BingNRT page - simple chart list

### Pattern B (ADVANCED - RARELY NEEDED)
**Use when**: Each chart needs custom Card wrapper with styling

⚠️ Must set `hideChartTitle={true}`
⚠️ Manually render title + subtitle
⚠️ Handle Reset Zoom & Jarvis link in page

**Example**: DataCenter page - multiple charts with per-chart Cards

## Implementation Checklist

### Chart Component
- [ ] Import helpers from `app/components/shared/chartHelpers.ts`
- [ ] Import `ChartMobileWrapper`
- [ ] Add mobile detection: `const [isMobile, setIsMobile] = useState(false)`
- [ ] Add resize listener in useEffect
- [ ] Apply mobile helper functions to chart options:
  - `getMobileGridMargins(isMobile)` - grid left/right margins
  - `getMobileGridTop(isMobile)` - grid top spacing
  - `getMobileYAxisNameConfig(isMobile, desktopGap)` - axis name styling
  - `getMobileYAxisLabelConfig(isMobile)` - axis label rotation
  - `getMobileSplitNumber(isMobile)` - reduce tick marks
  - `getMobileTitleConfig(isMobile, titleConfig)` - hide title on mobile
  - `getMobileBrushConfig(isMobile)` - disable brush on mobile
- [ ] Set tooltip opacity: `backgroundColor: 'rgba(255, 255, 255, 0.85)'`
- [ ] Wrap in `ChartMobileWrapper` (unless Pattern B)
- [ ] Set up export function in useEffect with cleanup
- [ ] Handle brush zoom events for Reset Zoom button

### Page with Filters
- [ ] Add state: `const [mobileFiltersExpanded, setMobileFiltersExpanded] = useState(false)`
- [ ] Add mobile detection with resize listener
- [ ] Create page header card with filter toggle button
- [ ] Hide desktop sidebar on mobile: `display: isMobile ? 'none' : 'block'`
- [ ] Implement mobile filter Card with responsive grid
- [ ] Use grid layout: `gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))'`
- [ ] Auto-close filters after Update button click
- [ ] Test on viewport < 768px

### Mobile Card View with Pagination (for data lists)
- [ ] Add pagination state: `const [currentPage, setCurrentPage] = useState(1)` and `const [pageSize, setPageSize] = useState(10)`
- [ ] Import `ImpressionCard` or similar card component for mobile view
- [ ] Add conditional rendering: `isMobile ? <CardView /> : <TableView />`
- [ ] Wrap cards in divs with spacing: `<div style={{ marginBottom: '16px' }}>`
- [ ] Implement responsive pagination with these properties:
  - `simple={isMobile}` - simplified UI for mobile
  - `size="small"` - compact controls
  - Container style: `width: '100%', overflowX: 'auto'`
- [ ] Slice data based on pagination: `.slice((currentPage - 1) * pageSize, currentPage * pageSize)`

### Pattern B Specific (hideChartTitle={true})
- [ ] Set `hideChartTitle={true}` on chart component
- [ ] Calculate timezone and granularity for subtitle
- [ ] Manually render title div (16px font, centered)
- [ ] Manually render subtitle div (12px, color #666)
- [ ] Wrap chart in relative div for absolute controls
- [ ] Add Reset Zoom button conditionally: `!isMobile && showResetZoom`
- [ ] Add Jarvis link conditionally: `!isMobile`
- [ ] Verify no double Card wrapping

## Key Helper Functions

```typescript
// From app/components/shared/chartHelpers.ts

getMobileYAxisLabelConfig(isMobile)
// Returns: { rotate: -90 } for mobile to save horizontal space

getMobileSplitNumber(isMobile)
// Returns: 4 for mobile, undefined for desktop (reduces tick marks)

getMobileGridTop(isMobile)
// Returns: '5%' for mobile, '13%' for desktop (adjust for title)

getMobileGridMargins(isMobile)
// Returns: { left: '8%', right: '8%' } for mobile (space for axis names)

getMobileTitleConfig(isMobile, titleConfig)
// Returns: undefined for mobile (title shown in Card header)

getMobileYAxisNameConfig(isMobile, desktopNameGap)
// Returns: reduced gap + smaller font (11px) for mobile
```

## Common Issues & Solutions

### Double Card Wrapping
**Symptom**: Nested card borders, extra padding
**Fix**: Set `hideChartTitle={true}` when page has own Card wrapper

### Missing Title/Subtitle
**Symptom**: Chart has no header with Pattern B
**Fix**: Manually render title and subtitle when `hideChartTitle={true}`

### Mobile Filters Not Showing
**Symptom**: No filter access on mobile
**Fix**: Add filter toggle button + mobile filter Card implementation

### Chart Extends Beyond Container
**Symptom**: Chart overflows on mobile
**Fix**: Remove negative margins, ensure container width: 100%

### Y-Axis Names Cut Off
**Symptom**: Axis names not visible on mobile
**Fix**: Use `getMobileYAxisNameConfig()` and `getMobileGridMargins()`

## Mobile Filter System

### Page Header with Filter Toggle
```typescript
<div style={{
  display: 'flex',
  alignItems: 'center',
  justifyContent: isMobile ? 'space-between' : 'center',
  fontSize: 'clamp(14px, 3vw, 22px)' // Responsive font
}}>
  {isMobile && <div style={{ width: '32px' }} />}
  <div style={{ flex: 1, textAlign: 'center' }}>{title}</div>
  {isMobile && (
    <Button
      icon={<FilterOutlined />}
      onClick={() => setMobileFiltersExpanded(!mobileFiltersExpanded)}
      aria-label={mobileFiltersExpanded ? 'Hide filters' : 'Show filters'}
    />
  )}
</div>
```

### Mobile Filter Card
```typescript
{mobileFiltersExpanded && (
  <Card style={styles.mobileFilterCard}>
    {/* Header with close button */}
    <div onClick={() => setMobileFiltersExpanded(false)}>
      <div style={styles.mobileFilterTitle}>Filters</div>
      <Button icon={<UpOutlined />} />
    </div>
    
    {/* Responsive grid layout */}
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '16px'
    }}>
      {/* Filter items */}
      <div>
        <label>Time Range</label>
        <Select /* ... */ />
      </div>
      {/* More filters... */}
    </div>
    
    {/* Action buttons */}
    <div style={{ display: 'flex', gap: '12px' }}>
      <Button onClick={() => {
        updateFilters();
        setMobileFiltersExpanded(false); // Auto-close
      }}>Update</Button>
      <Button onClick={resetFilters}>Reset</Button>
    </div>
  </Card>
)}
```

## Reference Files

- **Pattern A Example**: `app/Bing/BingNRT/page.tsx`
- **Pattern B Example**: `app/Bing/BingNRT/DataCenter/page.tsx`
- **Mobile Card View with Pagination**: `app/Bing/BingNRT/ImpressionSamples/page.tsx`, `app/Bing/BingNRT/PriorityImpressions/page.tsx`
- **Chart Component**: `app/components/BingNRT/BingNRTChart.tsx`
- **Card Component**: `app/components/shared/ImpressionCard.tsx`
- **Helper Functions**: `app/components/shared/chartHelpers.ts`
- **Mobile Wrapper**: `app/components/shared/ChartMobileWrapper.tsx`
- **Full Guide**: `documents/CHART_MOBILE_IMPLEMENTATION_GUIDE.md`

## Export Functionality

```typescript
const exportToTSV = (data: any, title: string) => {
  let tsvContent = 'Time\tMetric1\tMetric2\n';
  // Build TSV content from data
  Object.keys(data).forEach(time => {
    tsvContent += `${time}\t${data[time].metric1}\t${data[time].metric2}\n`;
  });
  
  // Download
  const blob = new Blob([tsvContent], { type: 'text/tab-separated-values' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${title}_${new Date().toISOString().split('T')[0]}.tsv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

// Set up in useEffect with cleanup
useEffect(() => {
  (window as any)[`exportChart_${title}`] = () => exportToTSV(data, title);
  return () => delete (window as any)[`exportChart_${title}`];
}, [data, title]);
```

## Best Practices

### DO ✅
- Use single component for both mobile and desktop
- Apply all mobile helper functions consistently
- Test on both < 768px and > 768px viewports
- Use semi-transparent tooltips (0.85 opacity)
- Clean up window exports in useEffect return
- Choose correct pattern based on page structure

### DON'T ❌
- Create separate Mobile components
- Hard-code mobile values in chart options
- Forget `hideChartTitle={true}` with Pattern B
- Shadow prop names with local variables
- Use negative margins that break mobile layout
- Enable brush tool on actual mobile devices

## Mobile Optimizations Applied

1. **Y-Axis Labels**: Rotated -90° to save horizontal space
2. **Y-Axis Names**: Smaller font (11px), reduced gap
3. **Grid Margins**: 8% on each side for axis names
4. **Split Number**: Reduced to 4 tick marks
5. **Chart Title**: Moved to Card header
6. **Brush Tool**: Disabled on mobile (use touch gestures)
7. **Buttons**: In Card header on mobile, overlaid on desktop
8. **Filters**: Expandable Card on mobile, fixed sidebar on desktop
9. **Data Display**: Card view for mobile (paginated), table view for desktop
10. **Pagination**: Simplified mobile UI with `simple` prop and `size="small"`

## Mobile Card View Pattern

For pages displaying data lists (impressions, samples, etc.), use conditional rendering:

```typescript
// Add pagination state
const [currentPage, setCurrentPage] = useState<number>(1);
const [pageSize, setPageSize] = useState<number>(10);

// In JSX - conditional rendering
{isMobile ? (
  // Mobile card view with pagination
  responseData && responseData.length > 0 ? (
    <>
      {responseData
        .slice((currentPage - 1) * pageSize, currentPage * pageSize)
        .map((item, index) => (
          <div key={index} style={{ marginBottom: '16px' }}>
            <ImpressionCard 
              data={item} 
              workflow={workflowName}
            />
          </div>
        ))}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        marginTop: '20px', 
        paddingBottom: '20px',
        width: '100%',
        overflowX: 'auto'
      }}>
        <Pagination
          current={currentPage}
          total={responseData.length}
          pageSize={pageSize}
          onChange={(page, size) => {
            setCurrentPage(page);
            if (size !== pageSize) {
              setPageSize(size);
              setCurrentPage(1);
            }
          }}
          showSizeChanger
          showTotal={(total) => `Total ${total} items`}
          pageSizeOptions={['10', '20', '50', '100']}
          simple={isMobile}
          size="small"
        />
      </div>
    </>
  ) : (
    !loading && <Empty description="No data available" />
  )
) : (
  // Desktop table view
  <BingNRTTable 
    data={responseData || []} 
    loading={loading} 
    workflow={workflowName}
  />
)}
```

**Key Points**:
- Use `simple={isMobile}` for pagination - shows only prev/next with page number
- Use `size="small"` for compact controls
- Wrap pagination in responsive container with `width: '100%'` and `overflowX: 'auto'`
- Add spacing between cards: `marginBottom: '16px'`
- Handle empty states appropriately

## Workflow

When user requests chart mobile implementation:

1. **Identify Pattern**: Ask if page has Card wrappers per chart
   - No wrappers → Pattern A (default)
   - Has wrappers → Pattern B (set hideChartTitle={true})

2. **Implement Chart Component**:
   - Add mobile detection
   - Import and apply helper functions
   - Wrap in ChartMobileWrapper (Pattern A) or render directly (Pattern B)
   - Set up export functionality

3. **Implement Page Filters** (if needed):
   - Add mobile state
   - Create filter toggle button
   - Implement mobile filter Card
   - Hide desktop sidebar on mobile

4. **Test**:
   - Desktop viewport (> 768px)
   - Mobile viewport (< 768px)
   - Filter expansion/collapse
   - Chart export
   - Zoom functionality
   - Responsive grid layout

5. **Verify Checklist**:
   - No double Card wrapping
   - Title and subtitle visible
   - Controls accessible
   - Y-axis names visible
   - Filters work on mobile

## Output Format

Provide clear, actionable implementation steps with code examples. Reference specific files and line numbers where changes are needed. Flag any pattern conflicts or potential double Card wrapping issues.
