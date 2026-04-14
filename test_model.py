from modules.tax_risk_model import predict_tax_risk

sample = {
    "shipment_tonnes": 15000,
    "distance_km": 17,
    "carbon_price_eur": 85,
    "emissions_per_tonne": 1.5,
    "season": 3
}

result = predict_tax_risk(sample)

print("\nRESULT:")
print(result)