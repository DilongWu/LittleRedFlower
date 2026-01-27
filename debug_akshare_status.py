import akshare as ak
import sys
import traceback

print(f"AkShare Version: {ak.__version__}")

def test_fund_flow():
    print("\n--- Testing Fund Flow ---")
    try:
        print("Calling stock_individual_fund_flow_rank()...")
        df = ak.stock_individual_fund_flow_rank()
        if df is not None and not df.empty:
            print(f"Success! Got {len(df)} rows.")
            print(df.head(1).to_string())
        else:
            print("Returned Empty DataFrame")
    except Exception:
        print("FAIL:")
        traceback.print_exc()

def test_index():
    print("\n--- Testing Index Daily ---")
    try:
        print("Calling stock_zh_index_daily_em(symbol='sh000001')...")
        df = ak.stock_zh_index_daily_em(symbol="sh000001")
        if df is not None and not df.empty:
            print(f"Success! Got {len(df)} rows.")
        else:
            print("Returned Empty DataFrame")
    except Exception:
        print("FAIL:")
        traceback.print_exc()

def test_concepts():
    print("\n--- Testing Concepts ---")
    try:
        print("Calling stock_board_concept_name_em()...")
        df = ak.stock_board_concept_name_em()
        if df is not None and not df.empty:
            print(f"Success! Got {len(df)} rows.")
        else:
            print("Returned Empty DataFrame")
    except Exception:
        print("FAIL:")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        test_fund_flow()
        test_index()
        test_concepts()
    except Exception as e:
        print(f"Global Error: {e}")
