from nic_analyzer import generate_dashboard_data
from pprint import pprint
sample_params = { "net_income_monthly": 30000,
                  "needs_food": 5000,
                  "needs_housing": 5000,
                  "needs_transport": 2000,
                  "needs_utilities": 1000,
                  "needs_insurance": 1000,
                  "needs_debt": 1000,
                  "wants_misc": 9000, }
print("\n=== Running Full Test (Analyzer + Typhoon) ===")
result = generate_dashboard_data(sample_params)
pprint(result)