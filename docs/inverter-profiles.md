# Inverter profiles

Renogy inverters do not all use the same Modbus register layout. During setup,
select the profile matching the inverter model:

- **Generic** uses the standard inverter register sequence.
- **RIV4835CSH1S** uses the model-specific register sequence supported by
  `renogy-ble`.

Existing inverter entries can switch profiles without being deleted. Open the
Renogy integration entry, choose **Reconfigure**, keep the device type set to
**Inverter**, continue, and select **RIV4835CSH1S**. The entry reloads with the
new profile and exposes the model-specific line charging current telemetry.

Do not select the RIV4835CSH1S profile for another inverter model. The profile
controls which registers the integration requests; a mismatched profile may
return incomplete or incorrect data.
