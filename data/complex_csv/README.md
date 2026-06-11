# Complex CSV Test Set

Upload all four CSV files together from the TaxNet XAI dashboard:

- `fbr_tax_records_complex.csv`
- `excise_vehicles_complex.csv`
- `disco_consumption_complex.csv`
- `property_transfers_complex.csv`

These files intentionally include:

- noisy name variants
- Urdu name text
- phone formats with and without Pakistan country code
- missing phones
- shared household addresses
- proxy/associate ownership
- luxury assets with low or zero declared income
- commercial/seller noise records
- address abbreviations such as `H`, `St`, `Ph`, and `Blk`

Expected behavior:

- direct high-risk profiles should include Muhammad Ahmed Khan, Kamran Ali, and Farhan Qureshi
- associate/proxy risk should appear around Ali Raza Sheikh and Zara Iqbal
- Sara Malik, Bilal Mahmood, Hira Noor, Asif Khan, and Ayesha Siddiqui should generally look lower risk
- some profiles should show uncertainty flags because shared address/phone does not always prove same identity
