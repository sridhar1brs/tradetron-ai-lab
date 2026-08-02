import json
file_path = "/Users/srbalakrishnan/Algo_Lab/Tradetron_AI_KB/impot_export/Live_N50_IntraDay_NoRe_2pm_EMA_3m_Cross_Buy_SLTG_EMA_ITM4_Mstr_100x_mtly.json"
with open(file_path, "r") as f:
    data = json.load(f)

# Clear out the sets but keep the structure
data["sets"] = []
data["variables"] = []

with open("/Users/srbalakrishnan/Algo_Lab/Tradetron_AI_KB/scripts/base_strategy.json", "w") as f:
    json.dump(data, f, indent=2)
print("Base template created.")
