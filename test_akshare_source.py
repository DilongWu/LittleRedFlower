import akshare as ak
import sys
import datetime

# Test different data sources
print('=' * 60)
print('Testing AkShare Data Source Availability')
print('=' * 60)

# Test 1: Industry Board Data
print('\n1. Testing Industry Board Data (stock_board_industry_name_em)...')
try:
    df = ak.stock_board_industry_name_em()
    if df is not None and not df.empty:
        print(f'   SUCCESS! Got {len(df)} industry records')
        print(f'   Columns: {list(df.columns)[:5]}...')
    else:
        print('   FAILED: Empty data returned')
except Exception as e:
    print(f'   FAILED: {str(e)[:150]}')

# Test 2: Limit-Up Pool Data
print('\n2. Testing Limit-Up Pool Data (stock_zt_pool_em)...')
try:
    today = datetime.datetime.now().strftime('%Y%m%d')
    df = ak.stock_zt_pool_em(date=today)
    if df is not None and not df.empty:
        print(f'   SUCCESS! Got {len(df)} limit-up records')
    else:
        print(f'   WARNING: No data for today, trying yesterday...')
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y%m%d')
        df = ak.stock_zt_pool_em(date=yesterday)
        if df is not None and not df.empty:
            print(f'   SUCCESS! Got {len(df)} records from yesterday')
        else:
            print('   FAILED: No available data')
except Exception as e:
    print(f'   FAILED: {str(e)[:150]}')

# Test 3: Fund Flow Rank Data
print('\n3. Testing Fund Flow Rank Data (stock_individual_fund_flow_rank)...')
try:
    df = ak.stock_individual_fund_flow_rank(indicator='今日')
    if df is not None and not df.empty:
        print(f'   SUCCESS! Got {len(df)} fund flow records')
        print(f'   Columns: {list(df.columns)[:5]}...')
    else:
        print('   FAILED: Empty data returned')
except Exception as e:
    print(f'   FAILED: {str(e)[:150]}')

# Test 4: Concept Board Data
print('\n4. Testing Concept Board Data (stock_board_concept_name_em)...')
try:
    df = ak.stock_board_concept_name_em()
    if df is not None and not df.empty:
        print(f'   SUCCESS! Got {len(df)} concept records')
        if '板块名称' in df.columns:
            print(f'   Top 3 concepts: {df["板块名称"].head(3).tolist()}')
    else:
        print('   FAILED: Empty data returned')
except Exception as e:
    print(f'   FAILED: {str(e)[:150]}')

print('\n' + '=' * 60)
print('Test Completed')
print('=' * 60)
